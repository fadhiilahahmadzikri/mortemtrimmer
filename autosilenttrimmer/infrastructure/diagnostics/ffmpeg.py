"""FFmpeg media subsystem diagnostics."""

from __future__ import annotations

import os
import subprocess

from autosilenttrimmer.core.exceptions import FFmpegExecutionException
from autosilenttrimmer.domain.contracts.diagnostic import ISystemDiagnostic
from autosilenttrimmer.domain.contracts.ffmpeg_locator import IFFmpegLocator
from autosilenttrimmer.domain.models.readiness import ReadinessItem, ReadinessStatus


class FFmpegDiagnostic(ISystemDiagnostic):
    """Verifies FFmpeg binary location, execution integrity, and codec support."""

    def __init__(self, locator: IFFmpegLocator, explicit_path: str | None = None) -> None:
        self._locator = locator
        self._explicit_path = explicit_path

    @property
    def category_name(self) -> str:
        return "Media Subsystem (FFmpeg)"

    def check(self) -> list[ReadinessItem]:
        items: list[ReadinessItem] = []

        try:
            ffmpeg_path = self._locator.locate(self._explicit_path)
            items.append(
                ReadinessItem(
                    component="FFmpeg Binary",
                    category=self.category_name,
                    status=ReadinessStatus.READY,
                    detail=f"Resolved at: {ffmpeg_path}",
                    is_critical=True,
                )
            )

            # Probe version
            env = os.environ.copy()
            ffmpeg_dir = os.path.dirname(ffmpeg_path)
            clean_path = [
                p for p in env.get("PATH", "").split(os.pathsep) if "venv" not in p.lower()
            ]
            env["PATH"] = os.pathsep.join([ffmpeg_dir] + clean_path)

            version_proc = subprocess.run(
                [ffmpeg_path, "-version"],
                capture_output=True,
                text=True,
                check=False,
                env=env,
            )
            if version_proc.returncode == 0:
                first_line = version_proc.stdout.splitlines()[0] if version_proc.stdout else "Available"
                items.append(
                    ReadinessItem(
                        component="FFmpeg Execution Integrity",
                        category=self.category_name,
                        status=ReadinessStatus.READY,
                        detail=first_line,
                        is_critical=True,
                    )
                )
            else:
                items.append(
                    ReadinessItem(
                        component="FFmpeg Execution Integrity",
                        category=self.category_name,
                        status=ReadinessStatus.FAILED,
                        detail=f"FFmpeg returned exit code {version_proc.returncode}",
                        is_critical=True,
                        remediation="Verify FFmpeg binary permissions and architecture compatibility.",
                    )
                )

        except FFmpegExecutionException as e:
            items.append(
                ReadinessItem(
                    component="FFmpeg Binary",
                    category=self.category_name,
                    status=ReadinessStatus.FAILED,
                    detail=str(e),
                    is_critical=True,
                    remediation="Install 'imageio-ffmpeg' (pip install imageio-ffmpeg) or ensure FFmpeg is in PATH.",
                )
            )

        return items
