"""DeepFilterNet3 deep learning speech enhancement."""

from __future__ import annotations

import logging

from tqdm import tqdm

from autosilenttrimmer.core.config import NoiseReductionConfig
from autosilenttrimmer.core.exceptions import (
    DependencyMissingException,
    NoiseReductionException,
)
from autosilenttrimmer.domain.contracts.noise_reduction import INoiseReductionStrategy

logger = logging.getLogger(__name__)


class DeepFilterNetStrategy(INoiseReductionStrategy):
    """State-of-the-art DeepFilterNet3 neural noise suppression."""

    def __init__(
        self, config: NoiseReductionConfig | None = None, device: str | None = None
    ) -> None:
        self._config = config or NoiseReductionConfig()
        self._device = device

    def process(self, input_path: str, output_path: str) -> None:
        logger.info("Loading DeepFilterNet libraries and model...")
        try:
            import torch
            from df.enhance import enhance, init_df, load_audio, save_audio
        except OSError as e:
            if "WinError 127" in str(e):
                raise NoiseReductionException(
                    "Architectural conflict detected in PyTorch & Torchaudio DLLs (WinError 127). "
                    "Resolution: Execute 'pip uninstall torch torchaudio -y' followed by 'pip install torch torchaudio'."
                ) from e
            raise NoiseReductionException(f"Failed to load DeepFilterNet: {e}") from e
        except ImportError as e:
            raise DependencyMissingException(
                "Missing dependencies 'torch' and 'deepfilternet' for DeepFilterNet3."
            ) from e

        device = self._device or ("cuda" if torch.cuda.is_available() else "cpu")
        logger.info("Initializing DeepFilterNet3 on %s...", device.upper())

        with torch.inference_mode():
            model, df_state, _ = init_df(config_allow_defaults=True)
            model = model.to(device).eval()

            audio, _ = load_audio(input_path, sr=df_state.sr())
            chunk_size = int(df_state.sr() * self._config.chunk_duration_sec)
            audio_chunks = torch.split(audio, chunk_size, dim=1)
            enhanced_chunks = []

            logger.info("Processing %d audio chunks...", len(audio_chunks))
            with tqdm(total=len(audio_chunks), desc="DeepFilterNet3 Inference") as pbar:
                for chunk in audio_chunks:
                    enhanced_chunk = enhance(model, df_state, chunk)
                    enhanced_chunks.append(enhanced_chunk)
                    if device == "cuda":
                        torch.cuda.empty_cache()
                    pbar.update(1)

            enhanced = torch.cat(enhanced_chunks, dim=1)
            logger.info("Saving denoised audio artifact...")
            save_audio(output_path, enhanced, df_state.sr())
