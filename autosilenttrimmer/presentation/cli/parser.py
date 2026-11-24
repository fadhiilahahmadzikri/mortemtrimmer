"""CLI argument parser configuration."""

from __future__ import annotations

import argparse


def build_argument_parser() -> argparse.ArgumentParser:
    """Construct CLI argument parser; omitted tuning flags inherit persisted settings.json."""
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
        "--tune",
        action="store_true",
        help="Open the PyQt6 Tune configuration interface",
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
        default=None,
        help="Override release manifest URL or local JSON path (default from settings.json)",
    )
    parser.add_argument(
        "--channel",
        choices=["stable", "beta"],
        default=None,
        help="Override release manifest channel ('stable' or 'beta')",
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
        default=None,
        help="Override noise reduction method (default from settings.json)",
    )
    parser.add_argument(
        "--vad",
        choices=["none", "energy", "whisper", "silero"],
        default=None,
        help="Override Voice Activity Detection engine (default from settings.json)",
    )
    parser.add_argument(
        "--strategy",
        choices=["auto-silence", "manual-range"],
        default=None,
        help="Override trim strategy plugin (default from settings.json)",
    )
    parser.add_argument(
        "--gpu-policy",
        choices=["g1_hard_gate", "g2_gpu_preferred", "g3_cpu_only"],
        default=None,
        help="Override compute backend policy (default from settings.json)",
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
        default=None,
        help="Override minimum silence gap in seconds",
    )
    parser.add_argument(
        "--pad",
        type=float,
        default=None,
        help="Override audio padding per cut boundary in seconds",
    )
    parser.add_argument(
        "-f",
        "--ffmpeg",
        default=None,
        type=str,
        help="Override FFmpeg executable path (default from settings.json or auto-managed)",
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
        default=None,
        help="Generate speech timeline PNG visualization alongside output",
    )
    return parser
