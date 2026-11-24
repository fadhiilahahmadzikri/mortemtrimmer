"""CLI runner and dependency wiring."""

from __future__ import annotations

import logging
import sys
import warnings

from autosilenttrimmer.application.use_cases.process_media import ProcessMediaUseCase
from autosilenttrimmer.application.use_cases.system_readiness import SystemReadinessUseCase
from autosilenttrimmer.core.config import (
    MediaProcessingConfig,
    NoiseReductionConfig,
    VADConfig,
)
from autosilenttrimmer.core.exceptions import AutoSilentTrimmerException
from autosilenttrimmer.infrastructure.diagnostics.engines import EngineDiagnostic
from autosilenttrimmer.infrastructure.diagnostics.ffmpeg import FFmpegDiagnostic
from autosilenttrimmer.infrastructure.diagnostics.hardware import HardwareDiagnostic
from autosilenttrimmer.infrastructure.media.ffmpeg_locator import ManagedFFmpegLocator
from autosilenttrimmer.infrastructure.media.ffmpeg_manager import FFmpegMediaManager
from autosilenttrimmer.infrastructure.noise_reduction.factory import NoiseReductionFactory
from autosilenttrimmer.infrastructure.vad.factory import VADFactory
from autosilenttrimmer.infrastructure.visualization.timeline_plotter import (
    MatplotlibTimelinePlotter,
)
from autosilenttrimmer.presentation.cli.parser import build_argument_parser
from autosilenttrimmer.presentation.cli.readiness_presenter import ReadinessPresenter

logger = logging.getLogger("autosilenttrimmer")


def configure_logging() -> None:
    """Configure minimal, consistent logging output."""
    warnings.filterwarnings("ignore")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def run_cli(args: list[str] | None = None) -> int:
    """Run CLI application parsing arguments, assembling dependencies, and executing use case."""
    configure_logging()
    parser = build_argument_parser()
    parsed_args = parser.parse_args(args)

    try:
        # Pre-flight system readiness check intercept
        if parsed_args.check:
            locator = ManagedFFmpegLocator()
            diagnostics = [
                HardwareDiagnostic(),
                FFmpegDiagnostic(locator, parsed_args.ffmpeg),
                EngineDiagnostic(),
            ]
            readiness_use_case = SystemReadinessUseCase(diagnostics)
            report = readiness_use_case.execute()
            ReadinessPresenter.present(report)
            return 0 if report.is_ready else 1

        if not parsed_args.input or not parsed_args.output:
            parser.error("the following arguments are required: -i/--input, -o/--output")

        vad_config = VADConfig(
            engine=parsed_args.vad,
            min_silence_gap=parsed_args.min_silence,
            pad=parsed_args.pad,
        )
        nr_config = NoiseReductionConfig(method=parsed_args.method)
        ffmpeg_locator = ManagedFFmpegLocator()
        resolved_ffmpeg = ffmpeg_locator.locate(parsed_args.ffmpeg)

        config = MediaProcessingConfig(
            ffmpeg_path=resolved_ffmpeg,
            vad=vad_config,
            noise_reduction=nr_config,
        )

        media_manager = FFmpegMediaManager(resolved_ffmpeg)
        vad_strategy = (
            VADFactory.create_vad(parsed_args.vad, config.vad)
            if parsed_args.vad != "none"
            else None
        )
        noise_reduction_strategy = (
            NoiseReductionFactory.create_noise_reduction(parsed_args.method, config.noise_reduction)
            if parsed_args.method != "none"
            else None
        )
        visualizer = (
            MatplotlibTimelinePlotter(config.visualizer) if vad_strategy is not None else None
        )

        use_case = ProcessMediaUseCase(
            media_manager=media_manager,
            vad_strategy=vad_strategy,
            noise_reduction_strategy=noise_reduction_strategy,
            visualizer=visualizer,
        )

        result = use_case.execute(
            input_path=parsed_args.input,
            output_path=parsed_args.output,
        )

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
        logger.error("Processing failed: %s", e)
        return 1
    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(run_cli())
