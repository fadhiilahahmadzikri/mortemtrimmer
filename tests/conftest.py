"""Pytest shared fixtures generating deterministic synthetic WAV & MP4 golden media."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import imageio_ffmpeg
import pytest


def _ffmpeg() -> str:
    return imageio_ffmpeg.get_ffmpeg_exe()


def synthesize_speech_silence_wav(dest_path: str) -> str:
    """Create a 4.0s stereo WAV: 1s silence + 1s 440Hz tone + 1s silence + 1s 523Hz tone."""
    import numpy as np
    import soundfile as sf

    sr = 16000
    t1 = np.linspace(0, 1.0, sr, endpoint=False)
    silence = np.zeros(sr, dtype=np.float32)
    tone1 = (0.4 * np.sin(2 * np.pi * 440 * t1)).astype(np.float32)
    tone2 = (0.4 * np.sin(2 * np.pi * 523 * t1)).astype(np.float32)
    wave = np.concatenate([silence, tone1, silence, tone2])
    sf.write(dest_path, wave, sr)
    return dest_path


def synthesize_golden_mp4(dest_path: str, duration_sec: float = 4.0) -> str:
    """Create a synthetic MP4 (video + speech/silence audio) with known keyframe GOPs."""
    wav_tmp = f"{dest_path}.src.wav"
    if abs(duration_sec - 4.0) < 0.1:
        synthesize_speech_silence_wav(wav_tmp)
    else:
        import numpy as np
        import soundfile as sf

        sr = 16000
        total_samples = int(sr * duration_sec)
        t = np.linspace(0, duration_sec, total_samples, endpoint=False)
        wave = (0.3 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        # Carve silence gaps cleanly
        half = total_samples // 2
        wave[half : half + int(sr * 1.0)] = 0.0
        sf.write(wav_tmp, wave, sr)

    cmd = [
        _ffmpeg(),
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"testsrc=size=320x240:rate=30:duration={duration_sec:.2f}",
        "-i",
        wav_tmp,
        "-c:v",
        "libx264",
        "-g",
        "15",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-shortest",
        dest_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    if os.path.exists(wav_tmp):
        os.remove(wav_tmp)
    return dest_path


@pytest.fixture
def golden_wav(tmp_path: Path) -> str:
    """Provide a deterministic 4.0s WAV containing active speech islands & silence."""
    return synthesize_speech_silence_wav(str(tmp_path / "sample_speech.wav"))


@pytest.fixture
def golden_mp4(tmp_path: Path) -> str:
    """Provide a deterministic 4.0s CFR H.264/AAC MP4 fixture."""
    return synthesize_golden_mp4(str(tmp_path / "sample_video.mp4"), duration_sec=4.0)
