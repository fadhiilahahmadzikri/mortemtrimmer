"""Spike S2 speedup benchmark harness measuring 1-worker vs multi-worker chunk throughput."""

from __future__ import annotations

import argparse
import os
import tempfile
import time

from autosilenttrimmer.application.use_cases.process_media import ProcessMediaUseCase
from autosilenttrimmer.core.config import ExecutionConfig, MediaProcessingConfig, VADConfig
from autosilenttrimmer.domain.models.processing_command import ProcessMediaCommand
from autosilenttrimmer.infrastructure.media.ffmpeg_locator import ManagedFFmpegLocator
from autosilenttrimmer.infrastructure.media.ffmpeg_manager import FFmpegMediaManager
from autosilenttrimmer.infrastructure.vad.energy import EnergyBasedVAD
from tests.conftest import synthesize_golden_mp4


def run_benchmark(duration_sec: float, worker_counts: list[int]) -> None:
    """Synthesize golden test video and measure chunk speedup across worker counts."""
    ffmpeg_path = ManagedFFmpegLocator().locate()
    with tempfile.TemporaryDirectory(prefix="trim_bench_") as tmp_dir:
        src_mp4 = os.path.join(tmp_dir, "bench_input.mp4")
        synthesize_golden_mp4(src_mp4, duration_sec=duration_sec)
        baseline_sec: float | None = None

        print(f"Benchmark input: {duration_sec:.1f}s synthetic MP4")
        for workers in worker_counts:
            out_mp4 = os.path.join(tmp_dir, f"bench_out_w{workers}.mp4")
            cfg = MediaProcessingConfig(
                ffmpeg_path=ffmpeg_path,
                vad=VADConfig(engine="energy", energy_min_len_sec=0.2),
                execution=ExecutionConfig(max_workers=workers),
            )
            use_case = ProcessMediaUseCase(
                media_manager=FFmpegMediaManager(ffmpeg_path),
                vad_strategy=EnergyBasedVAD(cfg.vad),
                config=cfg,
            )
            cmd = ProcessMediaCommand(
                input_path=src_mp4,
                output_path=out_mp4,
                vad_method="energy",
                max_workers=workers,
            )
            t0 = time.monotonic()
            use_case.execute(src_mp4, out_mp4, command=cmd)
            elapsed = time.monotonic() - t0
            if baseline_sec is None:
                baseline_sec = elapsed
            speedup = baseline_sec / elapsed if elapsed > 0 else 1.0
            print(f"  workers={workers}: elapsed={elapsed:.2f}s (speedup={speedup:.2f}x)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chunk speedup benchmark harness (Spike S2)")
    parser.add_argument("--duration", type=float, default=60.0)
    parser.add_argument("--workers", type=str, default="1,2,4")
    parsed = parser.parse_args()
    counts = [int(w.strip()) for w in parsed.workers.split(",") if w.strip()]
    run_benchmark(parsed.duration, counts)
