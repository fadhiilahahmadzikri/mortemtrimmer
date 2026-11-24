"""Shared composition builder resolving UserSettings + CLI overrides into pipeline actors."""

from __future__ import annotations

import argparse
import importlib.util
import logging
import os
from dataclasses import dataclass, replace

from autosilenttrimmer.core.config import MediaProcessingConfig
from autosilenttrimmer.core.i18n import Localizer
from autosilenttrimmer.domain.contracts.compute import IProcessPriorityController
from autosilenttrimmer.domain.contracts.ffmpeg_locator import IFFmpegLocator
from autosilenttrimmer.domain.contracts.media_manager import IMediaManager
from autosilenttrimmer.domain.contracts.media_verifier import IMediaVerifier
from autosilenttrimmer.domain.contracts.noise_reduction import INoiseReductionStrategy
from autosilenttrimmer.domain.contracts.storage import ISettingsRepository
from autosilenttrimmer.domain.contracts.trim_strategy import ITrimStrategy
from autosilenttrimmer.domain.contracts.visualizer import IVisualizer
from autosilenttrimmer.domain.models.settings import UserSettings
from autosilenttrimmer.infrastructure.media.ffmpeg_manager import FFmpegMediaManager
from autosilenttrimmer.infrastructure.media.pyav_verifier import PyAVMediaVerifier
from autosilenttrimmer.infrastructure.noise_reduction.factory import NoiseReductionFactory
from autosilenttrimmer.infrastructure.notify.composite_notifier import CompositeNotifier
from autosilenttrimmer.infrastructure.notify.desktop_notifier_adapter import DesktopNotifierAdapter
from autosilenttrimmer.infrastructure.platform.priority import PsutilPriorityController
from autosilenttrimmer.infrastructure.strategies.auto_silence import AutoSilenceTrimStrategy
from autosilenttrimmer.infrastructure.strategies.manual_range import ManualRangeTrimStrategy
from autosilenttrimmer.infrastructure.vad.factory import VADFactory
from autosilenttrimmer.infrastructure.visualization.timeline_plotter import (
    MatplotlibTimelinePlotter,
)


@dataclass(frozen=True)
class RuntimeComponents:
    """Assembled runtime actors synchronized with current UserSettings."""

    settings: UserSettings
    config: MediaProcessingConfig
    ffmpeg_path: str
    media_manager: IMediaManager
    media_verifier: IMediaVerifier
    trim_strategy: ITrimStrategy
    vad_detector: object | None
    noise_reduction: INoiseReductionStrategy | None
    visualizer: IVisualizer | None
    notifier: CompositeNotifier
    priority_ctrl: IProcessPriorityController


def ensure_initial_settings(
    settings_repo: ISettingsRepository, settings_file_path: str
) -> UserSettings:
    """Persist explicit initial settings on first run so Lean Core uses available Energy VAD."""
    if os.path.isfile(settings_file_path):
        return settings_repo.load()
    has_torch = importlib.util.find_spec("torch") is not None
    initial = UserSettings() if has_torch else UserSettings(vad_engine="energy")
    settings_repo.save(initial)
    logging.getLogger("autosilenttrimmer").info(
        "Initialized default settings.json (vad=%s, torch_installed=%s)",
        initial.vad_engine,
        has_torch,
    )
    return initial


def merge_cli_overrides(base: UserSettings, parsed: argparse.Namespace) -> UserSettings:
    """Apply explicit non-None CLI flags onto persisted UserSettings."""
    updates: dict[str, object] = {}
    if getattr(parsed, "lang", None) is not None:
        updates["language"] = parsed.lang
    if getattr(parsed, "method", None) is not None:
        updates["noise_reduction_method"] = parsed.method
    if getattr(parsed, "vad", None) is not None:
        updates["vad_engine"] = parsed.vad
    if getattr(parsed, "strategy", None) is not None:
        updates["trim_strategy"] = parsed.strategy
    if getattr(parsed, "gpu_policy", None) is not None:
        updates["compute_policy"] = parsed.gpu_policy
    if getattr(parsed, "max_workers", None) is not None:
        updates["max_workers"] = parsed.max_workers
    if getattr(parsed, "min_silence", None) is not None:
        updates["min_silence_gap"] = parsed.min_silence
    if getattr(parsed, "pad", None) is not None:
        updates["pad"] = parsed.pad
    if getattr(parsed, "ffmpeg", None) is not None:
        updates["ffmpeg_path"] = parsed.ffmpeg
    if getattr(parsed, "visual_plot", None) is True:
        updates["generate_visual_artifacts"] = True
    if getattr(parsed, "channel", None) is not None:
        updates["update_channel"] = parsed.channel
    if getattr(parsed, "manifest_url", None) is not None:
        updates["manifest_url"] = parsed.manifest_url
    return replace(base, **updates) if updates else base


def build_runtime_components(
    *,
    settings: UserSettings,
    locator: IFFmpegLocator,
    localizer: Localizer,
) -> RuntimeComponents:
    """Construct complete runtime dependencies from resolved UserSettings."""
    resolved_ffmpeg = locator.locate(settings.ffmpeg_path)
    config = settings.to_processing_config(ffmpeg_override=resolved_ffmpeg)

    media_manager = FFmpegMediaManager(resolved_ffmpeg, audio_config=config.audio)
    verifier = PyAVMediaVerifier(
        duration_tolerance_sec=config.execution.verify_duration_tolerance_sec
    )

    vad_detector = (
        VADFactory.create_vad(settings.vad_engine, config.vad)
        if settings.vad_engine != "none"
        else None
    )
    nr_strategy = (
        NoiseReductionFactory.create_noise_reduction(
            settings.noise_reduction_method, config.noise_reduction
        )
        if settings.noise_reduction_method != "none"
        else None
    )
    visualizer = (
        MatplotlibTimelinePlotter(config.visualizer)
        if (config.ui.generate_visual_artifacts and vad_detector is not None)
        else None
    )
    trim_strategy: ITrimStrategy = (
        ManualRangeTrimStrategy(frame_accurate=config.execution.frame_accurate)
        if settings.trim_strategy == "manual-range"
        else (
            AutoSilenceTrimStrategy(vad_detector)
            if vad_detector is not None
            else ManualRangeTrimStrategy(frame_accurate=config.execution.frame_accurate)
        )
    )

    notifier = CompositeNotifier(
        DesktopNotifierAdapter(localizer, enabled=config.ui.enable_notifications),
        localizer,
    )
    priority_ctrl = PsutilPriorityController(
        low_battery_threshold_percent=config.execution.low_battery_threshold_percent
    )

    return RuntimeComponents(
        settings=settings,
        config=config,
        ffmpeg_path=resolved_ffmpeg,
        media_manager=media_manager,
        media_verifier=verifier,
        trim_strategy=trim_strategy,
        vad_detector=vad_detector,
        noise_reduction=nr_strategy,
        visualizer=visualizer,
        notifier=notifier,
        priority_ctrl=priority_ctrl,
    )
