"""CLI runner, composition root, IPC dispatch, and daemon lifecycle controller."""

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
from autosilenttrimmer.core.config import (
    ExecutionConfig,
    MediaProcessingConfig,
    NoiseReductionConfig,
    UIConfig,
    VADConfig,
)
from autosilenttrimmer.core.constants import APP_NAME, TIER1_VIDEO_EXTENSIONS, VIDEO_EXTENSIONS
from autosilenttrimmer.core.exceptions import AutoSilentTrimmerException
from autosilenttrimmer.core.i18n import Localizer, detect_system_language
from autosilenttrimmer.domain.models.processing_command import ProcessMediaCommand
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
from autosilenttrimmer.infrastructure.media.ffmpeg_manager import FFmpegMediaManager
from autosilenttrimmer.infrastructure.media.pyav_prober import PyAVMediaProber
from autosilenttrimmer.infrastructure.media.pyav_verifier import PyAVMediaVerifier
from autosilenttrimmer.infrastructure.noise_reduction.factory import NoiseReductionFactory
from autosilenttrimmer.infrastructure.notify.composite_notifier import CompositeNotifier
from autosilenttrimmer.infrastructure.notify.desktop_notifier_adapter import DesktopNotifierAdapter
from autosilenttrimmer.infrastructure.platform.paths import PlatformDirsPaths
from autosilenttrimmer.infrastructure.platform.priority import PsutilPriorityController
from autosilenttrimmer.infrastructure.platform.shell.factory import create_shell_integration
from autosilenttrimmer.infrastructure.runtime.manifest_client import HttpManifestClient
from autosilenttrimmer.infrastructure.runtime.pack_manager import ManagedRuntimePackManager
from autosilenttrimmer.infrastructure.storage.job_manifest_repo import JsonJobManifestRepository
from autosilenttrimmer.infrastructure.storage.settings_repo import JsonSettingsRepository
from autosilenttrimmer.infrastructure.strategies.auto_silence import AutoSilenceTrimStrategy
from autosilenttrimmer.infrastructure.strategies.manual_range import ManualRangeTrimStrategy
from autosilenttrimmer.infrastructure.vad.factory import VADFactory
from autosilenttrimmer.infrastructure.visualization.timeline_plotter import (
    MatplotlibTimelinePlotter,
)
from autosilenttrimmer.presentation.cli.parser import build_argument_parser
from autosilenttrimmer.presentation.cli.readiness_presenter import ReadinessPresenter

logger = logging.getLogger("autosilenttrimmer")


def configure_logging(log_dir: str | None = None) -> None:
    """Configure minimal console and rotating-safe file logging."""
    warnings.filterwarnings("ignore")
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
        handlers.append(logging.FileHandler(os.path.join(log_dir, "app.log"), encoding="utf-8"))
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
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


def _spawn_detached_daemon(extra_args: list[str] | None = None) -> None:
    """Launch background daemon without terminal popup window."""
    exe = sys.executable
    if getattr(sys, "frozen", False):
        cmd = [exe, "--daemon", "--tray", *(extra_args or [])]
    else:
        cmd = [exe, "-m", "autosilenttrimmer", "--daemon", "--tray", *(extra_args or [])]

    kwargs: dict[str, object] = {}
    if os.name == "nt":
        flags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(
            subprocess, "CREATE_NO_WINDOW", 0
        )
        kwargs["creationflags"] = flags
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kwargs)  # type: ignore[arg-type]


def run_cli(args: list[str] | None = None) -> int:
    """Run CLI entrypoint handling readiness, setup, shell integration, IPC, daemon, or job."""
    paths = PlatformDirsPaths()
    paths.ensure_all_dirs()
    configure_logging(paths.logs_dir)

    parser = build_argument_parser()
    parsed = parser.parse_args(args)

    settings_repo = JsonSettingsRepository(paths.settings_file)
    settings = settings_repo.load()
    active_lang = parsed.lang or settings.language or detect_system_language()
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

    try:
        # 1. Pre-flight system readiness check
        if parsed.check:
            diagnostics = [
                HardwareDiagnostic(),
                FFmpegDiagnostic(locator, parsed.ffmpeg),
                EngineDiagnostic(),
                ProductionReadinessDiagnostic(paths, cap_prober, runtime_mgr, shell_adapter),
            ]
            report = SystemReadinessUseCase(diagnostics).execute()
            ReadinessPresenter.present(report)
            return 0 if report.is_ready else 1

        # 2. Shell right-click registration / cleanup
        if parsed.register_shell:
            target_exe = _resolve_shim_executable()
            shell_adapter.register(target_exe, APP_NAME, TIER1_VIDEO_EXTENSIONS | VIDEO_EXTENSIONS)
            logger.info("Shell context menu registered targeting: %s", target_exe)
            return 0

        if parsed.unregister_shell:
            shell_adapter.unregister(TIER1_VIDEO_EXTENSIONS | VIDEO_EXTENSIONS)
            logger.info("Shell context menu removed cleanly.")
            return 0

        # 3. Runtime Pack Setup / Offline Install
        if parsed.setup_runtime:
            ManageRuntimeUseCase(runtime_mgr, cap_prober).install_for_current_host(
                parsed.manifest_url, channel=parsed.channel
            )
            return 0

        if parsed.install_pack:
            rec = runtime_mgr.install_local_pack(parsed.install_pack, parsed.sha256)
            logger.info("Offline pack installed: %s (%s)", rec.pack_id, rec.install_dir)
            return 0

        # 4. Anonymized Diagnostics Bundle
        if parsed.export_diagnostics is not None:
            zip_out = parsed.export_diagnostics or None
            saved_zip = ExportDiagnosticsUseCase(
                paths, cap_prober, runtime_mgr, settings_repo
            ).execute(zip_out)
            logger.info("Diagnostics ZIP exported: %s", saved_zip)
            return 0

        # 5. Thin client enqueue mode (--enqueue <files>)
        ipc_addr, ipc_fam = resolve_ipc_address(paths.cache_dir)
        if parsed.enqueue:
            client = LocalIPCClient(ipc_addr, ipc_fam)
            if not client.is_daemon_running():
                _spawn_detached_daemon()
            abs_paths = [os.path.abspath(p) for p in parsed.enqueue]
            if client.enqueue_paths(abs_paths):
                logger.info("Submitted %d item(s) cleanly to background queue.", len(abs_paths))
                return 0
            logger.error("Could not reach IPC daemon to enqueue paths.")
            return 1

        # 6. Core processing assembly
        resolved_ffmpeg = locator.locate(parsed.ffmpeg)
        vad_cfg = VADConfig(
            engine=parsed.vad,
            min_silence_gap=parsed.min_silence,
            pad=parsed.pad,
        )
        nr_cfg = NoiseReductionConfig(method=parsed.method)
        exec_cfg = ExecutionConfig(
            strategy=parsed.strategy,
            compute_policy=parsed.gpu_policy,
            max_workers=parsed.max_workers,
            background_priority=settings.background_priority,
        )
        ui_cfg = UIConfig(
            language=active_lang,
            enable_notifications=settings.enable_notifications,
            generate_visual_artifacts=parsed.visual_plot or settings.generate_visual_artifacts,
        )
        config = MediaProcessingConfig(
            ffmpeg_path=resolved_ffmpeg,
            vad=vad_cfg,
            noise_reduction=nr_cfg,
            execution=exec_cfg,
            ui=ui_cfg,
        )

        media_manager = FFmpegMediaManager(resolved_ffmpeg)
        vad_detector = (
            VADFactory.create_vad(parsed.vad, config.vad) if parsed.vad != "none" else None
        )
        nr_strategy = (
            NoiseReductionFactory.create_noise_reduction(parsed.method, config.noise_reduction)
            if parsed.method != "none"
            else None
        )
        visualizer = (
            MatplotlibTimelinePlotter(config.visualizer)
            if (ui_cfg.generate_visual_artifacts and vad_detector is not None)
            else None
        )
        trim_strategy = (
            ManualRangeTrimStrategy()
            if parsed.strategy == "manual-range"
            else (
                AutoSilenceTrimStrategy(vad_detector)
                if vad_detector is not None
                else ManualRangeTrimStrategy()
            )
        )

        notifier = CompositeNotifier(
            DesktopNotifierAdapter(localizer, enabled=ui_cfg.enable_notifications),
            localizer,
        )
        orchestrator = JobOrchestrator(
            media_manager=media_manager,
            media_prober=PyAVMediaProber(),
            media_verifier=PyAVMediaVerifier(),
            trim_strategy=trim_strategy,
            capability_prober=cap_prober,
            compute_backend=PolicyComputeBackend(cap_prober),
            event_bus=event_bus,
            config=config,
            noise_reduction=nr_strategy,
            visualizer=visualizer,
            notifier=notifier,
            manifest_repo=JsonJobManifestRepository(paths.jobs_dir),
            priority_ctrl=PsutilPriorityController(),
        )

        # 7. Persistent background daemon mode (--daemon [--tray])
        if parsed.daemon:
            orchestrator.start_background_worker()
            gateway = LocalIPCGateway(ipc_addr, ipc_fam)

            def _on_batch(batch_paths: list[str]) -> None:
                cmds = [
                    ProcessMediaCommand(
                        input_path=p,
                        strategy=parsed.strategy,
                        vad_method=parsed.vad,
                        noise_reduction_method=parsed.method,
                        compute_policy=parsed.gpu_policy,
                        max_workers=parsed.max_workers,
                    )
                    for p in batch_paths
                ]
                orchestrator.enqueue(cmds)

            gateway.start(_on_batch)
            stop_requested = False

            def _quit_daemon() -> None:
                nonlocal stop_requested
                stop_requested = True
                orchestrator.stop_background_worker()
                gateway.stop()

            if parsed.tray:
                from autosilenttrimmer.presentation.tray.tray_app import PystrayTrayUI

                tray = PystrayTrayUI(event_bus, localizer)
                notifier.bind_tray(tray)
                tray.start(
                    on_pause_toggle=lambda: (
                        orchestrator.resume() if orchestrator.is_paused else orchestrator.pause()
                    ),
                    on_cancel_current=orchestrator.cancel_current,
                    on_export_diagnostics=lambda: ExportDiagnosticsUseCase(
                        paths, cap_prober, runtime_mgr, settings_repo
                    ).execute(),
                    on_toggle_language=localizer.toggle_language,
                    on_quit=_quit_daemon,
                )

            try:
                while not stop_requested:
                    time.sleep(0.5)
            except KeyboardInterrupt:
                _quit_daemon()
            return 0

        # 8. Standard synchronous single-run execution (-i ... [-o ...])
        if not parsed.input:
            parser.error("either --check, --daemon, --enqueue, or -i/--input is required")

        use_case = ProcessMediaUseCase(
            media_manager=media_manager,
            vad_strategy=vad_detector,
            noise_reduction_strategy=nr_strategy,
            visualizer=visualizer,
            capability_prober=cap_prober,
            compute_backend=PolicyComputeBackend(cap_prober),
            event_bus=event_bus,
            config=config,
        )
        cmd = ProcessMediaCommand(
            input_path=parsed.input,
            output_path=parsed.output,
            noise_reduction_method=parsed.method,
            vad_method=parsed.vad,
            min_silence_gap=parsed.min_silence,
            pad=parsed.pad,
            ffmpeg_path=resolved_ffmpeg,
            strategy=parsed.strategy,
            compute_policy=parsed.gpu_policy,
            max_workers=parsed.max_workers,
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
