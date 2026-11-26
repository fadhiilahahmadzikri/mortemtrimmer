# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Fadhiilah Ahmad Zikri
"""Non-destructive output path resolution and atomic file promotion."""

from __future__ import annotations

import os
import shutil
from collections.abc import Callable
from dataclasses import replace
from typing import TYPE_CHECKING

from autosilenttrimmer.core.config import OutputPolicyConfig
from autosilenttrimmer.core.constants import (
    DEFAULT_ON_CONFLICT,
    DEFAULT_OUTPUT_LOCATION,
    DEFAULT_OUTPUT_NAMING_TEMPLATE,
    DISK_SPACE_SAFETY_FACTOR,
    MIN_FREE_DISK_BYTES,
    VIDEO_EXTENSIONS,
)
from autosilenttrimmer.core.exceptions import (
    DiskFullException,
    FormatMismatchException,
    JobCancelledException,
)
from autosilenttrimmer.domain.models.processing_command import (
    DestinationPromptRequest,
    ProcessMediaCommand,
)

if TYPE_CHECKING:
    from autosilenttrimmer.domain.models.media_probe import MediaProbeInfo


class OutputPathResolver:
    """Resolves safe non-destructive output paths and atomic staging locations."""

    @staticmethod
    def resolve(
        source_path: str,
        explicit_output_path: str | None = None,
        policy: OutputPolicyConfig | None = None,
        output_dir: str | None = None,
    ) -> str:
        """Compute non-destructive final output path honoring collision policy (Doc 01 A4, P7)."""
        abs_source = os.path.abspath(source_path)
        src_dir, src_filename = os.path.split(abs_source)
        src_name, src_ext = os.path.splitext(src_filename)

        if explicit_output_path:
            abs_out = os.path.abspath(explicit_output_path)
            if os.path.normcase(abs_out) == os.path.normcase(abs_source):
                raise FormatMismatchException(
                    f"Output path cannot overwrite source file: {abs_source}"
                )
            return abs_out

        cfg = policy or OutputPolicyConfig()
        if output_dir and output_dir.strip():
            target_dir = os.path.abspath(output_dir.strip())
        elif cfg.location != DEFAULT_OUTPUT_LOCATION and cfg.custom_dir:
            target_dir = os.path.abspath(cfg.custom_dir)
        else:
            target_dir = src_dir
        os.makedirs(target_dir, exist_ok=True)

        template = cfg.naming_template or DEFAULT_OUTPUT_NAMING_TEMPLATE
        ext_clean = src_ext.lstrip(".")
        candidate_name = template.format(name=src_name, ext=ext_clean)
        candidate = os.path.join(target_dir, candidate_name)

        if cfg.on_conflict == "overwrite" and os.path.normcase(candidate) != os.path.normcase(
            abs_source
        ):
            return candidate

        # Default increment collision avoidance (Doc 01 §6.1)
        if cfg.on_conflict in {DEFAULT_ON_CONFLICT, "ask"} or os.path.normcase(
            candidate
        ) == os.path.normcase(abs_source):
            base_stem, out_ext = os.path.splitext(candidate_name)
            counter = 1
            while os.path.exists(candidate) or os.path.normcase(candidate) == os.path.normcase(
                abs_source
            ):
                candidate = os.path.join(target_dir, f"{base_stem}_{counter}{out_ext}")
                counter += 1

        return candidate

    @staticmethod
    def make_staging_path(final_output_path: str, job_id: str) -> str:
        """Create same-volume staging path preserving container extension for FFmpeg muxers."""
        out_dir, filename = os.path.split(os.path.abspath(final_output_path))
        stem, ext = os.path.splitext(filename)
        os.makedirs(out_dir, exist_ok=True)
        return os.path.join(out_dir, f".{stem}.{job_id[:8]}.tmp{ext}")

    @staticmethod
    def ensure_disk_space(
        target_path: str,
        source_size_bytes: int,
        safety_factor: float = DISK_SPACE_SAFETY_FACTOR,
    ) -> None:
        """Pre-flight free disk space check (Doc 01 §7.5)."""
        target_dir = os.path.dirname(os.path.abspath(target_path)) or "."
        usage = shutil.disk_usage(target_dir)
        required = max(MIN_FREE_DISK_BYTES, int(source_size_bytes * safety_factor))
        if usage.free < required:
            raise DiskFullException(
                f"Insufficient disk space in '{target_dir}': "
                f"{usage.free / (1024**2):.1f} MB free, "
                f"{required / (1024**2):.1f} MB required.",
                context={"free_bytes": usage.free, "required_bytes": required},
            )

    @staticmethod
    def resolve_with_disk_guard(
        *,
        probe: MediaProbeInfo,
        command: ProcessMediaCommand,
        policy: OutputPolicyConfig,
        on_destination_needed: Callable[[DestinationPromptRequest], str | None] | None = None,
    ) -> str:
        """Resolve non-destructive output and enforce free disk space with optional interactive relocation."""
        active_cmd = command
        while True:
            if active_cmd.output_path:
                out_ext = os.path.splitext(active_cmd.output_path.lower())[1]
                if not probe.is_video and out_ext and out_ext in VIDEO_EXTENSIONS:
                    raise FormatMismatchException(
                        f"Input is audio '{probe.extension}' but output '{out_ext}' is video."
                    )
            candidate = OutputPathResolver.resolve(
                probe.path,
                active_cmd.output_path,
                policy,
                output_dir=active_cmd.output_dir,
            )
            try:
                OutputPathResolver.ensure_disk_space(
                    candidate,
                    probe.file_size_bytes,
                    safety_factor=policy.disk_space_safety_factor,
                )
                return candidate
            except DiskFullException as exc:
                if on_destination_needed is None:
                    raise
                req = DestinationPromptRequest(
                    source_path=probe.path,
                    target_path=candidate,
                    free_bytes=int(exc.context.get("free_bytes", 0)),
                    required_bytes=int(exc.context.get("required_bytes", 0)),
                )
                picked = on_destination_needed(req)
                if not picked:
                    raise JobCancelledException(
                        "Job cancelled: no destination folder selected."
                    ) from exc
                chosen_dir = os.path.abspath(picked)
                next_explicit = (
                    os.path.join(chosen_dir, os.path.basename(active_cmd.output_path))
                    if active_cmd.output_path
                    else None
                )
                active_cmd = replace(active_cmd, output_dir=chosen_dir, output_path=next_explicit)

    @staticmethod
    def atomic_publish(staging_path: str, final_output_path: str) -> None:
        """Atomically promote verified staging output to final path."""
        os.replace(staging_path, final_output_path)
