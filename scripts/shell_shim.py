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
                return 0 if isinstance(resp, dict) and resp.get("ok") else 1
        except OSError:
            if not spawned:
                _spawn_core_daemon()
                spawned = True
            time.sleep(0.05)

    return 1


if __name__ == "__main__":
    sys.exit(main())
