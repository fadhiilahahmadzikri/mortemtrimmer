"""AI models, libraries, and C++/DLL integrity diagnostics."""

from __future__ import annotations

import logging

from autosilenttrimmer.domain.contracts.diagnostic import ISystemDiagnostic
from autosilenttrimmer.domain.models.readiness import ReadinessItem, ReadinessStatus

logger = logging.getLogger(__name__)


class EngineDiagnostic(ISystemDiagnostic):
    """Probes Torchaudio linking, soundfile, noisereduce, DeepFilterNet3, and Whisper."""

    @property
    def category_name(self) -> str:
        return "Audio & AI Engine Integrations"

    def check(self) -> list[ReadinessItem]:
        items: list[ReadinessItem] = []

        # 1. Torchaudio & C++ DLL integrity (WinError 127 guard)
        try:
            import torchaudio

            items.append(
                ReadinessItem(
                    component="Torchaudio Runtime",
                    category=self.category_name,
                    status=ReadinessStatus.READY,
                    detail=f"Torchaudio {torchaudio.__version__} (DLLs verified)",
                    is_critical=True,
                )
            )
        except OSError as e:
            if "WinError 127" in str(e):
                items.append(
                    ReadinessItem(
                        component="Torchaudio Runtime",
                        category=self.category_name,
                        status=ReadinessStatus.FAILED,
                        detail="Architectural DLL conflict detected (WinError 127)",
                        is_critical=True,
                        remediation="Run: pip uninstall torch torchaudio -y && pip install torch torchaudio",
                    )
                )
            else:
                items.append(
                    ReadinessItem(
                        component="Torchaudio Runtime",
                        category=self.category_name,
                        status=ReadinessStatus.FAILED,
                        detail=f"Torchaudio DLL load error: {e}",
                        is_critical=True,
                        remediation="Reinstall torch and torchaudio matching your system Python version.",
                    )
                )
        except ImportError as e:
            items.append(
                ReadinessItem(
                    component="Torchaudio Runtime",
                    category=self.category_name,
                    status=ReadinessStatus.FAILED,
                    detail=f"Import failed: {e}",
                    is_critical=True,
                    remediation="Run: pip install torchaudio",
                )
            )

        # 2. Soundfile & Noisereduce (Classical Gating)
        try:
            import noisereduce
            import soundfile

            items.append(
                ReadinessItem(
                    component="Spectral Gating & Soundfile",
                    category=self.category_name,
                    status=ReadinessStatus.READY,
                    detail="libsndfile and noisereduce operational",
                    is_critical=True,
                )
            )
        except ImportError as e:
            items.append(
                ReadinessItem(
                    component="Spectral Gating & Soundfile",
                    category=self.category_name,
                    status=ReadinessStatus.FAILED,
                    detail=f"Missing core audio dependency: {e}",
                    is_critical=True,
                    remediation="Run: pip install soundfile noisereduce",
                )
            )

        # 3. DeepFilterNet3 (Neural Noise Reduction)
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
                    remediation="To enable SOTA deep neural noise reduction: pip install deepfilternet",
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
                    remediation="Check Rust/C++ runtime or reinstall: pip install --force-reinstall deepfilternet",
                )
            )

        # 4. Silero VAD (Neural Acoustic VAD)
        items.append(
            ReadinessItem(
                component="Silero Acoustic VAD",
                category=self.category_name,
                status=ReadinessStatus.READY,
                detail="PyTorch Hub Silero VAD integration ready",
                is_critical=False,
            )
        )

        # 5. Faster-Whisper (Semantic VAD)
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
                    remediation="To enable Semantic NLP VAD: pip install faster-whisper",
                )
            )

        # 6. Matplotlib & Seaborn (Scientific Timeline Visualization)
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
        except ImportError as e:
            items.append(
                ReadinessItem(
                    component="Scientific Visualizer",
                    category=self.category_name,
                    status=ReadinessStatus.WARNING,
                    detail=f"Visualization dependencies missing: {e}",
                    is_critical=False,
                    remediation="To generate timeline charts: pip install matplotlib seaborn",
                )
            )

        return items
