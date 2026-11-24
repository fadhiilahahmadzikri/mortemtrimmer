"""Non-destructive output path resolution and atomic file promotion."""

from __future__ import annotations

import os
import shutil

from autosilenttrimmer.core.config import OutputPolicyConfig
from autosilenttrimmer.core.constants import (
    DEFAULT_ON_CONFLICT,
    DEFAULT_OUTPUT_LOCATION,
    DEFAULT_OUTPUT_NAMING_TEMPLATE,
    DISK_SPACE_SAFETY_FACTOR,
    MIN_FREE_DISK_BYTES,
)
from autosilenttrimmer.core.exceptions import DiskFullException, FormatMismatchException


class OutputPathResolver:
    """Resolves safe non-destructive output paths and atomic staging locations."""

    @staticmethod
    def resolve(
        source_path: str,
        explicit_output_path: str | None = None,
        policy: OutputPolicyConfig | None = None,
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
        target_dir = (
            os.path.abspath(cfg.custom_dir)
            if cfg.location != DEFAULT_OUTPUT_LOCATION and cfg.custom_dir
            else src_dir
        )
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
    def atomic_publish(staging_path: str, final_output_path: str) -> None:
        """Atomically promote verified staging output to final path."""
        os.replace(staging_path, final_output_path)
