#!/usr/bin/env python3
"""Foreground supervisor for an explicitly supplied Seurat/Shiny gadget script."""

import argparse
import collections
import os
from pathlib import Path
import re
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request


VERSION = "5.6.0-r1"
SERVER = Path("/opt/seurat/seurat_gadget_server.R")


def port_value(value):
    try:
        port = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("port must be an integer") from None
    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError("port must be between 1 and 65535")
    return port


def timeout_value(value):
    try:
        timeout = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError("timeout must be a number") from None
    if not 0 < timeout <= 3600:
        raise argparse.ArgumentTypeError("timeout must be greater than 0 and at most 3600 seconds")
    return timeout


def parse_args():
    parser = argparse.ArgumentParser(
        prog="seurat-gadget",
        description="Run one trusted R script containing a Seurat/Shiny gadget in the foreground.",
        epilog=("No authentication or TLS is provided. Use localhost or an SSH tunnel. "
                "For Docker/Podman use --bind 0.0.0.0 with a host 127.0.0.1 port mapping; "
                "Apptainer normally uses the default --bind 127.0.0.1 without -p. "
                "Relative input/output paths remain relative to the current working directory. "
                "The script must call an upstream gadget, for example IFeaturePlot(); "
                "a Seurat object alone does not start a service. Save returned selections "
                "in the script after the gadget returns. Logs remain in the printed private "
                "temporary directory until its container or temporary storage is removed."),
    )
    parser.add_argument("--version", action="version", version="seurat-gadget " + VERSION)
    parser.add_argument("--script", required=True, help="readable R script; runs with site R profile enabled")
    parser.add_argument("--bind", choices=("127.0.0.1", "0.0.0.0"), default="127.0.0.1",
                        help="container listen address (default: 127.0.0.1)")
    parser.add_argument("--port", type=port_value, default=8787, help="container listen port (default: 8787)")
    parser.add_argument("--host-port", type=port_value, help="port shown in URL/SSH (default: --port)")
    parser.add_argument("--url-host", default="127.0.0.1", help="host name shown in URL, not a bind address")
    parser.add_argument("--timeout", type=timeout_value, default=120.0, help="readiness deadline in seconds (default: 120)")
    parser.add_argument("--label", default="Seurat gadget", help="session label for the startup card")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?", args.url_host):
        parser.error("--url-host must be an IPv4 address or host name, without a scheme or path")
    if args.url_host == "0.0.0.0":
        parser.error("--url-host must be a reachable host name, not 0.0.0.0")
    if not args.label.strip() or any(ord(char) < 32 or ord(char) == 127 for char in args.label):
        parser.error("--label must be nonempty and contain no control characters")
    try:
        args.script = Path(args.script).resolve(strict=True)
        if not args.script.is_file() or not os.access(args.script, os.R_OK):
            raise OSError("not a readable regular file")
    except (OSError, RuntimeError) as error:
        parser.error("--script is missing or unreadable: {}. Create an R script calling an upstream "
                     "Seurat gadget, then run seurat-gadget --script SCRIPT.R".format(error))
    args.host_port = args.host_port or args.port
    return args


class StopRequest:
    """Defer termination through Popen/PID registration; never signal a sentinel PID."""

    def __init__(self):
        self.signum = None

    def handle(self, signum, _frame):
        if self.signum is None:
            self.signum = signum
            message = "Seurat gadget is stopping ({}).\n".format(signal.Signals(signum).name)
            try:
                os.write(sys.stdout.fileno(), message.encode())
            except OSError:
                pass


def group_exists(pgid):
    try:
        os.killpg(pgid, 0)
        return True
    except ProcessLookupError:
        return False


def stop_child(child):
    """Only the isolated session created by this invocation can be terminated."""
    if child is None:
        return
    pgid = child.pid
    if pgid <= 1 or pgid == os.getpgrp():
        raise RuntimeError("refusing cleanup of an unowned process group")
    if group_exists(pgid):
        try:
            os.killpg(pgid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        deadline = time.monotonic() + 4
        while group_exists(pgid) and time.monotonic() < deadline:
            child.poll()
            time.sleep(0.05)
        if group_exists(pgid):
            try:
                os.killpg(pgid, signal.SIGKILL)
            except ProcessLookupError:
                pass
    child.wait(timeout=3)


def log_tail(path):
    try:
        with path.open(errors="replace") as stream:
            lines = collections.deque(stream, maxlen=60)
        print("--- Seurat R/Shiny log (last 60 lines) ---", file=sys.stderr, flush=True)
        sys.stderr.writelines(lines)
        sys.stderr.flush()
    except OSError as error:
        print("Cannot read internal log: {}".format(error), file=sys.stderr, flush=True)


def service_ready(opener, port, marker):
    # The launch callback is invoked by our R process only after Shiny has bound
    # its listener. HTTP alone could otherwise mistake a foreign server for us.
    try:
        started_url = marker.read_text().strip()
        if started_url not in ("http://127.0.0.1:{}".format(port), "http://127.0.0.1:{}/".format(port)):
            return False
        with opener.open("http://127.0.0.1:{}/".format(port), timeout=0.4) as response:
            body = response.read(1024 * 1024)
            return response.status == 200 and b"shiny" in body.lower() and b"<html" in body.lower()
    except (OSError, urllib.error.URLError):
        return False


def main():
    args = parse_args()
    if not SERVER.is_file():
        print("seurat-gadget: missing installed R launcher: {}".format(SERVER), file=sys.stderr)
        return 1
    if not shutil.which("Rscript"):
        print("seurat-gadget: Rscript is unavailable", file=sys.stderr)
        return 1
    stop = StopRequest()
    signal.signal(signal.SIGINT, stop.handle)
    signal.signal(signal.SIGTERM, stop.handle)
    child = None
    root = None
    log = None
    result = 1
    try:
        # Reject an occupied endpoint without touching or stopping its owner.
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            probe.bind((args.bind, args.port))
        root = Path(tempfile.mkdtemp(prefix="seurat-gadget-"))
        private = {}
        for name in ("tmp", "home", "cache", "config"):
            private[name] = root / name
            private[name].mkdir(mode=0o700)
        log = root / "server.log"
        marker = root / "started"
        environment = os.environ.copy()
        environment.update({
            "TMPDIR": str(private["tmp"]), "TMP": str(private["tmp"]),
            "TEMP": str(private["tmp"]), "HOME": str(private["home"]),
            "R_USER": str(private["home"]), "XDG_CACHE_HOME": str(private["cache"]),
            "XDG_CONFIG_HOME": str(private["config"]), "PYTHONDONTWRITEBYTECODE": "1",
            "SEURAT_GADGET_SCRIPT": str(args.script), "SEURAT_GADGET_BIND": args.bind,
            "SEURAT_GADGET_PORT": str(args.port), "SEURAT_GADGET_STARTED": str(marker),
        })
        with log.open("xb") as output:
            os.chmod(log, 0o600)
            if stop.signum:
                return 128 + stop.signum
            print("{} is starting.\nOpen: http://{}:{}/\nRemote: ssh -N -L {}:127.0.0.1:{} user@server\n"
                  "Press Ctrl-C to stop this GUI session.\nInternal log: {}\n"
                  "Security: no authentication/TLS; use localhost or SSH only.".format(
                      args.label, args.url_host, args.host_port, args.host_port, args.host_port, log), flush=True)
            if not stop.signum:
                child = subprocess.Popen(
                    ["Rscript", "--no-save", "--no-restore", "--no-init-file", str(SERVER)],
                    stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT,
                    env=environment, start_new_session=True,
                )
            deadline = time.monotonic() + args.timeout
            ready = False
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            while child is not None and not stop.signum:
                status = child.poll()
                if status is not None:
                    if ready and status == 0:
                        print("Seurat gadget finished.", flush=True)
                        result = 0
                    else:
                        print("seurat-gadget: R/Shiny exited {} ({} readiness).".format(
                            status, "after" if ready else "before"), file=sys.stderr, flush=True)
                        log_tail(log)
                        result = status if status and status > 0 else 1
                    break
                if not ready:
                    if service_ready(opener, args.port, marker) and child.poll() is None and not stop.signum:
                        ready = True
                        print("Seurat gadget is ready.", flush=True)
                    elif time.monotonic() >= deadline:
                        print("seurat-gadget: R/Shiny readiness timeout after {} seconds.".format(args.timeout),
                              file=sys.stderr, flush=True)
                        log_tail(log)
                        break
                time.sleep(0.05)
            if stop.signum:
                result = 128 + stop.signum
    except (OSError, subprocess.SubprocessError, RuntimeError) as error:
        print("seurat-gadget: {}".format(error), file=sys.stderr, flush=True)
        if log is not None:
            log_tail(log)
    finally:
        try:
            stop_child(child)
        except (OSError, subprocess.SubprocessError, RuntimeError) as error:
            print("seurat-gadget: cleanup failed: {}".format(error), file=sys.stderr, flush=True)
            result = 1
        if root is not None:
            # Each target was created beneath this invocation's private root.
            # Retain only the diagnostic log; never scan shared /tmp.
            for name in ("tmp", "home", "cache", "config"):
                path = root / name
                if path.is_symlink():
                    path.unlink()
                elif path.is_dir():
                    shutil.rmtree(path)
            for name in ("started", "started.tmp"):
                (root / name).unlink(missing_ok=True)
        if stop.signum:
            print("Seurat gadget stopped.", flush=True)
            if result != 1:
                result = 128 + stop.signum
    return result


if __name__ == "__main__":
    sys.exit(main())
