# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Fadhiilah Ahmad Zikri
"""CLI runner, composition root, IPC dispatch, Tune launcher, and daemon lifecycle controller."""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import time
import warnings

from autosilenttrimmer.application.use_cases.diagnose_export import ExportDiagnosticsUseCase
from autosilenttrimmer.application.use_cases.job_orchestrator import JobOrchestrator
from autosilenttrimmer.application.use_cases.manage_runtime import ManageRuntimeUseCase
from autosilenttrimmer.application.use_cases.process_media import ProcessMediaUseCase
from autosilenttrimmer.application.use_cases.system_readiness import SystemReadinessUseCase
from autosilenttrimmer.branding import (
    APP_NAME,
    APP_VERSION,
    AUTHOR,
    COPYRIGHT_NOTICE,
    GITHUB_URL,
)
from autosilenttrimmer.core.constants import (
    SHELL_CONTEXT_MENU_LABEL,
    TIER1_VIDEO_EXTENSIONS,
    VIDEO_EXTENSIONS,
)
from autosilenttrimmer.core.exceptions import AutoSilentTrimmerException
from autosilenttrimmer.core.i18n import Localizer, detect_system_language
from autosilenttrimmer.domain.models.processing_command import (
    DestinationPromptRequest,
    ProcessMediaCommand,
)
from autosilenttrimmer.infrastructure.compute.backend_selector import PolicyComputeBackend
from autosilenttrimmer.infrastructure.compute.capability_prober import (
    CrossPlatformCapabilityProber,
)
from autosilenttrimmer.infrastructure.diagnostics.engines import EngineDiagnostic
from autosilenttrimmer.infrastructure.diagnostics.ffmpeg import FFmpegDiagnostic
from autosilenttrimmer.infrastructure.diagnostics.hardware import HardwareDiagnostic
from autosilenttrimmer.infrastructure.diagnostics.runtime_pack import (
    ProductionReadinessDiagnostic,
)
from autosilenttrimmer.infrastructure.events.in_memory_bus import InMemoryEventBus
from autosilenttrimmer.infrastructure.ipc.gateway import (
    LocalIPCClient,
    LocalIPCGateway,
    resolve_ipc_address,
)
from autosilenttrimmer.infrastructure.media.ffmpeg_locator import ManagedFFmpegLocator
from autosilenttrimmer.infrastructure.media.pyav_prober import PyAVMediaProber
from autosilenttrimmer.infrastructure.platform.paths import PlatformDirsPaths
from autosilenttrimmer.infrastructure.platform.shell.factory import create_shell_integration
from autosilenttrimmer.infrastructure.runtime.manifest_client import HttpManifestClient
from autosilenttrimmer.infrastructure.runtime.pack_manager import ManagedRuntimePackManager
from autosilenttrimmer.infrastructure.storage.job_manifest_repo import JsonJobManifestRepository
from autosilenttrimmer.infrastructure.storage.settings_repo import JsonSettingsRepository
from autosilenttrimmer.presentation.cli.parser import build_argument_parser
from autosilenttrimmer.presentation.cli.readiness_presenter import ReadinessPresenter
from autosilenttrimmer.presentation.cli.runtime_builder import (
    build_runtime_components,
    ensure_initial_settings,
    merge_cli_overrides,
)

logger = logging.getLogger("autosilenttrimmer")


def configure_logging(log_dir: str | None = None) -> None:
    """Configure append-only file logging preserving all historical log entries."""
    warnings.filterwarnings("ignore")
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
        handlers.append(
            logging.FileHandler(
                os.path.join(log_dir, "app.log"),
                mode="a",
                encoding="utf-8",
            )
        )
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] [pid:%(process)d] %(message)s",
        handlers=handlers,
        force=True,
    )


def _resolve_shim_executable() -> str:
    """Resolve sibling shim or current executable for Explorer right-click registration."""
    if getattr(sys, "frozen", False):
        install_dir = os.path.dirname(os.path.abspath(sys.executable))
        shim = os.path.join(install_dir, "trim-shim.exe")
        return shim if os.path.isfile(shim) else sys.executable
    return sys.executable


def _build_self_command(cli_flags: list[str]) -> list[str]:
    """Build subprocess command targeting frozen executable or current Python module."""
    exe = sys.executable
    if getattr(sys, "frozen", False):
        return [exe, *cli_flags]
    return [exe, "-m", "autosilenttrimmer", *cli_flags]


def _spawn_detached(cli_flags: list[str]) -> None:
    """Launch detached sibling process cleanly without console window flash."""
    cmd = _build_self_command(cli_flags)

    kwargs: dict[str, object] = {}
    if os.name == "nt":
        flags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(
            subprocess, "CREATE_NO_WINDOW", 0
        )
        kwargs["creationflags"] = flags
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kwargs)  # type: ignore[arg-type]


def format_version_banner() -> str:
    """Format canonical CLI --version output from branding metadata."""
    return f"{APP_NAME} {APP_VERSION}\n{COPYRIGHT_NOTICE}\nAuthor: {AUTHOR}\nGitHub: {GITHUB_URL}"


def run_cli(args: list[str] | None = None) -> int:
    """Run CLI entrypoint handling Tune, readiness, setup, shell integration, IPC, daemon, or job."""
    parser = build_argument_parser()
    parsed = parser.parse_args(args)

    if parsed.version:
        print(format_version_banner())
        return 0

    paths = PlatformDirsPaths()
    paths.ensure_all_dirs()
    configure_logging(paths.logs_dir)

    settings_repo = JsonSettingsRepository(paths.settings_file)
    base_settings = (
        settings_repo.load()
        if parsed.check
        else ensure_initial_settings(settings_repo, paths.settings_file)
    )
    effective_settings = merge_cli_overrides(base_settings, parsed)
    active_lang = parsed.lang or effective_settings.language or detect_system_language()
    localizer = Localizer(active_lang)
    event_bus = InMemoryEventBus()

    runtime_mgr = ManagedRuntimePackManager(
        runtime_packs_dir=paths.runtime_packs_dir,
        cache_dir=paths.cache_dir,
        manifest_client=HttpManifestClient(event_bus),
    )
    runtime_mgr.list_installed()

    locator = ManagedFFmpegLocator(paths.runtime_packs_dir)
    cap_prober = CrossPlatformCapabilityProber(locator, paths.capabilities_cache_file)
    shell_adapter = create_shell_integration()
    ipc_addr, ipc_fam = resolve_ipc_address(paths.cache_dir)

    try:
        # 1. Pre-flight system readiness check
        if parsed.check:
            diagnostics = [
                HardwareDiagnostic(),
                FFmpegDiagnostic(locator, effective_settings.ffmpeg_path),
                EngineDiagnostic(),
                ProductionReadinessDiagnostic(paths, cap_prober, runtime_mgr, shell_adapter),
            ]
            report = SystemReadinessUseCase(diagnostics).execute()
            ReadinessPresenter.present(report)
            return 0 if report.is_ready else 1

        # 2. Shell right-click registration / cleanup
        if parsed.register_shell:
            target_exe = _resolve_shim_executable()
            shell_adapter.register(
                target_exe, SHELL_CONTEXT_MENU_LABEL, TIER1_VIDEO_EXTENSIONS | VIDEO_EXTENSIONS
            )
            logger.info("Shell context menu registered targeting: %s", target_exe)
            return 0

        if parsed.unregister_shell:
            shell_adapter.unregister(TIER1_VIDEO_EXTENSIONS | VIDEO_EXTENSIONS)
            logger.info("Shell context menu removed cleanly.")
            return 0

        # 3. PyQt6 Tune Configuration UI (--tune)
        if parsed.tune:
            from autosilenttrimmer.presentation.tune.app_entry import run_tune_ui

            return run_tune_ui(
                settings_repo=settings_repo,
                settings_file_path=paths.settings_file,
                gateway_client=LocalIPCClient(ipc_addr, ipc_fam),
                shell_integration=shell_adapter,
                shim_executable_path=_resolve_shim_executable(),
            )

        # 3b. Read-only PyQt6 System Logs & Activity Viewer (--logs)
        if parsed.logs:
            from autosilenttrimmer.presentation.logs.app_entry import run_logs_ui

            return run_logs_ui(
                log_file_path=os.path.join(paths.logs_dir, "app.log"),
                gateway_client=LocalIPCClient(ipc_addr, ipc_fam),
                on_open_tune=lambda: _spawn_detached(["--tune"]),
            )

        # 3c. About Mortem Trimmer Dialog (--about)
        if parsed.about:
            from autosilenttrimmer.presentation.about_entry import run_about_ui

            return run_about_ui()

        # 3d. Native OS destination folder picker subprocess (--pick-folder)
        if parsed.pick_folder:
            from autosilenttrimmer.presentation.folder_picker import run_pick_folder_cli

            return run_pick_folder_cli(
                localizer,
                initial_dir=parsed.initial_dir,
                reason=parsed.pick_reason,
                target_path=parsed.target_path,
                free_bytes=parsed.free_bytes,
                required_bytes=parsed.required_bytes,
                result_file=parsed.pick_result_file,
            )

        # 4. Runtime Pack Setup / Offline Install
        if parsed.setup_runtime:
            ManageRuntimeUseCase(runtime_mgr, cap_prober).install_for_current_host(
                effective_settings.manifest_url, channel=effective_settings.update_channel
            )
            return 0

        if parsed.install_pack:
            rec = runtime_mgr.install_local_pack(parsed.install_pack, parsed.sha256)
            logger.info("Offline pack installed: %s (%s)", rec.pack_id, rec.install_dir)
            return 0

        # 5. Anonymized Diagnostics Bundle
        if parsed.export_diagnostics is not None:
            zip_out = parsed.export_diagnostics or None
            saved_zip = ExportDiagnosticsUseCase(
                paths, cap_prober, runtime_mgr, settings_repo
            ).execute(zip_out)
            logger.info("Diagnostics ZIP exported: %s", saved_zip)
            return 0

        # 6. Thin client enqueue mode (--enqueue <files>)
        if parsed.enqueue:
            client = LocalIPCClient(ipc_addr, ipc_fam)
            if not client.is_daemon_running():
                _spawn_detached(["--daemon", "--tray"])
            abs_paths = [os.path.abspath(p) for p in parsed.enqueue]
            if client.enqueue_paths(abs_paths):
                logger.info("Submitted %d item(s) cleanly to background queue.", len(abs_paths))
                return 0
            logger.error("Could not reach IPC daemon to enqueue paths.")
            return 1

        # 7. Core processing components
        comps = build_runtime_components(
            settings=effective_settings,
            locator=locator,
            localizer=localizer,
        )

        def _prompt_low_disk(req: DestinationPromptRequest) -> str | None:
            from autosilenttrimmer.presentation.folder_picker import (
                prompt_destination_via_subprocess,
            )

            return prompt_destination_via_subprocess(
                _build_self_command([]),
                initial_dir=os.path.dirname(req.target_path) or os.path.dirname(req.source_path),
                low_disk=True,
                target_path=req.target_path,
                free_bytes=req.free_bytes,
                required_bytes=req.required_bytes,
            )

        orchestrator = JobOrchestrator(
            media_manager=comps.media_manager,
            media_prober=PyAVMediaProber(),
            media_verifier=comps.media_verifier,
            trim_strategy=comps.trim_strategy,
            capability_prober=cap_prober,
            compute_backend=PolicyComputeBackend(cap_prober),
            event_bus=event_bus,
            config=comps.config,
            noise_reduction=comps.noise_reduction,
            visualizer=comps.visualizer,
            notifier=comps.notifier,
            manifest_repo=JsonJobManifestRepository(paths.jobs_dir),
            priority_ctrl=comps.priority_ctrl,
            on_destination_needed=(_prompt_low_disk if (parsed.daemon and parsed.tray) else None),
        )

        # 8. Persistent background daemon mode (--daemon [--tray])
        if parsed.daemon:
            orchestrator.start_background_worker()
            gateway = LocalIPCGateway(
                ipc_addr,
                ipc_fam,
                coalesce_window_sec=effective_settings.ipc_coalesce_window_sec,
            )
            tray_holder: list[object] = []

            def _reload_daemon_settings() -> object:
                fresh = merge_cli_overrides(settings_repo.load(), parsed)
                localizer.set_language(fresh.language)
                fresh_comps = build_runtime_components(
                    settings=fresh, locator=locator, localizer=localizer
                )
                if tray_holder:
                    fresh_comps.notifier.bind_tray(tray_holder[0])  # type: ignore[arg-type]
                orchestrator.reconfigure(
                    config=fresh_comps.config,
                    media_manager=fresh_comps.media_manager,
                    media_verifier=fresh_comps.media_verifier,
                    trim_strategy=fresh_comps.trim_strategy,
                    noise_reduction=fresh_comps.noise_reduction,
                    visualizer=fresh_comps.visualizer,
                    notifier=fresh_comps.notifier,
                    priority_ctrl=fresh_comps.priority_ctrl,
                )
                logger.info(
                    "Settings hot-reloaded (strategy=%s, vad=%s, nr=%s, lang=%s)",
                    fresh.trim_strategy,
                    fresh.vad_engine,
                    fresh.noise_reduction_method,
                    fresh.language,
                )
                return fresh

            def _on_batch(batch_paths: list[str]) -> None:
                logger.info("IPC batch dispatched (%d file(s)): %s", len(batch_paths), batch_paths)
                cur = _reload_daemon_settings()
                chosen_dir: str | None = None
                if parsed.tray and batch_paths:
                    from autosilenttrimmer.presentation.folder_picker import (
                        prompt_destination_via_subprocess,
                    )

                    default_dir = (
                        cur.output_custom_dir  # type: ignore[attr-defined]
                        if (
                            cur.output_location != "beside-source"  # type: ignore[attr-defined]
                            and cur.output_custom_dir  # type: ignore[attr-defined]
                            and os.path.isdir(cur.output_custom_dir)  # type: ignore[attr-defined]
                        )
                        else os.path.dirname(os.path.abspath(batch_paths[0]))
                    )
                    chosen_dir = prompt_destination_via_subprocess(
                        _build_self_command([]),
                        initial_dir=default_dir,
                    )
                    if not chosen_dir:
                        logger.info(
                            "Destination selection cancelled; skipped %d queued file(s).",
                            len(batch_paths),
                        )
                        return

                cmds = [
                    ProcessMediaCommand(
                        input_path=p,
                        output_dir=chosen_dir,
                        strategy=cur.trim_strategy,  # type: ignore[attr-defined]
                        vad_method=cur.vad_engine,  # type: ignore[attr-defined]
                        noise_reduction_method=cur.noise_reduction_method,  # type: ignore[attr-defined]
                        min_silence_gap=cur.min_silence_gap,  # type: ignore[attr-defined]
                        pad=cur.pad,  # type: ignore[attr-defined]
                        ffmpeg_path=cur.ffmpeg_path,  # type: ignore[attr-defined]
                        compute_policy=cur.compute_policy,  # type: ignore[attr-defined]
                        max_workers=cur.max_workers,  # type: ignore[attr-defined]
                        on_conflict=cur.on_conflict,  # type: ignore[attr-defined]
                        output_location=cur.output_location,  # type: ignore[attr-defined]
                        output_naming_template=cur.output_naming_template,  # type: ignore[attr-defined]
                    )
                    for p in batch_paths
                ]
                orchestrator.enqueue(cmds)

            gateway.start(_on_batch, on_reload_settings=_reload_daemon_settings)
            stop_requested = False

            def _quit_daemon() -> None:
                nonlocal stop_requested
                stop_requested = True
                orchestrator.stop_background_worker()
                gateway.stop()

            if parsed.tray:
                from autosilenttrimmer.presentation.tray.tray_app import PystrayTrayUI

                tray = PystrayTrayUI(event_bus, localizer)
                tray_holder.append(tray)
                comps.notifier.bind_tray(tray)
                tray.start(
                    on_open_tune=lambda: _spawn_detached(["--tune"]),
                    on_open_logs=lambda: _spawn_detached(["--logs"]),
                    on_pause_toggle=lambda: (
                        orchestrator.resume() if orchestrator.is_paused else orchestrator.pause()
                    ),
                    on_cancel_current=orchestrator.cancel_current,
                    on_export_diagnostics=lambda: ExportDiagnosticsUseCase(
                        paths, cap_prober, runtime_mgr, settings_repo
                    ).execute(),
                    on_toggle_language=localizer.toggle_language,
                    on_quit=_quit_daemon,
                    on_open_about=lambda: _spawn_detached(["--about"]),
                )

            try:
                while not stop_requested:
                    time.sleep(0.5)
            except KeyboardInterrupt:
                _quit_daemon()
            return 0

        # 9. Standard synchronous single-run execution (-i ... [-o ...])
        if not parsed.input:
            parser.error(
                "either --check, --tune, --logs, --daemon, --enqueue, or -i/--input is required"
            )

        use_case = ProcessMediaUseCase(
            media_manager=comps.media_manager,
            vad_strategy=comps.vad_detector,  # type: ignore[arg-type]
            noise_reduction_strategy=comps.noise_reduction,
            visualizer=comps.visualizer,
            capability_prober=cap_prober,
            compute_backend=PolicyComputeBackend(cap_prober),
            event_bus=event_bus,
            config=comps.config,
        )
        cmd = ProcessMediaCommand(
            input_path=parsed.input,
            output_path=parsed.output,
            noise_reduction_method=effective_settings.noise_reduction_method,
            vad_method=effective_settings.vad_engine,
            min_silence_gap=effective_settings.min_silence_gap,
            pad=effective_settings.pad,
            ffmpeg_path=comps.ffmpeg_path,
            strategy=effective_settings.trim_strategy,
            compute_policy=effective_settings.compute_policy,
            max_workers=effective_settings.max_workers,
            on_conflict=effective_settings.on_conflict,
            output_location=effective_settings.output_location,
            output_naming_template=effective_settings.output_naming_template,
        )
        result = use_case.execute(parsed.input, parsed.output, command=cmd)

        logger.info("Processing complete.")
        logger.info("Original duration : %.2f seconds", result.original_duration)
        logger.info("Final duration    : %.2f seconds", result.final_duration)
        logger.info(
            "Total reduction   : %.2f seconds (%.2f%% silence removed)",
            result.silence_removed_duration,
            result.reduction_percentage,
        )
        if result.manifest_path:
            logger.info("Transcript saved  : %s", result.manifest_path)
        if result.plot_path:
            logger.info("Visual plot saved : %s", result.plot_path)
        logger.info("Output artifact   : %s", result.output_path)
        return 0

    except AutoSilentTrimmerException as e:
        logger.error("Processing failed [%s]: %s", e.code.value, e)
        return 1
    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(run_cli())
