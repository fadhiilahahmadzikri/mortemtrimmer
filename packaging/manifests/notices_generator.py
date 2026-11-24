"""Generate third-party license notices and JSON SBOM for installer distribution."""

from __future__ import annotations

import os
import subprocess
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT_DIR = os.path.join(PROJECT_ROOT, "packaging", "dist_notices")

BUNDLED_ATTRIBUTION_SECTION = """
================================================================================
BUNDLED ASSETS, PRETRAINED MODELS, AND EXTERNAL TOOLS
================================================================================
The components below are third-party open-source dependencies, pretrained
weights, iconography, or binaries bundled separately from Mortem Primer's own
source copyright. Their respective licenses and notices apply intact:

- GitHub Octicons (`mark-github` SVG icon)
  License   : MIT License
  Copyright : Copyright (c) GitHub Inc.
  Source    : https://github.com/primer/octicons

- Silero VAD (`snakers4/silero-vad`, v6.2)
  License   : MIT License
  Copyright : Copyright (c) Silero Team
  Source    : https://github.com/snakers4/silero-vad

- Faster-Whisper / OpenAI Whisper (`tiny`, `base`)
  License   : MIT License
  Source    : https://github.com/SYSTRAN/faster-whisper

- DeepFilterNet3 (`DeepFilterNet`)
  License   : MIT License / Apache License 2.0
  Copyright : Copyright (c) Hendrik Schroeter and contributors
  Source    : https://github.com/Rikorose/DeepFilterNet

- FFmpeg (`imageio-ffmpeg`)
  License   : LGPL / GPL according to distributed FFmpeg build configuration
  Source    : https://ffmpeg.org/
"""


def generate_notices(out_dir: str = OUT_DIR) -> tuple[str, str]:
    """Emit human-readable THIRD_PARTY_NOTICES.txt and machine-readable sbom.json."""
    os.makedirs(out_dir, exist_ok=True)
    notices_path = os.path.join(out_dir, "THIRD_PARTY_NOTICES.txt")
    sbom_path = os.path.join(out_dir, "sbom.json")

    subprocess.run(
        [
            sys.executable,
            "-m",
            "piplicenses",
            "--format=plain-vertical",
            "--with-license-file",
            "--no-license-path",
            "--output-file",
            notices_path,
        ],
        check=True,
    )
    with open(notices_path, "a", encoding="utf-8") as f:
        f.write(BUNDLED_ATTRIBUTION_SECTION)

    subprocess.run(
        [
            sys.executable,
            "-m",
            "piplicenses",
            "--format=json",
            "--output-file",
            sbom_path,
        ],
        check=True,
    )
    return notices_path, sbom_path


if __name__ == "__main__":
    txt, js = generate_notices()
    print(f"Generated notices: {txt}")
    print(f"Generated SBOM   : {js}")
