"""FFmpeg locator implementation using managed binary, system PATH, and explicit path."""

from __future__ import annotations

import logging
import os
import shutil

from autosilenttrimmer.core.exceptions import FFmpegExecutionException
from autosilenttrimmer.domain.contracts.ffmpeg_locator import IFFmpegLocator

logger = logging.getLogger(__name__)


class ManagedFFmpegLocator(IFFmpegLocator):
    """Resolves FFmpeg executable dynamically via explicit path, imageio-ffmpeg, or system PATH."""

    def locate(self, explicit_path: str | None = None) -> str:
        # 1. User-supplied explicit path
        if explicit_path:
            if os.path.isfile(explicit_path):
                logger.info("Using explicitly configured FFmpeg: %s", explicit_path)
                return os.path.abspath(explicit_path)
            raise FFmpegExecutionException(
                f"Specified FFmpeg executable not found at path: {explicit_path}"
            )

        # 2. Managed binary from imageio-ffmpeg
        try:
            import imageio_ffmpeg

            managed_exe = imageio_ffmpeg.get_ffmpeg_exe()
            if managed_exe and os.path.isfile(managed_exe):
                logger.info("Using managed FFmpeg binary: %s", managed_exe)
                return managed_exe
        except ImportError:
            logger.debug("imageio-ffmpeg is not installed, falling back to system PATH.")

        # 3. System PATH lookup
        system_exe = shutil.which("ffmpeg")
        if system_exe and os.path.isfile(system_exe):
            logger.info("Using system PATH FFmpeg: %s", system_exe)
            return system_exe

        raise FFmpegExecutionException(
            "FFmpeg executable could not be located. "
            "Please install 'imageio-ffmpeg' (pip install imageio-ffmpeg), "
            "ensure FFmpeg is available in system PATH, "
            "or specify the path explicitly via '--ffmpeg <path>'."
        )
