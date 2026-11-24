"""Conventional Commits validator for Git commit-msg stage."""

from __future__ import annotations

import re
import sys

CONVENTIONAL_PATTERN = re.compile(
    r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)"
    r"(\([a-zA-Z0-9_\-\./]+\))?(!)?: .+"
)


def validate_commit_msg(msg_file: str) -> int:
    """Validate that the first line of the commit message conforms to Conventional Commits."""
    with open(msg_file, encoding="utf-8", errors="ignore") as f:
        first_line = f.readline().strip()

    # Ignore automated merge or revert commits
    if first_line.startswith(("Merge ", "Revert ", "Apply ")):
        return 0

    if not CONVENTIONAL_PATTERN.match(first_line):
        print(f"[commit-msg ERROR] Invalid commit message: '{first_line}'")
        print("Commit message must follow Conventional Commits specification:")
        print("  <type>(<scope>): <short description>")
        print(
            "  Allowed types: feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert"
        )
        print("  Example: feat(vad): add energy-based voice activity detector")
        return 1

    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Error: commit message file path not provided.")
        sys.exit(1)
    sys.exit(validate_commit_msg(sys.argv[1]))
