#!/usr/bin/env python3
"""Independent offline GUI probes; browser and real-wrapper gates are separate."""

import argparse
import os
from pathlib import Path
import re
import selectors
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request


FIXTURE = """suppressPackageStartupMessages(library(Seurat))
data(\"pbmc_small\", package = \"SeuratObject\")
stopifnot(\"MS4A1\" %in% rownames(pbmc_small), \"tsne\" %in% Reductions(pbmc_small))
Seurat::IFeaturePlot(pbmc_small, feature = \"MS4A1\", reduction = \"tsne\")
"""


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def free_port():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def port_closed(port):
    with socket.socket() as probe:
        probe.settimeout(0.2)
        return probe.connect_ex(("127.0.0.1", port)) != 0


class Session:
    def __init__(self, command, root):
        environment = os.environ.copy()
        environment["TMPDIR"] = str(root)
        self.child = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                      env=environment, start_new_session=True)
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.child.stdout, selectors.EVENT_READ)
        self.text = ""

    def pump(self, timeout=0.1):
        for key, _ in self.selector.select(timeout):
            data = os.read(key.fileobj.fileno(), 65536)
            if data:
                self.text += data.decode(errors="replace")
            else:
                self.selector.unregister(key.fileobj)

    def wait_for(self, marker, timeout):
        deadline = time.monotonic() + timeout
        while marker not in self.text and time.monotonic() < deadline:
            self.pump()
            if self.child.poll() is not None:
                self.pump(0)
                break
        require(marker in self.text, "missing marker: {}\n{}".format(marker, self.text))

    def finish(self, timeout=10):
        deadline = time.monotonic() + timeout
        while self.child.poll() is None and time.monotonic() < deadline:
            self.pump()
        require(self.child.poll() is not None, "helper failed to exit within {} seconds".format(timeout))
        while self.selector.get_map():
            self.pump(0.1)
        return self.child.returncode

    def cleanup(self):
        if self.child.poll() is None:
            self.child.send_signal(signal.SIGTERM)
            try:
                self.child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.child.kill()
                self.child.wait(timeout=3)
        self.selector.close()
        self.child.stdout.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("help", "missing", "ready-term", "ready-int", "startup-int",
                                        "startup-term", "failure", "timeout", "occupied"))
    parser.add_argument("--helper", default="seurat-gadget")
    args = parser.parse_args()
    root = Path(tempfile.mkdtemp(prefix="seurat-gadget-smoke-"))
    session = None
    foreign = None
    try:
        script = root / "tiny gadget.R"
        script.write_text(FIXTURE)
        if args.mode == "help":
            completed = subprocess.run([args.helper, "--help"], text=True, capture_output=True, timeout=10)
            require(completed.returncode == 0, completed.stderr)
            for marker in ("--script", "--bind", "--port", "--host-port", "--url-host", "--timeout", "--label"):
                require(marker in completed.stdout, "help missing " + marker)
            for bad in (["--unknown"], ["--script"], ["--script", str(script), "--port", "0"]):
                result = subprocess.run([args.helper] + bad, text=True, capture_output=True, timeout=10)
                require(result.returncode != 0, "invalid option unexpectedly succeeded")
            print("SEURAT_GADGET_HELP_PASS")
            return 0
        if args.mode == "missing":
            result = subprocess.run([args.helper, "--script", str(root / "missing.R")],
                                    text=True, capture_output=True, timeout=10)
            require(result.returncode != 0 and "missing or unreadable" in result.stderr, result.stderr)
            require("Create an R script" in result.stderr, "missing input lacks next step")
            require("is starting" not in result.stdout, "started with missing input")
            print("SEURAT_GADGET_MISSING_PASS")
            return 0
        port = free_port()
        if args.mode in ("startup-int", "startup-term", "timeout"):
            script.write_text("Sys.sleep(60)\n" + FIXTURE)
        if args.mode == "failure":
            script.write_text('stop("SEURAT_GADGET_FAILURE_FIXTURE")\n')
        if args.mode == "occupied":
            foreign = socket.socket()
            foreign.bind(("127.0.0.1", port))
            foreign.listen(1)
        command = [args.helper, "--script", str(script), "--port", str(port), "--host-port", "18787",
                   "--label", "Seurat tiny gadget", "--timeout", "0.5" if args.mode == "timeout" else "120"]
        session = Session(command, root)
        if args.mode == "occupied":
            status = session.finish()
            require(status != 0 and "is ready" not in session.text, session.text)
            require(foreign.fileno() >= 0 and not port_closed(port), "foreign endpoint was modified")
        else:
            session.wait_for("is starting.", 3)
            for marker in ("http://127.0.0.1:18787/", "ssh -N -L 18787:127.0.0.1:18787", "Ctrl-C", "Internal log:"):
                session.wait_for(marker, 1)
            match = re.search(r"Internal log: (.+)", session.text)
            require(match is not None, "missing log path")
            runtime = Path(match.group(1)).parent
            require(runtime.parent == root and (runtime.stat().st_mode & 0o777) == 0o700, "runtime not private")
            if args.mode in ("startup-int", "startup-term"):
                require("is ready" not in session.text, "startup fixture was already ready")
                sig = signal.SIGINT if args.mode == "startup-int" else signal.SIGTERM
                session.child.send_signal(sig)
                require(session.finish() == 128 + sig, session.text)
                require("is stopping ({})".format(signal.Signals(sig).name) in session.text, session.text)
                require("Seurat gadget stopped." in session.text, session.text)
            elif args.mode in ("failure", "timeout"):
                require(session.finish() != 0 and "is ready" not in session.text, session.text)
                marker = "SEURAT_GADGET_FAILURE_FIXTURE" if args.mode == "failure" else "readiness timeout"
                require(marker in session.text, "failure diagnostic absent: " + session.text)
            else:
                session.wait_for("Seurat gadget is ready.", 125)
                require(session.text.index("is starting.") < session.text.index("is ready."), "banner order")
                opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
                with opener.open("http://127.0.0.1:{}/".format(port), timeout=3) as response:
                    page = response.read().decode()
                require("shiny" in page.lower() and "mini" in page.lower(), "real gadget UI absent")
                scripts = re.findall(r'<script[^>]+src=["\']([^"\']+)', page)
                require(scripts, "Shiny JS dependencies absent")
                for source in scripts:
                    require(not source.startswith(("http:", "https:", "//")), "unexpected remote runtime JS")
                    with opener.open("http://127.0.0.1:{}/{}".format(port, source.lstrip("/")), timeout=3) as response:
                        require(response.status == 200 and response.read(100), "empty runtime JS")
                sig = signal.SIGTERM if args.mode == "ready-term" else signal.SIGINT
                session.child.send_signal(sig)
                require(session.finish() == 128 + sig, session.text)
                require("is stopping ({})".format(signal.Signals(sig).name) in session.text, session.text)
                require("Seurat gadget stopped." in session.text, session.text)
            require(port_closed(port), "session listen port remains open")
            require(sorted(path.name for path in runtime.iterdir()) == ["server.log"], "runtime endpoints remain")
        print("SEURAT_GADGET_{}_PASS".format(args.mode.upper().replace("-", "_")))
        return 0
    except Exception as error:
        print("seurat-gadget smoke-stage={} FAIL: {}".format(args.mode, error), file=sys.stderr)
        if session:
            print(session.text[-20000:], file=sys.stderr)
        return 1
    finally:
        if session:
            session.cleanup()
        if foreign:
            foreign.close()
        shutil.rmtree(root)


if __name__ == "__main__":
    sys.exit(main())
