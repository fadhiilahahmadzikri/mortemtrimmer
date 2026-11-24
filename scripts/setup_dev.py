"""Developer environment setup utility for AutoSilentTrimmer."""

from __future__ import annotations

import os
import subprocess
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run_command(cmd: list[str]) -> bool:
    """Execute a system command and print output."""
    print(f"-> {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    return result.returncode == 0


def setup() -> int:
    """Install dependencies and register multi-stage git hooks."""
    print("=================================================================")
    print("AutoSilentTrimmer: Developer Environment Initialization")
    print("=================================================================")

    # 1. Install pre-commit and ruff if missing
    pip_cmd = [sys.executable, "-m", "pip", "install", "pre-commit", "ruff"]
    if not run_command(pip_cmd):
        print("Error: Failed to install pre-commit and ruff.")
        return 1

    # 2. Register multi-stage pre-commit hooks
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

    print("\nEnvironment initialization complete!")
    print("Git hooks configured: pre-commit, commit-msg, and pre-push are active.")
    return 0


if __name__ == "__main__":
    sys.exit(setup())
