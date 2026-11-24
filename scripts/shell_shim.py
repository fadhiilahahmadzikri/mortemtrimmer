"""Ultra-thin Explorer shell handler (<100ms startup) forwarding paths via OS IPC."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from multiprocessing.connection import Client

PIPE_WIN = r"\\.\pipe\autosilenttrimmer_gateway"
CORE_EXE_WIN = "autosilenttrimmer.exe"


def _resolve_ipc_endpoint() -> tuple[str, str]:
    if os.name == "nt":
        return PIPE_WIN, "AF_PIPE"
    runtime_dir = os.environ.get("XDG_RUNTIME_DIR", "/tmp")
    return os.path.join(runtime_dir, "autosilenttrimmer_gateway.sock"), "AF_UNIX"


def _append_shim_log(level: str, message: str) -> None:
    """Append shim dispatch or error diagnostics cleanly without altering old log lines."""
    try:
        if os.name == "nt":
            base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
            log_dir = os.path.join(base, "autosilenttrimmer", "logs")
        else:
            base = os.environ.get("XDG_STATE_HOME") or os.path.expanduser("~/.local/state")
            log_dir = os.path.join(base, "autosilenttrimmer", "logs")
        os.makedirs(log_dir, exist_ok=True)
        stamp = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(os.path.join(log_dir, "app.log"), "a", encoding="utf-8") as f:
            f.write(f"{stamp},000 [{level}] [pid:{os.getpid()}] [trim-shim] {message}\n")
    except OSError:
        pass


def _spawn_core_daemon() -> None:
    install_dir = os.path.dirname(os.path.abspath(sys.executable))
    core_exe = os.path.join(install_dir, CORE_EXE_WIN)
    if os.path.isfile(core_exe):
        cmd = [core_exe, "--daemon", "--tray"]
    else:
        cmd = [sys.executable, "-m", "autosilenttrimmer", "--daemon", "--tray"]

    kwargs: dict[str, object] = {}
    if os.name == "nt":
        kwargs["creationflags"] = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(
            subprocess, "CREATE_NO_WINDOW", 0
        )
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kwargs)  # type: ignore[arg-type]


def main(argv: list[str] | None = None) -> int:
    """Deliver selected Explorer file paths over OS IPC and exit immediately."""
    raw_args = list(sys.argv[1:] if argv is None else argv)
    paths = [os.path.abspath(a) for a in raw_args if a != "--enqueue"]
    if not paths:
        return 0

    addr, fam = _resolve_ipc_endpoint()
    spawned = False
    deadline = time.monotonic() + 3.0

    while time.monotonic() <= deadline:
        try:
            with Client(addr, family=fam) as conn:
                conn.send({"cmd": "enqueue", "paths": paths})
                resp = conn.recv()
                if isinstance(resp, dict) and resp.get("ok"):
                    _append_shim_log("INFO", f"Dispatched {len(paths)} file(s): {paths}")
                    return 0
                _append_shim_log("ERROR", f"Daemon rejected IPC payload: {resp}")
                return 1
        except OSError:
            if not spawned:
                _append_shim_log("INFO", "Background daemon inactive; spawning --daemon --tray")
                _spawn_core_daemon()
                spawned = True
            time.sleep(0.05)

    _append_shim_log(
        "ERROR", f"Timed out connecting to IPC gateway ({addr}) for {len(paths)} path(s): {paths}"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
