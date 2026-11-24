"""Hardware, OS, and GPU acceleration diagnostics."""

from __future__ import annotations

import platform
import sys

import torch

from autosilenttrimmer.domain.contracts.diagnostic import ISystemDiagnostic
from autosilenttrimmer.domain.models.readiness import ReadinessItem, ReadinessStatus


class HardwareDiagnostic(ISystemDiagnostic):
    """Probes host platform, CPU, RAM, and GPU/CUDA hardware acceleration."""

    @property
    def category_name(self) -> str:
        return "Hardware & Runtime Environment"

    def check(self) -> list[ReadinessItem]:
        items: list[ReadinessItem] = []

        # 1. Python version check
        py_major, py_minor, py_micro = sys.version_info[:3]
        py_version_str = f"{py_major}.{py_minor}.{py_micro}"
        if sys.version_info >= (3, 9):
            items.append(
                ReadinessItem(
                    component="Python Runtime",
                    category=self.category_name,
                    status=ReadinessStatus.READY,
                    detail=f"Python {py_version_str} ({platform.platform()})",
                    is_critical=True,
                )
            )
        else:
            items.append(
                ReadinessItem(
                    component="Python Runtime",
                    category=self.category_name,
                    status=ReadinessStatus.FAILED,
                    detail=f"Python {py_version_str} (Python 3.9+ is required)",
                    is_critical=True,
                    remediation="Upgrade Python to version 3.9, 3.10, 3.11, or 3.12.",
                )
            )

        # 2. PyTorch Core
        items.append(
            ReadinessItem(
                component="PyTorch Engine",
                category=self.category_name,
                status=ReadinessStatus.READY,
                detail=f"PyTorch {torch.__version__}",
                is_critical=True,
            )
        )

        # 3. GPU / CUDA acceleration
        if torch.cuda.is_available():
            device_count = torch.cuda.device_count()
            device_name = torch.cuda.get_device_name(0)
            capability = torch.cuda.get_device_capability(0)
            total_vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            cuda_version = torch.version.cuda or "Unknown"

            items.append(
                ReadinessItem(
                    component="CUDA Hardware Acceleration",
                    category=self.category_name,
                    status=ReadinessStatus.READY,
                    detail=(
                        f"{device_name} ({total_vram_gb:.1f} GB VRAM, "
                        f"Compute {capability[0]}.{capability[1]}, "
                        f"CUDA {cuda_version}, {device_count} device(s))"
                    ),
                    is_critical=False,
                )
            )
        else:
            items.append(
                ReadinessItem(
                    component="CUDA Hardware Acceleration",
                    category=self.category_name,
                    status=ReadinessStatus.WARNING,
                    detail="CUDA unavailable. AI inference will execute on CPU.",
                    is_critical=False,
                    remediation=(
                        "To enable GPU acceleration, install a CUDA-enabled PyTorch build: "
                        "pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121"
                    ),
                )
            )

        return items
