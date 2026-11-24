<p align="center">
  <img src="https://github.com/user-attachments/assets/1b7cb555-c8ed-4410-8aeb-15898604b8ac" alt="Mortem Banner" width="100%" />
</p>

<p align="center">
  <h1 align="center">Auto Silent Trimmer</h1>
  <p align="center">
    <strong>State-of-the-Art AI-Powered Silence Remover & Noise Reduction Pipeline</strong>
  </p>
  <p align="center">
    <em>Remove silence, kill background noise, and produce broadcast-ready audio/video — all in one command.</em>
  </p>
  <p align="center">
    <a href="#features">Features</a> •
    <a href="#installation">Installation</a> •
    <a href="#usage">Usage</a> •
    <a href="#vad-engines">VAD Engines</a> •
    <a href="#noise-reduction">Noise Reduction</a> •
    <a href="#examples">Examples</a>
  </p>
</p>

---

## What is Mortem?

**Mortem** is a production-grade Python CLI tool that automatically detects and removes silent segments from audio and video files using cutting-edge Voice Activity Detection (VAD) models, then optionally applies deep-learning-based noise reduction to produce crystal-clear output.

Whether you're a **YouTuber**, **podcaster**, **video editor**, or **content creator** — this tool saves you hours of manual editing by intelligently trimming dead air and cleaning up noisy recordings with a single command.

---

## Features

| Feature | Description |
|---|---|
| **3 VAD Engines** | Silero VAD (neural), Whisper Semantic VAD, Energy-based VAD |
| **2 Noise Reduction Modes** | DeepFilterNet3 (SOTA deep learning) & Spectral Gating |
| **Video + Audio Support** | Process MP4, MKV, AVI, MOV, WAV, MP3, AAC, and more |
| **CUDA Acceleration** | GPU-accelerated inference for blazing-fast processing |
| **Scientific Visualization** | Auto-generates speech segment plots (timeline chart) |
| **Speech Manifest** | Exports timestamped transcript of all detected speech segments |
| **Zero AV-Drift Splicing** | Frame-accurate trim+concat via FFmpeg filter graphs |
| **Strategy Pattern Architecture** | Clean, extensible OOP design — plug in your own engines |

---

## Requirements

- **Python** 3.10+
- **FFmpeg** installed and accessible (or provide the path via `--ffmpeg`)
- **CUDA** (optional, for GPU acceleration with DeepFilterNet3 and Whisper)

---

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/fadhiilahahmadzikri/autosilenttrimmer.git
cd autosilenttrimmer
```

### 2. Create a Virtual Environment

```bash
python -m venv .venv
```

**Activate the virtual environment:**

- **Windows (PowerShell):**
  ```powershell
  .\.venv\Scripts\Activate.ps1
  ```

- **Windows (CMD):**
  ```cmd
  .\.venv\Scripts\activate.bat
  ```

- **Linux / macOS:**
  ```bash
  source .venv/bin/activate
  ```

### 3. Install Dependencies

```bash
pip install numpy soundfile torch torchaudio noisereduce tqdm matplotlib seaborn
```

**For DeepFilterNet3 noise reduction (recommended):**
```bash
pip install deepfilternet
```

**For Whisper-based VAD:**
```bash
pip install faster-whisper
```

### 4. FFmpeg Integration

FFmpeg is **automatically managed out of the box** via `imageio-ffmpeg` upon running `pip install -r requirements.txt`. No manual installation or Chocolatey setup is required!

If you prefer to use your own system FFmpeg binary instead, you can:
- Ensure `ffmpeg` is in your system `PATH`, OR
- Pass the explicit path via `-f / --ffmpeg <path>`.

---

## Usage

### Basic Syntax

```bash
python main.py -i <input_file> -o <output_file> [options]
```

or via package execution:
```bash
python -m autosilenttrimmer -i <input_file> -o <output_file> [options]
```

### Pre-Flight System Readiness Check

Verify your hardware acceleration, FFmpeg integration, and deep learning engines:
```bash
python main.py --check
```

### Command-Line Arguments

| Argument | Type | Default | Description |
|---|---|---|---|
| `--check` | `flag` | `False` | Run comprehensive system readiness diagnostics and exit |
| `-i`, `--input` | `str` | **(required)** | Path to the input audio/video file |
| `-o`, `--output` | `str` | **(required)** | Path for the output file |
| `-m`, `--method` | `str` | `deepfilter` | Noise reduction method: `none`, `spectral`, `deepfilter` |
| `--vad` | `str` | `silero` | VAD engine: `none`, `energy`, `whisper`, `silero` |
| `--min-silence` | `float` | `0.5` | Minimum silence duration (seconds) to trigger a cut |
| `--pad` | `float` | `0.2` | Padding (seconds) added around each speech boundary |
| `-f`, `--ffmpeg` | `str` | `auto-detected` | Path to FFmpeg executable (default: auto-detected via managed binary or PATH) |

---

## VAD Engines

### Silero VAD (Default — Recommended)
Neural network-based acoustic voice activity detection. Fastest and most reliable for general use.
```bash
python main.py -i input.mp4 -o output.mp4 --vad silero
```

### Whisper Semantic VAD
Uses OpenAI's Whisper model to transcribe audio and extract word-level timestamps. Best for content where semantic accuracy matters (e.g., podcasts with music).
```bash
python main.py -i input.mp4 -o output.mp4 --vad whisper
```

### Energy-Based VAD
Lightweight, zero-dependency VAD using signal energy thresholding. Great for clean recordings with obvious silence gaps.
```bash
python main.py -i input.wav -o output.wav --vad energy
```

---

## Noise Reduction

### DeepFilterNet3 (Default — SOTA)
State-of-the-art deep neural network for real-time speech enhancement. Supports CUDA GPU acceleration with chunked processing for O(1) memory usage.
```bash
python main.py -i input.mp4 -o output.mp4 -m deepfilter
```

### Spectral Gating
Classic signal processing approach using `noisereduce` library. Lightweight and CPU-friendly.
```bash
python main.py -i input.wav -o output.wav -m spectral
```

### No Noise Reduction
Skip noise reduction entirely — only perform silence trimming.
```bash
python main.py -i input.mp4 -o output.mp4 -m none
```

---

## Examples

### Remove silence from a video (default settings)
```bash
python main.py -i raw_video.mp4 -o clean_video.mp4
```

### Podcast cleanup with aggressive silence removal
```bash
python main.py -i podcast.wav -o podcast_clean.wav --min-silence 0.3 --pad 0.1
```

### Video with only silence trimming (no noise reduction)
```bash
python main.py -i lecture.mp4 -o lecture_trimmed.mp4 -m none --vad silero
```

### Full pipeline with Whisper VAD + DeepFilterNet3
```bash
python main.py -i interview.mkv -o interview_clean.mkv -m deepfilter --vad whisper
```

### Audio-only processing with spectral gating
```bash
python main.py -i recording.wav -o recording_clean.wav -m spectral --vad energy
```

### Custom FFmpeg path
```bash
python main.py -i input.mp4 -o output.mp4 -f /usr/bin/ffmpeg
```

---

## Output Files

After processing, the tool generates:

| File | Description |
|---|---|
| `output.mp4` | The final cleaned & trimmed media file |
| `output.mp4.manifest.txt` | Timestamped speech segment transcript |
| `output.mp4.plot.png` | Scientific visualization of speech vs silence timeline |

---

## Architecture

The project is structured according to **Feature-First Clean Architecture (OOP, SOLID)** with strict layer decoupling and zero hardcoding:

```
autosilenttrimmer/
├── core/                         # Constants, configurations, and domain exceptions
│   ├── config.py
│   ├── constants.py
│   └── exceptions.py
├── domain/                       # Core business contracts, entities, and models
│   ├── contracts/                # Abstractions (IMediaManager, IVoiceActivityDetector, etc.)
│   ├── entities/                 # Value objects (MediaSegment)
│   └── models/                   # Command and Result DTOs
├── application/                  # Pure application orchestration
│   └── use_cases/
│       └── process_media.py      # ProcessMediaUseCase
├── infrastructure/               # Concrete external library implementations
│   ├── media/                    # FFmpegMediaManager
│   ├── noise_reduction/          # DeepFilterNet & SpectralGating strategies + Factory
│   ├── vad/                      # Silero, Whisper & Energy-based VADs + Factory
│   └── visualization/            # Matplotlib & Seaborn timeline plotter
└── presentation/                 # Presentation and CLI interface
    └── cli/
        ├── parser.py             # CLI argument definitions
        └── runner.py             # Composition root and execution runner
```

---

## Developer Workflow & Git Hooks

This repository adheres to an enterprise Git hooks and code quality infrastructure with multi-stage verification:

### 1. Setup Development Environment
```bash
# Using Makefile
make bootstrap

# Or using Python:
python scripts/setup_dev.py
```

### 2. Available Make Targets
- `make lint` : Run Ruff linter across the entire repository.
- `make format` : Format all files with Ruff.
- `make readiness` : Execute the full pre-flight system readiness diagnostic.
- `make check` : Execute all pre-commit hooks on all files.

### 3. Git Hooks Quality Gates
- **`pre-commit`** : Fast Ruff check, formatting, and Clean Architecture file length & hygiene gate (<3s).
- **`commit-msg`** : Conventional Commits enforcement (`feat`, `fix`, `chore`, `docs`, `refactor`, etc.) (<1s).
- **`pre-push`** : Deep system readiness diagnostic audit (<60s).

---

## Troubleshooting

| Issue | Solution |
|---|---|
| `WinError 127` (DLL conflict) | Run `pip uninstall torch torchaudio -y` then `pip install torch torchaudio` |
| FFmpeg not found | Install FFmpeg or pass the correct path via `--ffmpeg` |
| CUDA out of memory | DeepFilterNet3 uses chunked processing — try reducing chunk size or use CPU |
| Whisper VAD is slow | Use `silero` VAD instead for faster processing |

---

## License

This project is open source and available under the [MIT License](LICENSE).

---

## Star This Repo

If this tool saved you time, please **star this repository** — it helps others discover it!

---

<p align="center">
  <strong>Built by <a href="https://github.com/fadhiilahahmadzikri">fadhiilahahmadzikri</a></strong>
</p>

<!-- SEO Tags & Keywords -->
<!-- mortem, auto silence remover, remove silence from video, remove silence from audio, silence trimmer, 
     auto cut silence, automatic silence removal, python silence remover, ffmpeg silence detection,
     voice activity detection, VAD, silero vad, whisper vad, deepfilternet, noise reduction,
     background noise removal, audio cleaner, video cleaner, podcast editor, youtube editor,
     content creator tools, ai audio processing, deep learning audio, speech enhancement,
     auto trim silence python, silence cutter, dead air remover, audio silence detector,
     remove pauses from video, automatic video editor, ai noise cancellation -->
