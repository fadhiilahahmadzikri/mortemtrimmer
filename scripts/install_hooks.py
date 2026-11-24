"""Script to configure Git to use tracked .githooks directory."""

from __future__ import annotations

import os
import subprocess
import sys


def install_hooks() -> int:
    """Configure core.hooksPath in local git repository."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    hooks_dir = os.path.join(project_root, ".githooks")

    if not os.path.exists(hooks_dir):
        print(f"Error: Hooks directory not found at {hooks_dir}")
        return 1

    try:
        subprocess.run(
            ["git", "config", "core.hooksPath", ".githooks"],
            cwd=project_root,
            check=True,
            capture_output=True,
            text=True,
        )
        print("Git configured successfully: core.hooksPath set to '.githooks'.")
        print("Pre-commit quality gates will run automatically on 'git commit'.")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"Failed to configure git core.hooksPath: {e.stderr}")
        return 1


if __name__ == "__main__":
    sys.exit(install_hooks())
