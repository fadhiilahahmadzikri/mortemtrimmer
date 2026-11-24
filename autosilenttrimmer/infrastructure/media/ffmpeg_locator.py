# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Fadhiilah Ahmad Zikri
"""FFmpeg locator checking explicit path, managed Runtime Pack, imageio-ffmpeg, and PATH."""

from __future__ import annotations

import logging
import os
import shutil

from autosilenttrimmer.core.exceptions import FFmpegExecutionException
from autosilenttrimmer.domain.contracts.ffmpeg_locator import IFFmpegLocator
from autosilenttrimmer.domain.models.compute import PlatformSpec

logger = logging.getLogger(__name__)


class ManagedFFmpegLocator(IFFmpegLocator):
    """Resolves FFmpeg via explicit path, installed Runtime Pack, imageio-ffmpeg, or PATH."""

    def __init__(self, runtime_packs_dir: str | None = None) -> None:
        self._runtime_packs_dir = runtime_packs_dir

    def locate(self, explicit_path: str | None = None) -> str:
        # 1. User-supplied explicit path
        if explicit_path:
            if os.path.isfile(explicit_path):
                logger.info("Using explicitly configured FFmpeg: %s", explicit_path)
                return os.path.abspath(explicit_path)
            raise FFmpegExecutionException(
                f"Specified FFmpeg executable not found at path: {explicit_path}"
            )

        # 2. Managed Runtime Pack binary (downloaded via IRuntimeManager)
        pack_exe = self._find_runtime_pack_ffmpeg()
        if pack_exe:
            logger.info("Using managed Runtime Pack FFmpeg: %s", pack_exe)
            return pack_exe

        # 3. Managed binary from imageio-ffmpeg wheel
        try:
            import imageio_ffmpeg

            managed_exe = imageio_ffmpeg.get_ffmpeg_exe()
            if managed_exe and os.path.isfile(managed_exe):
                logger.info("Using managed FFmpeg binary: %s", managed_exe)
                return managed_exe
        except ImportError:
            logger.debug("imageio-ffmpeg is not installed, falling back to system PATH.")

        # 4. System PATH lookup
        system_exe = shutil.which("ffmpeg")
        if system_exe and os.path.isfile(system_exe):
            logger.info("Using system PATH FFmpeg: %s", system_exe)
            return system_exe

        raise FFmpegExecutionException(
            "FFmpeg executable could not be located. "
            "Run runtime setup, install 'imageio-ffmpeg', or ensure FFmpeg is in PATH."
        )

    def _find_runtime_pack_ffmpeg(self) -> str | None:
        if not self._runtime_packs_dir:
            return None
        tag = PlatformSpec.current().platform_tag
        exe_name = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
        for sub in ("bin", ""):
            candidate = os.path.join(
                self._runtime_packs_dir, f"ffmpeg-{tag}", "current", sub, exe_name
            )
            if os.path.isfile(candidate):
                return os.path.abspath(candidate)
        return None
