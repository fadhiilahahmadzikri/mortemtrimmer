# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Fadhiilah Ahmad Zikri
"""Core audio, AI models, and C++/DLL integrity diagnostics."""

from __future__ import annotations

import logging

from autosilenttrimmer.domain.contracts.diagnostic import ISystemDiagnostic
from autosilenttrimmer.domain.models.readiness import ReadinessItem, ReadinessStatus

logger = logging.getLogger(__name__)


class EngineDiagnostic(ISystemDiagnostic):
    """Probes SoundFile, PyAV, Torchaudio DLL linking, noisereduce, DeepFilterNet3, and Whisper."""

    @property
    def category_name(self) -> str:
        return "Audio & AI Engine Integrations"

    def check(self) -> list[ReadinessItem]:
        items: list[ReadinessItem] = []

        # 1. Core Audio I/O & Energy VAD (always required in Lean Core)
        try:
            import av
            import numpy
            import soundfile

            items.append(
                ReadinessItem(
                    component="Core Audio & Media I/O",
                    category=self.category_name,
                    status=ReadinessStatus.READY,
                    detail=f"PyAV {av.__version__}, libsndfile, NumPy {numpy.__version__}",
                    is_critical=True,
                )
            )
            items.append(
                ReadinessItem(
                    component="Energy Acoustic VAD",
                    category=self.category_name,
                    status=ReadinessStatus.READY,
                    detail="Zero-dependency signal frame VAD operational",
                    is_critical=True,
                )
            )
        except ImportError as e:
            items.append(
                ReadinessItem(
                    component="Core Audio & Media I/O",
                    category=self.category_name,
                    status=ReadinessStatus.FAILED,
                    detail=f"Missing core dependency: {e}",
                    is_critical=True,
                    remediation="Reinstall core application package or dependencies.",
                )
            )

        # 2. Torchaudio & C++ DLL integrity (WinError 127 guard; optional in Lean Core)
        torch_available = False
        try:
            import torch
            import torchaudio

            torch_available = True
            items.append(
                ReadinessItem(
                    component="Torchaudio Runtime",
                    category=self.category_name,
                    status=ReadinessStatus.READY,
                    detail=f"Torchaudio {torchaudio.__version__} (DLLs verified)",
                    is_critical=False,
                )
            )
        except OSError as e:
            detail = (
                "Architectural DLL conflict detected (WinError 127)"
                if "WinError 127" in str(e)
                else f"Torchaudio DLL load error: {e}"
            )
            items.append(
                ReadinessItem(
                    component="Torchaudio Runtime",
                    category=self.category_name,
                    status=ReadinessStatus.FAILED,
                    detail=detail,
                    is_critical=True,
                    remediation="Run: pip uninstall torch torchaudio -y && pip install torch torchaudio",
                )
            )
        except ImportError:
            try:
                import torch

                torch_available = True
            except ImportError:
                torch_available = False
            items.append(
                ReadinessItem(
                    component="Torchaudio Runtime",
                    category=self.category_name,
                    status=ReadinessStatus.OPTIONAL_MISSING,
                    detail="Torchaudio runtime pack not installed (optional for Core Energy VAD).",
                    is_critical=False,
                    remediation="Run --setup-runtime or install AI extras to enable neural audio models.",
                )
            )

        # 3. Silero VAD (Neural Acoustic VAD)
        items.append(
            ReadinessItem(
                component="Silero Acoustic VAD",
                category=self.category_name,
                status=ReadinessStatus.READY
                if torch_available
                else ReadinessStatus.OPTIONAL_MISSING,
                detail=(
                    "PyTorch Hub Silero VAD integration ready"
                    if torch_available
                    else "Requires AI Runtime Pack (PyTorch)"
                ),
                is_critical=False,
                remediation=None
                if torch_available
                else "Run: autosilenttrimmer-cli --setup-runtime",
            )
        )

        # 4. Spectral Gating (noisereduce)
        try:
            import noisereduce

            items.append(
                ReadinessItem(
                    component="Spectral Gating Denoiser",
                    category=self.category_name,
                    status=ReadinessStatus.AVAILABLE,
                    detail="noisereduce operational",
                    is_critical=False,
                )
            )
        except ImportError:
            items.append(
                ReadinessItem(
                    component="Spectral Gating Denoiser",
                    category=self.category_name,
                    status=ReadinessStatus.OPTIONAL_MISSING,
                    detail="noisereduce not installed in Lean Core",
                    is_critical=False,
                    remediation="Run --setup-runtime or: pip install noisereduce",
                )
            )

        # 5. DeepFilterNet3 (Neural Noise Reduction)
        try:
            import df

            items.append(
                ReadinessItem(
                    component="DeepFilterNet3 Neural Denoiser",
                    category=self.category_name,
                    status=ReadinessStatus.AVAILABLE,
                    detail="DeepFilterNet framework loaded successfully",
                    is_critical=False,
                )
            )
        except ImportError:
            items.append(
                ReadinessItem(
                    component="DeepFilterNet3 Neural Denoiser",
                    category=self.category_name,
                    status=ReadinessStatus.OPTIONAL_MISSING,
                    detail="DeepFilterNet package not installed",
                    is_critical=False,
                    remediation="Run --setup-runtime or: pip install deepfilternet",
                )
            )
        except Exception as e:
            items.append(
                ReadinessItem(
                    component="DeepFilterNet3 Neural Denoiser",
                    category=self.category_name,
                    status=ReadinessStatus.WARNING,
                    detail=f"DeepFilterNet initialization warning: {e}",
                    is_critical=False,
                    remediation="Check Rust/C++ runtime or reinstall deepfilternet.",
                )
            )

        # 6. Faster-Whisper (Semantic VAD)
        try:
            import faster_whisper

            items.append(
                ReadinessItem(
                    component="Whisper Semantic VAD",
                    category=self.category_name,
                    status=ReadinessStatus.AVAILABLE,
                    detail="faster-whisper (CTranslate2) loaded successfully",
                    is_critical=False,
                )
            )
        except ImportError:
            items.append(
                ReadinessItem(
                    component="Whisper Semantic VAD",
                    category=self.category_name,
                    status=ReadinessStatus.OPTIONAL_MISSING,
                    detail="faster-whisper package not installed",
                    is_critical=False,
                    remediation="Run --setup-runtime or: pip install faster-whisper",
                )
            )

        # 7. Matplotlib & Seaborn (Scientific Timeline Visualization)
        try:
            import matplotlib
            import seaborn

            items.append(
                ReadinessItem(
                    component="Scientific Visualizer",
                    category=self.category_name,
                    status=ReadinessStatus.READY,
                    detail=f"Matplotlib {matplotlib.__version__} & Seaborn {seaborn.__version__}",
                    is_critical=False,
                )
            )
        except ImportError:
            items.append(
                ReadinessItem(
                    component="Scientific Visualizer",
                    category=self.category_name,
                    status=ReadinessStatus.OPTIONAL_MISSING,
                    detail="Visualization libraries not installed in Lean Core",
                    is_critical=False,
                    remediation="Install optional AI/extras for PNG timeline charts.",
                )
            )

        return items
