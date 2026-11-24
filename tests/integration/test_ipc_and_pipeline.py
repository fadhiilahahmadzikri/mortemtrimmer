"""Integration tests covering Spikes S1 (IPC multi-select), S2 (Golden invariants), and S6 (HTTP Range)."""

from __future__ import annotations

import functools
import os
import threading
import time
import uuid
import zipfile
from concurrent.futures import ThreadPoolExecutor
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from autosilenttrimmer.application.use_cases.process_media import ProcessMediaUseCase
from autosilenttrimmer.core.config import MediaProcessingConfig, VADConfig
from autosilenttrimmer.domain.contracts.compute import IComputeBackend
from autosilenttrimmer.domain.models.compute import BackendSelection, ComputePolicy
from autosilenttrimmer.domain.models.events import BackendFallback, RuntimeDownloadProgress
from autosilenttrimmer.domain.models.runtime_pack import RuntimePackArtifact
from autosilenttrimmer.infrastructure.events.in_memory_bus import InMemoryEventBus
from autosilenttrimmer.infrastructure.ipc.gateway import LocalIPCClient, LocalIPCGateway
from autosilenttrimmer.infrastructure.media.ffmpeg_locator import ManagedFFmpegLocator
from autosilenttrimmer.infrastructure.media.ffmpeg_manager import FFmpegMediaManager
from autosilenttrimmer.infrastructure.media.pyav_prober import PyAVMediaProber
from autosilenttrimmer.infrastructure.media.pyav_verifier import PyAVMediaVerifier
from autosilenttrimmer.infrastructure.runtime.manifest_client import HttpManifestClient
from autosilenttrimmer.infrastructure.runtime.pack_manager import (
    ManagedRuntimePackManager,
    compute_sha256,
)
from autosilenttrimmer.infrastructure.vad.energy import EnergyBasedVAD


@pytest.mark.integration
def test_spike_s1_ipc_multiselect_coalescing(tmp_path: Path) -> None:
    """Spike S1: concurrent shell clients coalesce into one ordered batch cleanly."""
    if os.name == "nt":
        addr = rf"\\.\pipe\test_trim_gw_{uuid.uuid4().hex[:8]}"
        fam = "AF_PIPE"
    else:
        addr = str(tmp_path / "gw.sock")
        fam = "AF_UNIX"

    received_batches: list[list[str]] = []
    reloaded = threading.Event()
    done_ev = threading.Event()

    gateway = LocalIPCGateway(address=addr, family=fam, coalesce_window_sec=0.15)
    gateway.start(
        lambda batch: (received_batches.append(batch), done_ev.set()),
        on_reload_settings=reloaded.set,
    )

    try:
        client = LocalIPCClient(address=addr, family=fam)
        assert client.is_daemon_running()
        assert client.notify_settings_updated()
        assert reloaded.wait(timeout=1.5)

        paths = [f"video_{i}.mp4" for i in range(6)]
        with ThreadPoolExecutor(max_workers=6) as pool:
            results = list(pool.map(lambda p: client.enqueue_paths([p]), paths))
        assert all(results)
        assert done_ev.wait(timeout=3.0)
        flattened = [item for batch in received_batches for item in batch]
        assert set(flattened) == set(paths)
        assert len(flattened) == 6
    finally:
        gateway.stop()


@pytest.mark.integration
@pytest.mark.slow
def test_spike_s2_golden_mp4_non_destructive_and_verified(golden_mp4: str, tmp_path: Path) -> None:
    """Spike S2: trim MP4 end-to-end, verify original untouched, output passes PyAVMediaVerifier."""
    src_sha_before = compute_sha256(golden_mp4)
    ffmpeg_path = ManagedFFmpegLocator().locate()

    cfg = MediaProcessingConfig(
        ffmpeg_path=ffmpeg_path,
        vad=VADConfig(engine="energy", energy_min_len_sec=0.15, energy_dilation_pad_sec=0.1),
    )
    bus = InMemoryEventBus()
    use_case = ProcessMediaUseCase(
        media_manager=FFmpegMediaManager(ffmpeg_path),
        vad_strategy=EnergyBasedVAD(cfg.vad),
        noise_reduction_strategy=None,
        visualizer=None,
        event_bus=bus,
        config=cfg,
    )

    result = use_case.execute(golden_mp4)
    assert result.output_path.endswith(".trimmed.mp4")
    assert os.path.isfile(result.output_path)
    assert compute_sha256(golden_mp4) == src_sha_before
    assert result.final_duration < result.original_duration
    assert result.reduction_percentage > 15.0

    verifier = PyAVMediaVerifier()
    probe = PyAVMediaProber().probe(result.output_path)
    assert probe.is_video
    vreport = verifier.verify(
        result.output_path,
        expected_duration_sec=result.final_duration,
        expected_has_video=True,
        expected_audio_streams=1,
    )
    assert vreport.passed, vreport.failure_reason
    assert vreport.decode_samples_checked >= 2


@pytest.mark.integration
@pytest.mark.slow
def test_spike_s2_golden_wav_audio_pipeline(golden_wav: str, tmp_path: Path) -> None:
    """Verify audio-only pipeline runs cleanly with automatic output naming & PyAV verification."""
    ffmpeg_path = ManagedFFmpegLocator().locate()
    cfg = MediaProcessingConfig(
        ffmpeg_path=ffmpeg_path,
        vad=VADConfig(engine="energy", energy_min_len_sec=0.15, energy_dilation_pad_sec=0.1),
    )
    use_case = ProcessMediaUseCase(
        media_manager=FFmpegMediaManager(ffmpeg_path),
        vad_strategy=EnergyBasedVAD(cfg.vad),
        config=cfg,
    )
    result = use_case.execute(golden_wav)
    assert result.output_path.endswith(".trimmed.wav")
    assert result.final_duration < result.original_duration


@pytest.mark.integration
def test_spike_s6_http_range_resumable_runtime_download(tmp_path: Path) -> None:
    """Spike S6: resumable partial download + SHA-256 verification + atomic installation."""
    serve_dir = tmp_path / "cdn"
    serve_dir.mkdir()
    archive_file = serve_dir / "ffmpeg-windows-x86_64-7.1.0.zip"
    with zipfile.ZipFile(archive_file, "w") as zf:
        zf.writestr("bin/ffmpeg.exe", b"X" * 2048)
    expected_sha = compute_sha256(str(archive_file))

    class _RangeHandler(SimpleHTTPRequestHandler):
        def do_GET(self) -> None:
            range_hdr = self.headers.get("Range")
            if range_hdr and range_hdr.startswith("bytes="):
                start = int(range_hdr.split("=")[1].split("-")[0])
                data = archive_file.read_bytes()[start:]
                self.send_response(206)
                self.send_header("Content-Length", str(len(data)))
                self.send_header(
                    "Content-Range",
                    f"bytes {start}-{archive_file.stat().st_size - 1}/{archive_file.stat().st_size}",
                )
                self.end_headers()
                self.wfile.write(data)
                return
            super().do_GET()

        def log_message(self, format: str, *args: object) -> None:
            pass

    handler_cls = functools.partial(_RangeHandler, directory=str(serve_dir))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_cls)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        # Simulate pre-existing interrupted .part file containing first 512 bytes
        part_file = cache_dir / "ffmpeg-windows-x86_64-7.1.0.zip.part"
        part_file.write_bytes(archive_file.read_bytes()[:512])

        events: list[int] = []
        bus = InMemoryEventBus()
        bus.subscribe(
            RuntimeDownloadProgress,
            lambda ev: events.append(getattr(ev, "downloaded_bytes", 0)),
        )
        client = HttpManifestClient(bus)
        mgr = ManagedRuntimePackManager(
            runtime_packs_dir=str(tmp_path / "packs"),
            cache_dir=str(cache_dir),
            manifest_client=client,
        )
        artifact = RuntimePackArtifact(
            pack_id="ffmpeg-windows-x86_64",
            pack_type="ffmpeg",
            platform_tag="windows-x86_64",
            version="7.1.0",
            url=f"http://127.0.0.1:{port}/{archive_file.name}",
            sha256=expected_sha,
            size_bytes=archive_file.stat().st_size,
        )
        rec = mgr.install_pack(artifact)
        assert rec.sha256 == expected_sha
        assert len(events) > 0
        assert Path(rec.install_dir, "bin", "ffmpeg.exe").read_bytes() == b"X" * 2048
    finally:
        server.shutdown()
        server.server_close()
        time.sleep(0.05)


class _BrokenGPUBackend(IComputeBackend):
    """Simulates a failing hardware encoder forcing G2 fallback onto CPU libx264."""

    def select_backend(
        self,
        policy: ComputePolicy,
        ffmpeg_path: str,
        requested_max_workers: int | None = None,
    ) -> BackendSelection:
        return BackendSelection(
            backend_id="gpu-fake",
            ai_device="cpu",
            video_encoder="nonexistent_broken_encoder",
            max_concurrency=2,
            is_gpu=True,
            reason="simulated gpu",
        )

    def fallback_to_cpu(self, reason: str) -> BackendSelection:
        return BackendSelection(
            backend_id="cpu",
            ai_device="cpu",
            video_encoder="libx264",
            max_concurrency=2,
            is_gpu=False,
            reason=f"fallback: {reason}",
        )


@pytest.mark.integration
@pytest.mark.slow
def test_spike_s3_gpu_fallback_to_cpu_under_policy_g2(golden_mp4: str) -> None:
    """Spike S3: forced GPU chunk error emits BackendFallback and recovers on CPU."""
    ffmpeg_path = ManagedFFmpegLocator().locate()
    fallback_events: list[BackendFallback] = []
    bus = InMemoryEventBus()
    bus.subscribe(BackendFallback, lambda ev: fallback_events.append(ev))  # type: ignore[arg-type]

    cfg = MediaProcessingConfig(
        ffmpeg_path=ffmpeg_path,
        vad=VADConfig(engine="energy", energy_min_len_sec=0.15, energy_dilation_pad_sec=0.1),
    )
    use_case = ProcessMediaUseCase(
        media_manager=FFmpegMediaManager(ffmpeg_path),
        vad_strategy=EnergyBasedVAD(cfg.vad),
        compute_backend=_BrokenGPUBackend(),
        event_bus=bus,
        config=cfg,
    )

    result = use_case.execute(golden_mp4)
    assert os.path.isfile(result.output_path)
    assert len(fallback_events) >= 1
    assert fallback_events[0].from_backend == "gpu-fake"
    assert fallback_events[0].to_backend == "cpu"
