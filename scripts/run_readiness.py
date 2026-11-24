"""Runner for system readiness pre-push check ensuring project venv resolution."""

from __future__ import annotations

import os
import subprocess
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENV_PYTHON_WIN = os.path.join(PROJECT_ROOT, ".venv", "Scripts", "python.exe")
VENV_PYTHON_UNIX = os.path.join(PROJECT_ROOT, ".venv", "bin", "python")


def main() -> int:
    """Execute pre-push system readiness audit, delegating to venv if needed."""
    if os.path.isfile(VENV_PYTHON_WIN) and os.path.normpath(sys.executable) != os.path.normpath(
        VENV_PYTHON_WIN
    ):
        proc = subprocess.run([VENV_PYTHON_WIN, "-m", "autosilenttrimmer", "--check"])
        return proc.returncode

    if os.path.isfile(VENV_PYTHON_UNIX) and os.path.normpath(sys.executable) != os.path.normpath(
        VENV_PYTHON_UNIX
    ):
        proc = subprocess.run([VENV_PYTHON_UNIX, "-m", "autosilenttrimmer", "--check"])
        return proc.returncode

    if PROJECT_ROOT not in sys.path:
        sys.path.insert(0, PROJECT_ROOT)

    from autosilenttrimmer.presentation.cli.runner import run_cli

    return run_cli(["--check"])


if __name__ == "__main__":
    sys.exit(main())
