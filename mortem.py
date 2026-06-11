import argparse
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import traceback
import warnings
from abc import ABC, abstractmethod

import numpy as np
import soundfile as sf
import torch
from tqdm import tqdm

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


class INoiseReductionStrategy(ABC):
    @abstractmethod
    def process(self, input_path: str, output_path: str) -> None:
        pass


class IMediaManager(ABC):
    @abstractmethod
    def extract_audio(self, video_path: str, temp_audio_path: str) -> None:
        pass

    @abstractmethod
    def merge_audio(
        self, video_path: str, clean_audio_path: str, output_path: str
    ) -> None:
        pass

    @abstractmethod
    def export_audio(self, clean_audio_path: str, output_path: str) -> None:
        pass

    @abstractmethod
    def slice_and_concat(
        self, media_path: str, segments: list[tuple[float, float]], output_path: str
    ) -> None:
        pass


class IVoiceActivityDetector(ABC):
    @abstractmethod
    def get_keep_segments(
        self, audio_path: str, manifest_path: str
    ) -> list[tuple[float, float]]:
        pass


class SpectralGatingStrategy(INoiseReductionStrategy):
    def process(self, input_path: str, output_path: str) -> None:
        import noisereduce as nr

        logger.info("Initializing Spectral Gating process...")
        audio_data, sample_rate = sf.read(input_path, dtype="float32")

        if len(audio_data.shape) > 1:
            audio_data = audio_data.T
            reduced_audio = nr.reduce_noise(
                y=audio_data, sr=sample_rate, prop_decrease=0.8
            )
            reduced_audio = reduced_audio.T
        else:
            reduced_audio = nr.reduce_noise(
                y=audio_data, sr=sample_rate, prop_decrease=0.8
            )

        sf.write(output_path, reduced_audio, sample_rate)


class DeepFilterNetStrategy(INoiseReductionStrategy):
    @torch.inference_mode()
    def process(self, input_path: str, output_path: str) -> None:
        logger.info(
            "Loading Deep Learning libraries and validating C++/CUDA dependencies..."
        )
        try:
            from df.enhance import enhance, init_df, load_audio, save_audio
        except OSError as e:
            if "WinError 127" in str(e):
                raise RuntimeError(
                    "Architectural conflict detected in PyTorch & Torchaudio DLLs (WinError 127). "
                    "Resolution: Execute 'pip uninstall torch torchaudio -y' followed by 'pip install torch torchaudio'."
                ) from e
            raise

        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(
            f"Initializing DeepFilterNet3 (Hardware Acceleration: {device.upper()})..."
        )

        model, df_state, _ = init_df(config_allow_defaults=True)
        model = model.to(device).eval()

        audio, _ = load_audio(input_path, sr=df_state.sr())
        chunk_size = int(df_state.sr() * 10)
        audio_chunks = torch.split(audio, chunk_size, dim=1)
        enhanced_chunks = []

        logger.info(
            "====================================================================="
        )
        logger.info(">> O(1) GPU MEMORY ALLOCATION ENABLED <<")
        logger.info(f">> Total audio segments to process: {len(audio_chunks)} chunks.")
        logger.info(
            "====================================================================="
        )

        with tqdm(total=len(audio_chunks), desc="Neural Network Processing") as pbar:
            for chunk in audio_chunks:
                enhanced_chunk = enhance(model, df_state, chunk)
                enhanced_chunks.append(enhanced_chunk)
                if device == "cuda":
                    torch.cuda.empty_cache()
                pbar.update(1)

        enhanced = torch.cat(enhanced_chunks, dim=1)
        logger.info("Neural Network inference completed. Saving artifact...")
        save_audio(output_path, enhanced, df_state.sr())


class SileroBasedVAD(IVoiceActivityDetector):
    def __init__(self, min_silence_gap: float, pad: float):
        self._min_silence_gap = min_silence_gap
        self._pad = pad

    def get_keep_segments(
        self, audio_path: str, manifest_path: str
    ) -> list[tuple[float, float]]:
        logger.info("Loading Silero VAD (Acoustic Neural Engine)...")
        model, utils = torch.hub.load(
            repo_or_dir="snakers4/silero-vad",
            model="silero_vad",
            force_reload=False,
            trust_repo=True,
        )
        get_speech_timestamps, _, read_audio, _, _ = utils

        logger.info("Reading raw acoustic wave data...")
        wav = read_audio(audio_path, sampling_rate=16000)

        logger.info("Scanning human vocal cord vibrations (Acoustic Analysis)...")
        min_silence_ms = int(self._min_silence_gap * 1000)

        speech_timestamps = get_speech_timestamps(
            wav,
            model,
            sampling_rate=16000,
            min_silence_duration_ms=min_silence_ms,
            min_speech_duration_ms=100,
        )

        keep_segments = []
        manifest_lines = []

        for seg in tqdm(
            speech_timestamps, desc="Acoustic Segmentation", unit=" segment"
        ):
            start_sec = seg["start"] / 16000.0
            end_sec = seg["end"] / 16000.0

            start_padded = max(0.0, start_sec - self._pad)
            end_padded = end_sec + self._pad

            manifest_lines.append(
                f"[{start_sec:.3f} -> {end_sec:.3f}] Speech Detected (Vocal Acoustic)"
            )
            keep_segments.append((start_padded, end_padded))

        if manifest_path:
            with open(manifest_path, "w", encoding="utf-8") as f:
                f.write("\n".join(manifest_lines))

        logger.info("Resolving overlapping timestamps...")
        return self._merge_overlapping(keep_segments)

    def _merge_overlapping(
        self, segments: list[tuple[float, float]]
    ) -> list[tuple[float, float]]:
        if not segments:
            return []
        segments.sort(key=lambda x: x[0])
        merged = [segments[0]]
        for current in segments[1:]:
            prev = merged[-1]
            if current[0] <= prev[1]:
                merged[-1] = (prev[0], max(prev[1], current[1]))
            else:
                merged.append(current)
        return merged


class WhisperBasedVAD(IVoiceActivityDetector):
    def __init__(self, min_silence_gap: float, pad: float):
        self._min_silence_gap = min_silence_gap
        self._pad = pad

    def get_keep_segments(
        self, audio_path: str, manifest_path: str
    ) -> list[tuple[float, float]]:
        try:
            from faster_whisper import WhisperModel
        except ImportError as e:
            raise RuntimeError("Missing dependency for Semantic VAD.") from e

        device = "cuda" if torch.cuda.is_available() else "cpu"
        compute_type = "float16" if device == "cuda" else "int8"

        logger.info(
            f"Loading Whisper Semantic Engine on {device.upper()} (Compute: {compute_type})..."
        )
        model = WhisperModel("base", device=device, compute_type=compute_type)

        logger.info(
            "Transcribing audio to extract precision semantic timestamps (Language: ID)..."
        )
        segments_gen, _ = model.transcribe(
            audio_path,
            language="id",
            word_timestamps=True,
            vad_filter=False,
            condition_on_previous_text=False,
        )

        keep_segments = []
        manifest_lines = []

        for segment in tqdm(
            segments_gen, desc="NLP Semantic Analysis", unit=" segment"
        ):
            if (
                segment.no_speech_prob > 0.6
                or not segment.text.strip()
                or not segment.words
            ):
                continue

            manifest_lines.append(
                f"[{segment.start:.3f} -> {segment.end:.3f}] {segment.text.strip()} (P_NoSpeech: {segment.no_speech_prob:.2f})"
            )

            for word in segment.words:
                if not word.word.strip() or (word.end - word.start > 2.5):
                    continue
                manifest_lines.append(
                    f"    [{word.start:.3f} -> {word.end:.3f}] {word.word.strip()}"
                )
                start_padded = max(0.0, word.start - self._pad)
                end_padded = word.end + self._pad
                keep_segments.append((start_padded, end_padded))

        if manifest_path:
            with open(manifest_path, "w", encoding="utf-8") as f:
                f.write("\n".join(manifest_lines))

        return self._merge_overlapping(keep_segments)

    def _merge_overlapping(
        self, segments: list[tuple[float, float]]
    ) -> list[tuple[float, float]]:
        if not segments:
            return []
        segments.sort(key=lambda x: x[0])
        merged = [segments[0]]
        for current in segments[1:]:
            prev = merged[-1]
            if current[0] - prev[1] < self._min_silence_gap:
                merged[-1] = (prev[0], max(prev[1], current[1]))
            else:
                merged.append(current)
        return merged


class EnergyBasedVAD(IVoiceActivityDetector):
    def get_keep_segments(
        self, audio_path: str, manifest_path: str
    ) -> list[tuple[float, float]]:
        min_len_sec = 0.2
        audio, sr = sf.read(audio_path, dtype="float32")
        if len(audio.shape) > 1:
            audio = audio.mean(axis=1)
        window_sec = 0.05
        window_size = int(sr * window_sec)
        if len(audio) == 0:
            return []
        pad_len = window_size - (len(audio) % window_size)
        if pad_len != window_size:
            audio = np.pad(audio, (0, pad_len))
        frames = audio.reshape(-1, window_size)
        power = np.mean(frames**2, axis=1)
        db = 10 * np.log10(power + 1e-10)
        peak_db = float(np.percentile(db, 95))
        threshold_db = peak_db - 25.0
        is_speech = db > threshold_db
        pad_frames = int(0.3 / window_sec)
        kernel = np.ones(pad_frames * 2 + 1)
        dilated = np.convolve(is_speech.astype(int), kernel, mode="same") > 0
        diff = np.diff(np.concatenate([[0], dilated.astype(int), [0]]))
        starts = np.where(diff == 1)[0]
        ends = np.where(diff == -1)[0]
        segments = []
        for s, e in zip(starts, ends):
            start_sec = s * window_sec
            end_sec = e * window_sec
            actual_duration = len(audio) / sr
            end_sec = min(end_sec, actual_duration)
            if end_sec - start_sec >= min_len_sec:
                segments.append((start_sec, end_sec))
        if manifest_path:
            with open(manifest_path, "w", encoding="utf-8") as f:
                for start, end in segments:
                    f.write(f"[{start:.3f} - {end:.3f}]\n")
        return segments


class FFmpegMediaManager(IMediaManager):
    def __init__(self, ffmpeg_path: str):
        self._ffmpeg_path = ffmpeg_path
        if not os.path.exists(self._ffmpeg_path):
            raise RuntimeError(
                f"FFmpeg executable not found at absolute path: {self._ffmpeg_path}"
            )
        self._verify_ffmpeg_active()

    def _get_clean_env(self) -> dict:
        env = os.environ.copy()
        ffmpeg_dir = os.path.dirname(self._ffmpeg_path)
        clean_path = [
            p for p in env.get("PATH", "").split(os.pathsep) if "venv" not in p.lower()
        ]
        env["PATH"] = os.pathsep.join([ffmpeg_dir] + clean_path)
        return env

    def _verify_ffmpeg_active(self) -> None:
        logger.info("Verifying FFmpeg service integrity and environment isolation...")
        try:
            subprocess.run(
                [self._ffmpeg_path, "-version"],
                check=True,
                capture_output=True,
                text=True,
                env=self._get_clean_env(),
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"FFmpeg responded with an error state:\n{e.stderr}")
        except OSError as e:
            raise RuntimeError(
                f"System failed to execute FFmpeg (Possible corruption): {e}"
            )

    def extract_audio(self, video_path: str, temp_audio_path: str) -> None:
        logger.info(
            "Extracting raw audio stream (48 kHz mono PCM — native DeepFilterNet SR)..."
        )
        command = [
            self._ffmpeg_path,
            "-y",
            "-i",
            video_path,
            "-vn",
            "-acodec",
            "pcm_s16le",
            "-ar",
            "48000",
            "-ac",
            "1",
            temp_audio_path,
        ]
        self._run_ffmpeg(command)

    def merge_audio(
        self, video_path: str, clean_audio_path: str, output_path: str
    ) -> None:
        logger.info(
            "Multiplexing clean audio with original video stream (Zero-loss video copy)..."
        )
        command = [
            self._ffmpeg_path,
            "-y",
            "-i",
            video_path,
            "-i",
            clean_audio_path,
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "256k",
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            output_path,
        ]
        self._run_ffmpeg(command)

    def export_audio(self, clean_audio_path: str, output_path: str) -> None:
        logger.info("Exporting final audio artifact...")
        out_ext = os.path.splitext(output_path)[1].lower()
        codec = "copy" if out_ext == ".wav" else "aac"
        command = [self._ffmpeg_path, "-y", "-i", clean_audio_path, "-c:a", codec]
        if codec == "aac":
            command.extend(["-b:a", "256k"])
        command.append(output_path)
        self._run_ffmpeg(command)

    def slice_and_concat(
        self, media_path: str, segments: list[tuple[float, float]], output_path: str
    ) -> None:
        if not segments:
            shutil.copy(media_path, output_path)
            return

        _, ext = os.path.splitext(media_path)
        is_video = ext.lower() in {".mp4", ".mkv", ".avi", ".mov", ".flv", ".webm"}
        total_keep = sum(e - s for s, e in segments)
        n = len(segments)

        logger.info(f"Cutting plan: {n} segments | Keep: {total_keep:.1f}s")
        logger.info(
            "Building precision filter graph (trim/atrim + concat, zero AV-drift)..."
        )

        fc_path = None
        try:
            filter_parts: list[str] = []

            if n == 1:

                start, end = segments[0]
                if is_video:
                    filter_parts.append(
                        f"[0:v]trim=start={start:.6f}:end={end:.6f},"
                        f"setpts=PTS-STARTPTS[vout];"
                    )
                    filter_parts.append(
                        f"[0:a]atrim=start={start:.6f}:end={end:.6f},"
                        f"asetpts=PTS-STARTPTS[aout]"
                    )
                    map_args = ["-map", "[vout]", "-map", "[aout]"]
                    codec_args = [
                        "-c:v",
                        "libx264",
                        "-bf",
                        "0",
                        "-crf",
                        "18",
                        "-preset",
                        "superfast",
                        "-c:a",
                        "pcm_s16le",
                    ]
                else:
                    filter_parts.append(
                        f"[0:a]atrim=start={start:.6f}:end={end:.6f},"
                        f"asetpts=PTS-STARTPTS[aout]"
                    )
                    map_args = ["-map", "[aout]"]
                    codec_args = ["-c:a", "pcm_s16le"]

            else:

                if is_video:
                    split_v = "".join(f"[v_s{i}]" for i in range(n))
                    split_a = "".join(f"[a_s{i}]" for i in range(n))
                    filter_parts.append(f"[0:v]split={n}{split_v};")
                    filter_parts.append(f"[0:a]asplit={n}{split_a};")

                    for i, (start, end) in enumerate(segments):
                        filter_parts.append(
                            f"[v_s{i}]trim=start={start:.6f}:end={end:.6f},"
                            f"setpts=PTS-STARTPTS[v{i}];"
                        )
                        filter_parts.append(
                            f"[a_s{i}]atrim=start={start:.6f}:end={end:.6f},"
                            f"asetpts=PTS-STARTPTS[a{i}];"
                        )

                    v_inputs = "".join(f"[v{i}]" for i in range(n))
                    a_inputs = "".join(f"[a{i}]" for i in range(n))

                    filter_parts.append(f"{v_inputs}concat=n={n}:v=1:a=0[vout];")
                    filter_parts.append(f"{a_inputs}concat=n={n}:v=0:a=1[aout]")

                    map_args = ["-map", "[vout]", "-map", "[aout]"]
                    codec_args = [
                        "-c:v",
                        "libx264",
                        "-bf",
                        "0",
                        "-crf",
                        "18",
                        "-preset",
                        "superfast",
                        "-c:a",
                        "pcm_s16le",
                    ]

                else:
                    split_a = "".join(f"[a_s{i}]" for i in range(n))
                    filter_parts.append(f"[0:a]asplit={n}{split_a};")

                    for i, (start, end) in enumerate(segments):
                        filter_parts.append(
                            f"[a_s{i}]atrim=start={start:.6f}:end={end:.6f},"
                            f"asetpts=PTS-STARTPTS[a{i}];"
                        )

                    a_inputs = "".join(f"[a{i}]" for i in range(n))
                    filter_parts.append(f"{a_inputs}concat=n={n}:v=0:a=1[aout]")

                    map_args = ["-map", "[aout]"]
                    codec_args = ["-c:a", "pcm_s16le"]

            filter_complex = "".join(filter_parts)

            fd_fc, fc_path = tempfile.mkstemp(suffix=".txt")
            os.close(fd_fc)
            with open(fc_path, "w", encoding="utf-8") as f:
                f.write(filter_complex)

            logger.info(
                f"Executing precision splice ({n} segments) via filter_complex_script..."
            )
            command = [
                self._ffmpeg_path,
                "-y",
                "-i",
                media_path,
                "-filter_complex_script",
                fc_path,
                *map_args,
                *codec_args,
                output_path,
            ]
            self._run_ffmpeg(command)

        finally:
            if fc_path and os.path.exists(fc_path):
                os.remove(fc_path)

    def _run_ffmpeg(self, command: list) -> None:
        try:
            subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
                env=self._get_clean_env(),
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"FFmpeg execution failed during media processing:\n{e.stderr}"
            )
        except OSError as e:
            raise RuntimeError(
                f"OS level failure when invoking FFmpeg ({self._ffmpeg_path}): {e}"
            )


class AudioProcessor:
    def __init__(
        self,
        strategy: INoiseReductionStrategy,
        media_manager: IMediaManager,
        vad_strategy: IVoiceActivityDetector,
    ):
        self._strategy = strategy
        self._media_manager = media_manager
        self._vad_strategy = vad_strategy
        self._video_extensions = {".mp4", ".mkv", ".avi", ".mov", ".flv", ".webm"}

    def _generate_scientific_plot(
        self,
        segments: list[tuple[float, float]],
        total_duration: float,
        output_path: str,
    ) -> str:
        try:
            import matplotlib

            matplotlib.use("Agg")
            import matplotlib.patches as mpatches
            import matplotlib.pyplot as plt
            import seaborn as sns
        except ImportError as e:
            raise RuntimeError(
                "Eksekusi visualisasi saintifik membutuhkan pustaka khusus. "
                "Jalankan 'pip install seaborn matplotlib' di terminal."
            ) from e

        if total_duration <= 0:
            total_duration = 1.0

        sns.set_theme(
            style="darkgrid",
            rc={
                "axes.facecolor": "#121212",
                "figure.facecolor": "#121212",
                "grid.color": "#333333",
                "text.color": "white",
                "axes.labelcolor": "white",
                "xtick.color": "white",
                "ytick.color": "white",
            },
        )

        fig, ax = plt.subplots(figsize=(16, 4))
        ax.set_xlim(0, total_duration)
        ax.set_ylim(0, 1)
        ax.set_yticks([])
        ax.axhspan(0, 1, color="#2c2c2c", alpha=1.0)

        xranges = [(start, end - start) for start, end in segments]
        if xranges:
            ax.broken_barh(xranges, (0, 1), facecolors="#00e676", alpha=0.85)

        ax.set_xlabel("Timeline (Seconds)", fontsize=12, fontweight="bold")
        ax.set_title(
            "SOTA Acoustic Segmentation & Voice Activity Detection",
            fontsize=16,
            fontweight="bold",
            pad=20,
        )

        speech_patch = mpatches.Patch(color="#00e676", label="Active Speech (Retained)")
        silence_patch = mpatches.Patch(
            color="#2c2c2c", label="Silence / Noise (Discarded)"
        )
        ax.legend(
            handles=[speech_patch, silence_patch],
            loc="upper right",
            facecolor="#1e1e1e",
            edgecolor="#333333",
            labelcolor="white",
        )

        plt.tight_layout()
        plot_path = output_path + ".plot.png"
        plt.savefig(plot_path, dpi=300, bbox_inches="tight")
        plt.close(fig)
        return plot_path

    def execute(self, input_path: str, output_path: str) -> None:
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input file does not exist: {input_path}")

        _, in_ext = os.path.splitext(input_path.lower())
        _, out_ext = os.path.splitext(output_path.lower())

        is_input_video = in_ext in self._video_extensions
        is_output_video = out_ext in self._video_extensions

        if not is_input_video and is_output_video:
            raise ValueError(
                f"Format Mismatch Error: Input is an audio file '{in_ext}', "
                f"but output is set to a video container '{out_ext}'. "
                "Please specify an audio extension (e.g., .wav, .aac, .mp3) for the output."
            )

        fd_raw, raw_audio = tempfile.mkstemp(suffix=".wav")
        os.close(fd_raw)

        try:
            if is_input_video:
                self._media_manager.extract_audio(input_path, raw_audio)
                target_audio = raw_audio
            else:
                target_audio = input_path
                shutil.copy(input_path, raw_audio)

            info = sf.info(target_audio)
            original_duration = info.duration

            segments = []
            if self._vad_strategy:
                logger.info(
                    "Initializing SOTA Voice Activity Detection on RAW Audio..."
                )
                manifest_path = output_path + ".manifest.txt"
                segments = self._vad_strategy.get_keep_segments(
                    target_audio, manifest_path
                )
                logger.info(f"VAD Detected {len(segments)} valid speech segments.")

            _cut_suffix = ".mkv" if is_input_video else ".wav"
            fd_cut_media, cut_media = tempfile.mkstemp(suffix=_cut_suffix)
            os.close(fd_cut_media)

            try:
                if self._vad_strategy:
                    self._media_manager.slice_and_concat(
                        input_path, segments, cut_media
                    )
                    final_duration = sum(e - s for s, e in segments)
                else:
                    shutil.copy(input_path, cut_media)
                    final_duration = original_duration

                if self._strategy:
                    fd_cut_raw, cut_raw_audio = tempfile.mkstemp(suffix=".wav")
                    fd_cut_clean, cut_clean_audio = tempfile.mkstemp(suffix=".wav")
                    os.close(fd_cut_raw)
                    os.close(fd_cut_clean)

                    try:
                        if is_input_video:
                            self._media_manager.extract_audio(cut_media, cut_raw_audio)
                            audio_to_enhance = cut_raw_audio
                        else:
                            audio_to_enhance = cut_media

                        self._strategy.process(audio_to_enhance, cut_clean_audio)

                        if is_input_video:
                            self._media_manager.merge_audio(
                                cut_media, cut_clean_audio, output_path
                            )
                        else:
                            self._media_manager.export_audio(
                                cut_clean_audio, output_path
                            )
                    finally:
                        if os.path.exists(cut_raw_audio):
                            os.remove(cut_raw_audio)
                        if os.path.exists(cut_clean_audio):
                            os.remove(cut_clean_audio)
                else:
                    if is_input_video:
                        shutil.copy(cut_media, output_path)
                    else:
                        self._media_manager.export_audio(cut_media, output_path)

            finally:
                if os.path.exists(cut_media):
                    os.remove(cut_media)

            if self._vad_strategy:
                plot_path = self._generate_scientific_plot(
                    segments, original_duration, output_path
                )
                reduction_pct = (
                    ((original_duration - final_duration) / original_duration) * 100
                    if original_duration > 0
                    else 0
                )
                logger.info(
                    "====================================================================="
                )
                logger.info(">> SOTA PRODUCTION ARTIFACT REPORT <<")
                logger.info(f">> Original Duration : {original_duration:.2f} seconds")
                logger.info(f">> Final Duration    : {final_duration:.2f} seconds")
                logger.info(
                    f">> Total Reduction   : {original_duration - final_duration:.2f} seconds ({reduction_pct:.2f}% Silence Removed)"
                )
                logger.info(f">> Transcript Saved  : {manifest_path}")
                logger.info(f">> Visual Plot       : {plot_path}")
                logger.info(
                    "====================================================================="
                )

            logger.info(f"SUCCESS: Final SOTA artifact saved at {output_path}")

        finally:
            if os.path.exists(raw_audio):
                os.remove(raw_audio)


class StrategyFactory:
    @staticmethod
    def create_noise_reduction(method_name: str) -> INoiseReductionStrategy:
        if method_name == "spectral":
            return SpectralGatingStrategy()
        elif method_name == "deepfilter":
            return DeepFilterNetStrategy()
        return None

    @staticmethod
    def create_vad(
        method_name: str, min_silence_gap: float, pad: float
    ) -> IVoiceActivityDetector:
        if method_name == "energy":
            return EnergyBasedVAD()
        elif method_name == "whisper":
            return WhisperBasedVAD(min_silence_gap=min_silence_gap, pad=pad)
        elif method_name == "silero":
            return SileroBasedVAD(min_silence_gap=min_silence_gap, pad=pad)
        return None


def main():
    warnings.filterwarnings("ignore")

    parser = argparse.ArgumentParser(
        description="SOTA Noise Reduction & Acoustic VAD Pipeline"
    )
    parser.add_argument(
        "-i",
        "--input",
        required=True,
        type=str,
        help="Absolute path to the input media file",
    )
    parser.add_argument(
        "-o",
        "--output",
        required=True,
        type=str,
        help="Absolute path for the output artifact",
    )
    parser.add_argument(
        "-m",
        "--method",
        choices=["none", "spectral", "deepfilter"],
        default="deepfilter",
        help="Noise reduction / AI algorithm selection",
    )
    parser.add_argument(
        "--vad",
        choices=["none", "energy", "whisper", "silero"],
        default="silero",
        help="Voice Activity Detection strategy (Silero recommended for Acoustic precision)",
    )
    parser.add_argument(
        "--min-silence",
        type=float,
        default=0.5,
        help="Minimum silence gap in seconds to trigger a cut (default: 0.5)",
    )
    parser.add_argument(
        "--pad",
        type=float,
        default=0.2,
        help="Audio padding per cut boundary in seconds (default: 0.2)",
    )
    parser.add_argument(
        "-f",
        "--ffmpeg",
        default=r"C:\ProgramData\chocolatey\bin\ffmpeg.exe",
        type=str,
        help="Absolute path to FFmpeg binary",
    )

    args = parser.parse_args()

    try:
        strategy = StrategyFactory.create_noise_reduction(args.method)
        vad_strategy = StrategyFactory.create_vad(
            args.vad, min_silence_gap=args.min_silence, pad=args.pad
        )
        media_manager = FFmpegMediaManager(args.ffmpeg)

        processor = AudioProcessor(strategy, media_manager, vad_strategy)
        processor.execute(args.input, args.output)

    except Exception:
        logger.error(
            "FATAL ERROR: System failure encountered. Detailed stack trace below:"
        )
        logger.error(f"\n{traceback.format_exc()}")
        sys.exit(1)


if __name__ == "__main__":
    main()
