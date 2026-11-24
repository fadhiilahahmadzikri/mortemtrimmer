"""Pre-commit quality gate checker enforcing Feature-First Clean Architecture rules."""

from __future__ import annotations

import os
import py_compile
import re
import subprocess
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

FORBIDDEN_PATTERNS = [
    (re.compile(r"[C|c]:\\Users\\"), "Hardcoded user directory path detected"),
    (re.compile(r"[C|c]:\\ProgramData\\"), "Hardcoded machine-specific absolute path detected"),
]

EMOJI_PATTERN = re.compile(
    r"[\U00010000-\U0010ffff]|[\u2600-\u27bf]|[\u2300-\u23ff]",
    re.UNICODE,
)

MAX_LINES_PER_FILE = 500


def find_source_files(root_dir: str) -> list[str]:
    """Return git-tracked Python files only (ignores untracked caches and generated artifacts)."""
    out = subprocess.check_output(["git", "ls-files", "*.py"], cwd=root_dir, text=True)
    files: list[str] = []
    for rel in out.splitlines():
        rel_clean = rel.strip()
        if not rel_clean:
            continue
        full_path = os.path.join(root_dir, rel_clean)
        if os.path.isfile(full_path):
            files.append(os.path.abspath(full_path))
    return sorted(files)


def gate_syntax_compilation(files: list[str]) -> bool:
    """Quality Gate 1: Compile every Python source file to catch syntax errors."""
    print("[gate 1/4] Checking Python syntax compilation...")
    has_error = False
    for path in files:
        try:
            py_compile.compile(path, doraise=True)
        except py_compile.PyCompileError as e:
            print(f"  [SYNTAX ERROR] {path}: {e}")
            has_error = True
    if not has_error:
        print(f"  [OK] Syntax verified across {len(files)} files.")
    return not has_error


def gate_file_size_limit(files: list[str]) -> bool:
    """Quality Gate 2: Enforce max 500 lines per file (Feature-First Clean Architecture rule)."""
    print(f"[gate 2/4] Checking file line count limit (max {MAX_LINES_PER_FILE} lines)...")
    has_error = False
    for path in files:
        with open(path, encoding="utf-8", errors="ignore") as f:
            lines = len(f.readlines())
        if lines > MAX_LINES_PER_FILE:
            print(f"  [LINE LIMIT EXCEEDED] {path}: {lines} lines (max {MAX_LINES_PER_FILE})")
            has_error = True
    if not has_error:
        print("  [OK] All source files respect line-count limits.")
    return not has_error


def gate_clean_code_hygiene(files: list[str]) -> bool:
    """Quality Gate 3: Reject hardcoded paths, forbidden patterns, and emojis in source code."""
    print("[gate 3/4] Scanning for hardcoded paths and prohibited artifacts...")
    has_error = False
    for path in files:
        with open(path, encoding="utf-8", errors="ignore") as f:
            content = f.read()

        for pattern, msg in FORBIDDEN_PATTERNS:
            if pattern.search(content):
                print(f"  [HYGIENE VIOLATION] {path}: {msg}")
                has_error = True

        if EMOJI_PATTERN.search(content):
            print(f"  [EMOJI DETECTED] {path}: Emojis are strictly prohibited in codebase.")
            has_error = True

    if not has_error:
        print("  [OK] Code hygiene clean: zero prohibited hardcoded patterns or emojis.")
    return not has_error


def gate_system_readiness() -> bool:
    """Quality Gate 4: Execute system readiness diagnostic check."""
    print("[gate 4/4] Executing system readiness diagnostic...")
    try:
        from autosilenttrimmer.application.use_cases.system_readiness import (
            SystemReadinessUseCase,
        )
        from autosilenttrimmer.infrastructure.diagnostics.engines import EngineDiagnostic
        from autosilenttrimmer.infrastructure.diagnostics.ffmpeg import FFmpegDiagnostic
        from autosilenttrimmer.infrastructure.diagnostics.hardware import HardwareDiagnostic
        from autosilenttrimmer.infrastructure.media.ffmpeg_locator import ManagedFFmpegLocator

        locator = ManagedFFmpegLocator()
        diagnostics = [
            HardwareDiagnostic(),
            FFmpegDiagnostic(locator),
            EngineDiagnostic(),
        ]
        use_case = SystemReadinessUseCase(diagnostics)
        report = use_case.execute()

        if not report.is_ready:
            print("  [FAILED] System readiness audit detected critical dependency issues:")
            for item in report.items:
                if item.is_critical and item.status.value == "FAILED":
                    print(f"    * {item.component}: {item.detail}")
            return False

        print(f"  [OK] System readiness verified (Ready: {report.is_ready}).")
        return True

    except Exception as e:
        print(f"  [ERROR] System readiness diagnostic failed to run: {e}")
        return False


def main() -> int:
    """Run Clean Architecture quality gates on git-tracked files."""
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    files = find_source_files(root_dir)

    success = (
        gate_syntax_compilation(files)
        and gate_file_size_limit(files)
        and gate_clean_code_hygiene(files)
    )

    if "--with-readiness" in sys.argv:
        success = success and gate_system_readiness()

    if not success:
        print("\nPre-commit quality gates FAILED. Commit aborted.")
        return 1

    print("\nPre-commit quality gates PASSED. Proceeding with commit.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
