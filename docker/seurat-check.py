#!/usr/bin/env python3
"""独立、离线、只读根兼容的 Seurat 运行检查。网络隔离由调用 engine 提供。"""

import argparse
import collections
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time


VERSION = "5.6.0-r1"
MODES = ("identity", "modules", "workflow", "threading", "sct", "bpcells", "io", "static", "negative")
DATA = Path("/opt/seurat/share/testdata")


def log_tail(path):
    with path.open("rb") as stream:
        lines = collections.deque(stream, maxlen=100)
    return b"".join(lines)[-24000:].decode("utf-8", errors="replace")


def run_stage(mode):
    # TemporaryDirectory 只删除本调用创建的唯一私有根；从不接受用户删除路径。
    with tempfile.TemporaryDirectory(prefix="taf-seurat-check-", dir="/tmp") as work:
        root = Path(work)
        os.chmod(root, 0o700)
        env = os.environ.copy()
        for key in ("R_LIBS", "R_LIBS_SITE", "R_PROFILE", "R_PROFILE_USER", "R_ENVIRON", "R_ENVIRON_USER"):
            env.pop(key, None)
        for key, directory in (("HOME", "home"), ("TMPDIR", "tmp"), ("XDG_CACHE_HOME", "cache"),
                               ("XDG_CONFIG_HOME", "config"), ("XDG_DATA_HOME", "data"),
                               ("R_LIBS_USER", "r-user")):
            path = root / directory
            path.mkdir(mode=0o700)
            env[key] = str(path)
        env.update({"OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1",
                    "BLIS_NUM_THREADS": "1", "VECLIB_MAXIMUM_THREADS": "1", "NUMEXPR_NUM_THREADS": "1",
                    "RETICULATE_USE_MANAGED_VENV": "no", "PYTHONDONTWRITEBYTECODE": "1"})
        if mode == "workflow":
            argv = ["Rscript", "--vanilla", str(DATA / "seurat_smoke.R"), str(root / "output")]
            marker = "seurat smoke ok"
        else:
            argv = ["Rscript", "--vanilla", str(DATA / "seurat_checks.R"), mode, str(root)]
            marker = f"SEURAT_CHECK {mode} PASS"
        log = root / "stage.log"
        print(f"smoke-stage={mode} starting", flush=True)
        proc = None
        interrupted = [None]
        interrupted_at = [None]

        def on_signal(signum, _frame):
            interrupted[0] = signum
            interrupted_at[0] = time.monotonic()
            # 只向本轮 start_new_session 创建且尚存活的子进程组发信号。
            if proc is not None and proc.poll() is None:
                try:
                    os.killpg(proc.pid, signum)
                except ProcessLookupError:
                    pass

        handlers = {s: signal.signal(s, on_signal) for s in (signal.SIGINT, signal.SIGTERM)}
        try:
            with log.open("wb") as stream:
                proc = subprocess.Popen(argv, cwd=root, env=env, stdin=subprocess.DEVNULL,
                                        stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
                deadline = time.monotonic() + 480
                while proc.poll() is None:
                    now = time.monotonic()
                    if interrupted_at[0] is not None and now - interrupted_at[0] >= 5:
                        os.killpg(proc.pid, signal.SIGKILL)
                        break
                    if now >= deadline:
                        os.killpg(proc.pid, signal.SIGTERM)
                        try:
                            proc.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            os.killpg(proc.pid, signal.SIGKILL)
                        break
                    try:
                        proc.wait(timeout=0.2)
                    except subprocess.TimeoutExpired:
                        pass
                status = proc.wait()
                if time.monotonic() >= deadline and interrupted[0] is None:
                    status = 124
            if interrupted[0] is not None:
                status = 128 + interrupted[0]
            elif status < 0:
                status = 128 - status
            tail = log_tail(log)
            if status == 0 and marker not in tail.splitlines():
                print(f"smoke-stage={mode} missing-success-marker", file=sys.stderr)
                status = 1
            if status != 0:
                print(f"smoke-stage={mode} exit={status}\n{tail}", file=sys.stderr, flush=True)
                return status
            print(f"{marker}\nsmoke-stage={mode} exit=0", flush=True)
            return 0
        except OSError as exc:
            print(f"smoke-stage={mode} spawn-error={exc}", file=sys.stderr)
            return 127
        finally:
            if proc is not None and proc.poll() is None:
                try:
                    os.killpg(proc.pid, signal.SIGTERM)
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait()
                except ProcessLookupError:
                    pass
            for signum, handler in handlers.items():
                signal.signal(signum, handler)


def main():
    parser = argparse.ArgumentParser(description="Independent Seurat offline checks; engine must disable networking.")
    parser.add_argument("--version", action="version", version=f"seurat-check {VERSION}")
    parser.add_argument("mode", choices=("buildtime",) + MODES + ("all",))
    args = parser.parse_args()
    modes = MODES if args.mode == "all" else (args.mode,)
    for mode in modes:
        status = run_stage(mode)
        if status:
            return status
    return 0


if __name__ == "__main__":
    sys.exit(main())
