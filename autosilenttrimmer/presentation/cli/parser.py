"""CLI argument parser configuration."""

from __future__ import annotations

import argparse

from autosilenttrimmer.core.constants import (
    DEFAULT_COMPUTE_POLICY,
    DEFAULT_FFMPEG_EXECUTABLE,
    DEFAULT_MIN_SILENCE_GAP_SEC,
    DEFAULT_NOISE_REDUCTION_METHOD,
    DEFAULT_PAD_SEC,
    DEFAULT_RELEASE_CHANNEL,
    DEFAULT_RELEASE_MANIFEST_URL,
    DEFAULT_TRIM_STRATEGY,
    DEFAULT_VAD_METHOD,
)


def build_argument_parser() -> argparse.ArgumentParser:
    """Construct CLI argument parser covering headless CLI, daemon, shell, and runtime pack commands."""
    parser = argparse.ArgumentParser(
        description="AutoSilentTrimmer: AI-Powered Silence Remover & Noise Reduction Production Suite"
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
        help="Path for the output artifact (default: non-destructive {name}.trimmed.{ext})",
    )
    parser.add_argument(
        "--enqueue",
        nargs="+",
        metavar="PATH",
        help="Submit one or more media paths to single-instance background IPC daemon",
    )
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Start background IPC gateway and multi-job orchestrator daemon",
    )
    parser.add_argument(
        "--tray",
        action="store_true",
        help="Attach minimal tray icon & progress overlay when running --daemon",
    )
    parser.add_argument(
        "--register-shell",
        action="store_true",
        help="Register per-user OS file manager right-click entry ('Trim This Video')",
    )
    parser.add_argument(
        "--unregister-shell",
        action="store_true",
        help="Remove per-user OS file manager right-click entries cleanly",
    )
    parser.add_argument(
        "--setup-runtime",
        action="store_true",
        help="Probe host platform/GPU and install verified Runtime Packs from manifest",
    )
    parser.add_argument(
        "--install-pack",
        type=str,
        default=None,
        help="Install offline runtime pack archive (.zip) verified against --sha256",
    )
    parser.add_argument(
        "--sha256",
        type=str,
        default="",
        help="Expected SHA-256 hex digest for --install-pack archive",
    )
    parser.add_argument(
        "--manifest-url",
        type=str,
        default=DEFAULT_RELEASE_MANIFEST_URL,
        help="Signed release manifest URL or local JSON path",
    )
    parser.add_argument(
        "--channel",
        choices=["stable", "beta"],
        default=DEFAULT_RELEASE_CHANNEL,
        help=f"Release manifest channel (default: {DEFAULT_RELEASE_CHANNEL})",
    )
    parser.add_argument(
        "--export-diagnostics",
        nargs="?",
        const="",
        default=None,
        metavar="ZIP_PATH",
        help="Export anonymized diagnostics ZIP bundle",
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
        "--strategy",
        choices=["auto-silence", "manual-range"],
        default=DEFAULT_TRIM_STRATEGY,
        help=f"Trim strategy plugin (default: {DEFAULT_TRIM_STRATEGY})",
    )
    parser.add_argument(
        "--gpu-policy",
        choices=["g1_hard_gate", "g2_gpu_preferred", "g3_cpu_only"],
        default=DEFAULT_COMPUTE_POLICY,
        help=f"Compute backend selection policy (default: {DEFAULT_COMPUTE_POLICY})",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=None,
        help="Override maximum parallel chunk workers",
    )
    parser.add_argument(
        "--min-silence",
        type=float,
        default=DEFAULT_MIN_SILENCE_GAP_SEC,
        help=f"Minimum silence gap in seconds (default: {DEFAULT_MIN_SILENCE_GAP_SEC})",
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
        help="Path to FFmpeg binary executable (default: managed binary or PATH)",
    )
    parser.add_argument(
        "--lang",
        choices=["en", "id"],
        default=None,
        help="Override UI/error language ('en' or 'id')",
    )
    parser.add_argument(
        "--visual-plot",
        action="store_true",
        help="Generate speech timeline PNG visualization alongside output",
    )
    return parser
