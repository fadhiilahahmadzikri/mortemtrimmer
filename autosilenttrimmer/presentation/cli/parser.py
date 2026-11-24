"""CLI argument parser configuration."""

import argparse

from autosilenttrimmer.core.constants import (
    DEFAULT_FFMPEG_EXECUTABLE,
    DEFAULT_MIN_SILENCE_GAP_SEC,
    DEFAULT_NOISE_REDUCTION_METHOD,
    DEFAULT_PAD_SEC,
    DEFAULT_VAD_METHOD,
)


def build_argument_parser() -> argparse.ArgumentParser:
    """Construct CLI argument parser with canonical defaults and documentation."""
    parser = argparse.ArgumentParser(
        description="AutoSilentTrimmer: AI-Powered Silence Remover & Noise Reduction Pipeline"
    )
    parser.add_argument(
        "--check",
        "--readiness",
        dest="check",
        action="store_true",
        help="Perform comprehensive system readiness diagnostic and exit",
    )
    parser.add_argument(
        "-i",
        "--input",
        required=False,
        type=str,
        help="Path to the input media file (audio or video)",
    )
    parser.add_argument(
        "-o",
        "--output",
        required=False,
        type=str,
        help="Path for the output artifact",
    )
    parser.add_argument(
        "-m",
        "--method",
        choices=["none", "spectral", "deepfilter"],
        default=DEFAULT_NOISE_REDUCTION_METHOD,
        help=f"Noise reduction method (default: {DEFAULT_NOISE_REDUCTION_METHOD})",
    )
    parser.add_argument(
        "--vad",
        choices=["none", "energy", "whisper", "silero"],
        default=DEFAULT_VAD_METHOD,
        help=f"Voice Activity Detection engine (default: {DEFAULT_VAD_METHOD})",
    )
    parser.add_argument(
        "--min-silence",
        type=float,
        default=DEFAULT_MIN_SILENCE_GAP_SEC,
        help=f"Minimum silence gap in seconds to trigger a cut (default: {DEFAULT_MIN_SILENCE_GAP_SEC})",
    )
    parser.add_argument(
        "--pad",
        type=float,
        default=DEFAULT_PAD_SEC,
        help=f"Audio padding per cut boundary in seconds (default: {DEFAULT_PAD_SEC})",
    )
    parser.add_argument(
        "-f",
        "--ffmpeg",
        default=DEFAULT_FFMPEG_EXECUTABLE,
        type=str,
        help="Path to FFmpeg binary executable (default: auto-detected via managed binary or system PATH)",
    )
    return parser
