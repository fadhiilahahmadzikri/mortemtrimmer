"""Developer environment setup utility for AutoSilentTrimmer."""

from __future__ import annotations

import os
import subprocess
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run_command(cmd: list[str]) -> bool:
    """Execute a system command cleanly."""
    print(f"-> {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    return result.returncode == 0


def setup() -> int:
    """Install dependencies and register multi-stage git hooks."""
    print("AutoSilentTrimmer: Developer Environment Initialization")

    if not run_command([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"]):
        print("Error: Failed to install project dependencies.")
        return 1

    hooks_cmd = [
        sys.executable,
        "-m",
        "pre_commit",
        "install",
        "-t",
        "pre-commit",
        "-t",
        "commit-msg",
        "-t",
        "pre-push",
    ]
    if not run_command(hooks_cmd):
        print("Error: Failed to install pre-commit hooks.")
        return 1

    print("Environment initialization complete. Multi-stage hooks active.")
    return 0


if __name__ == "__main__":
    sys.exit(setup())
