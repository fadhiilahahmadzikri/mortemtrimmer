"""Cleanly remove installed AutoSilentTrimmer desktop binaries & Explorer shell hooks."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from autosilenttrimmer.core.constants import APP_NAME, SUPPORTED_MEDIA_EXTENSIONS
from autosilenttrimmer.infrastructure.platform.paths import PlatformDirsPaths
from autosilenttrimmer.infrastructure.platform.shell.factory import create_shell_integration

TARGET_PROCESS_NAMES: frozenset[str] = frozenset({"autosilenttrimmer.exe", "trim-shim.exe"})
INNO_UNINSTALL_REG_PATH: str = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\{B4E73E3A-9C2F-4F91-A72E-83D18D410F12}_is1"


def _clear_inno_uninstall_registry() -> bool:
    """Remove leftover Inno Setup HKCU Uninstall key so reinstalls honor fresh defaults."""
    if os.name != "nt":
        return False
    import winreg

    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, INNO_UNINSTALL_REG_PATH)
        return True
    except OSError:
        return False


def default_windows_install_dir() -> Path:
    """Resolve per-user Inno Setup installation folder without hardcoded machine paths."""
    local_app = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    return Path(local_app) / "Programs" / "AutoSilentTrimmer"


def _windows_start_menu_dir() -> Path:
    app_data = os.environ.get("APPDATA") or os.path.expanduser("~")
    return Path(app_data) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / APP_NAME


def stop_installed_processes(install_dir: Path, *, dry_run: bool = False) -> list[int]:
    """Terminate running installed desktop binaries matching install_dir safely via psutil."""
    import psutil

    stopped: list[int] = []
    norm_install = os.path.normcase(str(install_dir.resolve()))
    for proc in psutil.process_iter(["pid", "name", "exe"]):
        try:
            name = (proc.info.get("name") or "").lower()
            exe = proc.info.get("exe") or ""
            if name not in TARGET_PROCESS_NAMES or not exe:
                continue
            norm_exe = os.path.normcase(os.path.abspath(exe))
            if not norm_exe.startswith(norm_install):
                continue
            pid = int(proc.info["pid"])
            if not dry_run:
                proc.terminate()
                try:
                    proc.wait(timeout=3.0)
                except psutil.TimeoutExpired:
                    proc.kill()
            stopped.append(pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
            continue

    if stopped and not dry_run:
        time.sleep(0.3)
    return stopped


def clean_installed_app(
    *,
    install_dir: Path | None = None,
    data_dir: Path | None = None,
    start_menu_dir: Path | None = None,
    unregister_shell: bool = True,
    purge_data: bool = False,
    dry_run: bool = False,
) -> dict[str, object]:
    """Perform complete clean removal of installed app while preserving user logs by default."""
    target_install = install_dir or default_windows_install_dir()
    target_data = data_dir or Path(PlatformDirsPaths().data_dir)
    target_menu = start_menu_dir or _windows_start_menu_dir()

    stopped_pids = stop_installed_processes(target_install, dry_run=dry_run)

    uninstaller_ran = False
    unins_exe = target_install / "unins000.exe"
    if unins_exe.is_file():
        uninstaller_ran = True
        if not dry_run:
            subprocess.run(
                [str(unins_exe), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"],
                check=False,
                capture_output=True,
                timeout=30,
            )

    shell_cleaned = False
    if unregister_shell:
        shell_cleaned = True
        if not dry_run:
            create_shell_integration().unregister(SUPPORTED_MEDIA_EXTENSIONS)

    install_removed = False
    if target_install.exists():
        install_removed = True
        if not dry_run:
            shutil.rmtree(target_install, ignore_errors=True)

    menu_removed = False
    if target_menu.exists():
        menu_removed = True
        if not dry_run:
            shutil.rmtree(target_menu, ignore_errors=True)

    data_purged = False
    if purge_data and target_data.exists():
        data_purged = True
        if not dry_run:
            shutil.rmtree(target_data, ignore_errors=True)

    if not dry_run:
        _clear_inno_uninstall_registry()

    return {
        "dry_run": dry_run,
        "stopped_pids": stopped_pids,
        "uninstaller_ran": uninstaller_ran,
        "shell_unregistered": shell_cleaned,
        "install_dir_removed": install_removed,
        "start_menu_removed": menu_removed,
        "data_purged": data_purged,
        "data_preserved_at": None if data_purged else str(target_data),
    }


def main() -> int:
    """CLI entrypoint for clean post-test uninstall before reinstalling newer builds."""
    parser = argparse.ArgumentParser(
        description=f"Cleanly remove installed {APP_NAME} desktop app (preserves logs unless --purge-data)."
    )
    parser.add_argument(
        "--install-dir",
        type=Path,
        default=None,
        help="Override target installation directory to remove",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help="Override user data directory (used when --purge-data is passed)",
    )
    parser.add_argument(
        "--start-menu-dir",
        type=Path,
        default=None,
        help="Override Start Menu folder to clean",
    )
    parser.add_argument(
        "--skip-shell",
        action="store_true",
        help="Skip HKCU shell registry cleanup (useful for isolated CI temp installs)",
    )
    parser.add_argument(
        "--purge-data",
        action="store_true",
        help="Also remove app.log, settings.json, and downloaded Runtime Packs",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show cleanup actions without terminating processes or deleting files",
    )
    args = parser.parse_args()

    summary = clean_installed_app(
        install_dir=args.install_dir,
        data_dir=args.data_dir,
        start_menu_dir=args.start_menu_dir,
        unregister_shell=not args.skip_shell,
        purge_data=args.purge_data,
        dry_run=args.dry_run,
    )
    print(f"Cleaner summary (dry_run={summary['dry_run']}):")
    print(f"  Stopped PIDs       : {summary['stopped_pids']}")
    print(f"  Inno uninstaller   : {summary['uninstaller_ran']}")
    print(f"  Shell menu cleaned : {summary['shell_unregistered']}")
    print(f"  Install dir wiped  : {summary['install_dir_removed']}")
    print(f"  Start Menu wiped   : {summary['start_menu_removed']}")
    print(f"  User data purged   : {summary['data_purged']}")
    if summary["data_preserved_at"]:
        print(f"  Logs/settings kept : {summary['data_preserved_at']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
