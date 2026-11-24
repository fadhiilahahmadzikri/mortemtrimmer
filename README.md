<p align="center">
  <img src="https://github.com/user-attachments/assets/1b7cb555-c8ed-4410-8aeb-15898604b8ac" alt="Mortem Banner" width="100%" />
</p>

<p align="center">
  <h1 align="center">Mortem Primer (Mortem Trimmer)</h1>
  <p align="center">
    <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-D99A2B.svg" alt="License: MIT" /></a>
    <a href="https://github.com/fadhiilahahmadzikri/mortemtrimmer"><img src="https://img.shields.io/badge/GitHub-fadhiilahahmadzikri%2Fmortemtrimmer-261E18.svg" alt="GitHub Repository" /></a>
    <img src="https://img.shields.io/badge/Platform-Windows%20x64-8C5A2B.svg" alt="Platform: Windows x64" />
    <img src="https://img.shields.io/badge/Runtime-100%25%20Offline%20AI-D99A2B.svg" alt="100% Offline AI" />
  </p>
  <p align="center">
    <strong>Self-Contained Offline AI Silence Remover &amp; Noise Reduction Production Suite</strong>
  </p>
  <p align="center">
    <em>Right-click any video in Windows Explorer or automate via CLI — remove dead air, suppress background noise, and preserve broadcast-ready AV sync offline.</em>
  </p>
  <p align="center">
    <a href="#author">Author</a> •
    <a href="#features">Features</a> •
    <a href="#installing-from-exe-windows">Install (.exe)</a> •
    <a href="#cheat-sheet">Cheat Sheet</a> •
    <a href="#vad--noise-reduction">AI Engines</a> •
    <a href="#project-tree-structure">Tree Structure</a> •
    <a href="#credits">Credits</a>
  </p>
</p>

---

## Author

- **Author & Maintainer**: Fadhiilah Ahmad Zikri ([github.com/fadhiilahahmadzikri](https://github.com/fadhiilahahmadzikri))
- **Repository**: [github.com/fadhiilahahmadzikri/mortemtrimmer](https://github.com/fadhiilahahmadzikri/mortemtrimmer)
- **License**: [MIT License](LICENSE) — Copyright (c) 2026 Fadhiilah Ahmad Zikri

---

## What is Mortem Primer?

**Mortem Primer** (**Mortem**) is a production-grade Windows desktop and CLI media pipeline that automatically detects and removes silent pauses from audio and video files, optionally cleans background noise, verifies stream integrity with PyAV, and writes non-destructive outputs beside your source files.

The Windows installer ships **100% self-contained and offline-ready**: FFmpeg, PyTorch CPU, neural VAD models (Silero VAD `v6.2`, Faster-Whisper `tiny`/`base`), DeepFilterNet3 denoiser checkpoints, and Spectral Gating libraries are all bundled inside the executable — zero post-install downloads or internet access required.

---

## Features

| Area | Capabilities |
|---|---|
| **Zero-Setup Offline Installer** | Single Windows x64 Inno Setup `.exe` bundling Python 3.11.5 runtime, managed FFmpeg, neural weights, and desktop apps |
| **Explorer Right-Click Integration** | Per-user **Trim This Video** context menu powered by a `<100ms` native shim (`trim-shim.exe`) with multi-select IPC batching |
| **System Tray & Progress Popup** | Unobtrusive tray daemon with real-time stage/engine label, ETA progress bar, pause/resume/cancel controls, and desktop notifications |
| **PyQt6 Settings UI (`--tune`)** | Five-tab gold-and-bronze configuration editor (`General`, `Speech and Audio`, `Encoding and Speed`, `Files and Output`, `System and Updates`) with instant daemon hot-reload |
| **Preserved Log Viewer (`--logs`)** | Strict append-only log history (`app.log`), live 1s tailing, level filtering (`All Levels`, `Errors`, `Warnings`, `Info`), and zero silent failures |
| **Attribution & About (`--about`)** | Help menu, offline Octicons GitHub link, About dialog displaying copyright/license, bundled `THIRD_PARTY_NOTICES.txt` viewer, and Windows PE VersionInfo metadata |
| **4 Speech Detection Engines** | Silero Neural VAD (`silero`), Faster-Whisper Semantic VAD (`whisper`), Energy Level Gate (`energy`), or pass-through (`none`) |
| **2 Noise Reduction Modes** | DeepFilterNet3 deep speech enhancement (`deepfilter`) and noisereduce Spectral Gating (`spectral`) |
| **Adaptive Parallel Encoding** | Keyframe-aligned multi-chunk splitting with GPU policies (`G1 Hard Gate`, `G2 GPU Preferred -> CPU Fallback`, `G3 CPU Only`) supporting `h264_nvenc`, `h264_qsv`, `h264_amf`, and `libx264` |
| **Non-Destructive Safety Guards** | Atomic temp writes, PyAV post-encode stream & duration verification, free disk-space safety checks, and `{name}.trimmed.{ext}` naming |
| **Deterministic CI/CD Pipeline** | Unified `scripts/ci.ps1` + GitHub Actions workflow using pinned `requirements.lock` hashes, SHA-256 model verification, `<2 GB` installer guard, and offline clean-room smoke checks |

---

## Installing from `.exe` (Windows)

### Option A: Interactive Windows Installer (Recommended)

1. Download **`MortemPrimer-Setup-<version>-win-x64.exe`** from [GitHub Releases](https://github.com/fadhiilahahmadzikri/mortemtrimmer/releases).
2. Double-click the `.exe` installer (no Administrator password required — installs per-user into `%LOCALAPPDATA%\Programs\AutoSilentTrimmer`).
3. Review the **MIT License** and bundled **Third-Party Notices**, then choose optional tasks:
   - **Register right-click 'Trim This Video' menu in File Explorer** *(enabled by default)*
   - **Start Mortem Primer background service on sign-in** *(optional)*
4. After installation completes:
   - **Trim directly**: Right-click any `.mp4`, `.mkv`, `.mov`, `.webm`, `.wav`, `.mp3`, etc. file in File Explorer -> **Trim This Video**.
   - **Configure settings**: Open **Settings - Mortem Primer** from Start Menu (or tray menu -> **Settings**).
   - **Inspect activity/errors**: Open **System Logs - Mortem Primer** from Start Menu (or tray popup -> **View Logs**).

### Option B: Silent / Automated Installation

```powershell
# Silent install with File Explorer context menu enabled:
.\MortemPrimer-Setup-1.0.0-win-x64.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /TASKS=contextmenu

# Silent install into a custom folder without registering shell context menu:
.\MortemPrimer-Setup-1.0.0-win-x64.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /DIR="D:\Apps\MortemPrimer" /TASKS=none
```

### What Is Bundled Inside the Installer?

Everything runs locally offline after install (`0` runtime downloads):

- `autosilenttrimmer.exe` & `autosilenttrimmer-cli.exe` (PyInstaller 6 Windows PE executables with `Mortem Primer` icon & VersionInfo metadata)
- `trim-shim.exe` (ultra-fast Explorer IPC shell dispatcher)
- Managed FFmpeg & PyAV runtime
- Pre-installed AI stack: CPU `torch` `2.8.0+cpu`, `torchaudio`, `faster-whisper`, `ctranslate2`, `deepfilternet`, `noisereduce`, `scipy`, `onnxruntime`, `matplotlib`, `seaborn`, `PyQt6`
- Pre-verified offline model weights (`packaging/offline_models`): Silero VAD `v6.2`, Faster-Whisper `tiny` & `base`, and `DeepFilterNet3`
- Legal & notice files: `LICENSE` and `THIRD_PARTY_NOTICES.txt`

### Upgrading or Cleanly Removing Before Re-Testing

Before installing a newer test build (or cleanly removing an installation), run the cleaner utility — it safely terminates running binaries, runs the uninstaller, cleans Explorer shell entries, and **preserves your `app.log` and `settings.json` by default**:

```powershell
# Preview cleanup actions without deleting anything:
python scripts/clean_install.py --dry-run

# Clean uninstall while preserving %LOCALAPPDATA%\autosilenttrimmer logs & settings:
python scripts/clean_install.py

# Clean uninstall INCLUDING removing logs, settings, and downloaded runtime packs:
python scripts/clean_install.py --purge-data
```

---

## Cheat Sheet

### Desktop & Installed CLI Commands

| Command | Purpose |
|---|---|
| `autosilenttrimmer-cli.exe --version` | Print product name, version, author, copyright, and GitHub URL |
| `autosilenttrimmer-cli.exe --check` | Run full pre-flight diagnostic audit (FFmpeg, GPU, AI models, PyQt6, Shell) |
| `autosilenttrimmer.exe --daemon --tray` | Start background IPC worker service with tray icon and progress popup |
| `autosilenttrimmer.exe --tune` | Open the 5-tab PyQt6 Settings window |
| `autosilenttrimmer.exe --logs` | Open the append-only PyQt6 System Logs & Activity viewer |
| `autosilenttrimmer.exe --about` | Open the About dialog (version, copyright, GitHub link, Third-Party Notices) |
| `autosilenttrimmer-cli.exe --register-shell` | Register per-user `'Trim This Video'` right-click menu in Windows Explorer |
| `autosilenttrimmer-cli.exe --unregister-shell` | Remove `'Trim This Video'` File Explorer registry entries cleanly |
| `autosilenttrimmer-cli.exe --enqueue a.mp4 b.mp4` | Submit media files directly to the running background daemon queue |
| `autosilenttrimmer-cli.exe --export-diagnostics` | Export anonymized logs, settings, and readiness JSON into a diagnostics `.zip` |

### Media Trimming CLI Flags (Run From Source or Frozen CLI)

```powershell
# Default Silero VAD trim beside source -> writes video.trimmed.mp4
autosilenttrimmer-cli.exe -i video.mp4

# Explicit output + Silero VAD + DeepFilterNet3 neural denoising + timeline chart
autosilenttrimmer-cli.exe -i raw.mp4 -o clean.mp4 --vad silero -m deepfilter --visual-plot

# Whisper Semantic VAD (specify spoken language code) + custom silence bounds
autosilenttrimmer-cli.exe -i podcast.mkv -o podcast_clean.mkv --vad whisper --lang en --min-silence 0.35 --pad 0.15

# Fast Energy Gate trim + Spectral Gating denoise + CPU-only execution policy
autosilenttrimmer-cli.exe -i voice.wav -o voice_clean.wav --vad energy -m spectral --gpu-policy g3_cpu_only

# Override worker count and explicit FFmpeg executable
autosilenttrimmer-cli.exe -i clip.mp4 -o clip_out.mp4 --max-workers 4 -f "C:\ffmpeg\bin\ffmpeg.exe"
```

| Flag | Values / Type | Default | Description |
|---|---|---|---|
| `-i`, `--input` | `path` | — | Input video or audio file |
| `-o`, `--output` | `path` | `{name}.trimmed.{ext}` | Custom destination path |
| `--vad` | `silero \| whisper \| energy \| none` | `silero` (or `settings.json`) | Speech detection engine |
| `-m`, `--method` | `none \| spectral \| deepfilter` | `none` (or `settings.json`) | Audio noise reduction mode |
| `--strategy` | `auto-silence \| manual-range` | `auto-silence` | Trimming strategy plugin |
| `--gpu-policy` | `g2_gpu_preferred \| g1_hard_gate \| g3_cpu_only` | `g2_gpu_preferred` | Compute backend & fallback policy |
| `--min-silence` | `float` (seconds) | `0.5` | Minimum silence gap required to split/remove |
| `--pad` | `float` (seconds) | `0.2` | Safety audio margin kept around active speech |
| `--max-workers` | `int` | adaptive (`None`) | Override maximum parallel chunk encode workers |
| `-f`, `--ffmpeg` | `path` | auto-managed | Override FFmpeg binary path |
| `--lang` | `en \| id` | `en` | UI/notification locale & Whisper hint |
| `--visual-plot` | `flag` | `False` | Export `{output}.plot.png` speech timeline graphic |
| `-V`, `--version` | `flag` | — | Show version, authorship, and repository info |
| `--check` | `flag` | — | Run system readiness check and exit |

### Developer, Build & CI/CD Cheat Sheet

```powershell
# 1. Create clean Python 3.11.5 venv & install strictly hashed requirements.lock
uv venv --python 3.11.5 .venv
pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/ci.ps1 -Stage deps

# 2. Run discrete pipeline stages (identical locally and in GitHub Actions)
pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/ci.ps1 -Stage lint          # Ruff check/format + git-tracked 500-line gate
pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/ci.ps1 -Stage test          # Fast + slow pytest suites with >=70% coverage gate
pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/ci.ps1 -Stage stage-models  # Download & SHA-256 verify offline AI checkpoints
pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/ci.ps1 -Stage build         # Generate notices + build PyInstaller shim & Full AI bundle
pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/ci.ps1 -Stage package       # Compile Inno Setup installer (<2GB check) + .sha256
pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/ci.ps1 -Stage smoke         # Offline frozen + silent install verification (Silero/Whisper/DeepFilter)
pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/ci.ps1 -Stage all           # Run full end-to-end release pipeline
```

| Makefile / Tool Command | Action |
|---|---|
| `make bootstrap` | Install dependencies and activate multi-stage `pre-commit` / `commit-msg` / `pre-push` git hooks |
| `make lint` / `make format` | Run Ruff linter (`check`) or formatter (`format`) |
| `make readiness` | Run `scripts/run_readiness.py` diagnostics |
| `make stage-models` | Stage & verify offline models against `packaging/offline_models.manifest.json` |
| `make clean-install` | Run `scripts/clean_install.py` post-test cleaner |
| `cz bump --dry-run` / `cz bump` | Bump SemVer across `pyproject.toml`, `branding.py`, `installer.iss`, and `CITATION.cff` cleanly |

---

## Developer Setup (From Source)

1. **Clone the canonical repository:**

```bash
git clone https://github.com/fadhiilahahmadzikri/mortemtrimmer.git
cd mortemtrimmer
```

2. **Create a Python `3.11.5` virtual environment & install locked hashes (recommended via `uv`):**

```powershell
uv venv --python 3.11.5 .venv
pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/ci.ps1 -Stage deps
```

*(Alternatively install editable development dependencies via `python scripts/setup_dev.py` or `make bootstrap`, which also installs `pre-commit`, `commit-msg`, and `pre-push` hooks.)*

3. **Verify your environment:**

```powershell
.\.venv\Scripts\python.exe main.py --check
```

---

## VAD & Noise Reduction

### Speech Detection (VAD)

- **Silero Neural VAD (`silero`, default)**: Fast CPU/GPU neural acoustic speech detector; pre-bundled offline (`snakers4/silero-vad:v6.2`).
- **Whisper Semantic VAD (`whisper`)**: Uses Faster-Whisper CTranslate2 models (`tiny` and `base` pre-bundled offline) for word-timestamp alignment — ideal when recordings contain ambient music or soft pauses.
- **Energy Level Gate (`energy`)**: Zero-neural-dependency RMS dB adaptive envelope gate; ultra-fast for crisp studio speech recordings.

### Noise Reduction

- **Off (`none`, default)**: Pure silence removal without modifying speech timbre.
- **DeepFilterNet 3 (`deepfilter`)**: Chunked deep-learning speech enhancement preserving vocal clarity; model checkpoints pre-bundled offline.
- **Spectral Gating (`spectral`)**: Signal-processing stationary/non-stationary noise floor suppression powered by `noisereduce` + `scipy`.

---

## Output Files & Environment Overrides

- Trimmed output defaults to **`{name}.trimmed.{ext}`** in the same folder as your input (never overwrites original source files).
- Optional `--visual-plot` exports **`{output}.plot.png`** in obsidian-and-gold timeline styling.
- Per-user runtime directory (`%LOCALAPPDATA%\autosilenttrimmer` on Windows):
  - `logs/app.log` — strict append-only activity & error log history
  - `settings.json` — persistent user settings synchronized between `--tune` UI and background daemon
- Environment overrides (useful for portable/CI isolation):
  - `AUTOSILENTTRIMMER_DATA_DIR` — override per-user logs/settings/cache root directory
  - `AUTOSILENTTRIMMER_MODELS_DIR` — exclusively override bundled offline models directory
  - `QT_QPA_PLATFORM=offscreen` — run GUI suites headlessly in CI/tests

---

## Project Tree Structure

The codebase follows **Feature-First Clean Architecture (OOP, SOLID)** with strict dependency separation (`domain` <- `application` <- `infrastructure` & `presentation`):

```text
mortemtrimmer/
├── .github/workflows/ci-cd.yml                 # Pinned Windows CI/CD build, test, installer & release DAG
├── .pre-commit-config.yaml                     # pre-commit (Ruff + 500-line gate), commit-msg, pre-push hooks
├── CITATION.cff                                # Citation File Format 1.2.0 metadata
├── LICENSE                                     # MIT License (Copyright (c) 2026 Fadhiilah Ahmad Zikri)
├── Makefile                                    # Developer task shortcuts
├── pyproject.toml                              # Package metadata, URLs, Ruff, Pytest, Coverage, Commitizen
├── requirements.lock / requirements.txt        # Hash-locked Python 3.11.5 dependencies (CPU PyTorch 2.8.0+cpu)
├── main.py                                     # Root development CLI launcher
├── README.md
│
├── autosilenttrimmer/                          # Core application package (SPDX MIT headers)
│   ├── branding.py                             # Single Source of Truth: author, copyright, version, URLs
│   ├── __init__.py / __main__.py
│   ├── core/                                   # Constants, dataclass configs, exceptions, i18n, UI schema
│   │   ├── config.py / constants.py / exceptions.py / settings_schema.py
│   │   ├── i18n/                               # English & Indonesian message catalogs (catalog_en.py, catalog_id.py)
│   │   └── schema/                             # Underscore-free Tune UI field descriptors (pipeline & execution)
│   ├── domain/                                 # Pure domain contracts (ABCs), entities, events & models
│   │   ├── contracts/                          # compute, diagnostic, event_bus, ffmpeg, ipc, media, notifier, shell, vad...
│   │   ├── entities/                           # job.py, segment.py
│   │   └── models/                             # processing_command, processing_result, readiness, settings, events...
│   ├── application/                            # Pure use cases & planners (no framework lock-in)
│   │   ├── services/                           # chunk_planner, execution_planner, output_path_resolver, worker_pool
│   │   └── use_cases/                          # process_media, job_orchestrator, _job_events, system_readiness, diagnose_export
│   ├── infrastructure/                         # External integrations (FFmpeg, PyAV, AI engines, IPC, OS shells)
│   │   ├── compute/                            # capability_prober.py, backend_selector.py (G1/G2/G3 policies)
│   │   ├── diagnostics/                        # engines.py, ffmpeg.py, hardware.py, runtime_pack.py
│   │   ├── events/                             # in_memory_bus.py
│   │   ├── ipc/                                # Windows Named Pipe / Unix Socket gateway with multi-select coalescing
│   │   ├── media/                              # ffmpeg_locator, ffmpeg_manager, pyav_prober, pyav_verifier
│   │   ├── noise_reduction/                    # deepfilter.py (offline/chunked), spectral.py, factory.py
│   │   ├── notify/                             # desktop_notifier_adapter.py, composite_notifier.py
│   │   ├── platform/                           # paths.py, priority.py, shell/{factory,windows_registry}.py
│   │   ├── runtime/                            # model_paths.py (offline weights resolver), manifest_client, pack_manager
│   │   ├── storage/                            # settings_repo.py, job_manifest_repo.py
│   │   ├── strategies/                         # auto_silence.py, manual_range.py
│   │   ├── updater/                            # manifest_updater.py
│   │   ├── vad/                                # silero.py, whisper.py, energy.py, factory.py
│   │   └── visualization/                      # timeline_plotter.py
│   └── presentation/                           # Desktop PyQt6 windows, system tray, popup & CLI
│       ├── theme.py                            # Obsidian-and-gold QSS theme, icon tinting, stage/error formatters
│       ├── qt_app.py                           # Shared Fusion palette, window icon & single-instance IPC launcher
│       ├── about_dialog.py / about_entry.py    # About dialog, Third-Party Notices viewer, Help menu, GitHub button
│       ├── assets/                             # mortem_icon.png, mortem_tray.png, github_mark.svg, SVG UI controls
│       ├── cli/                                # parser.py, runner.py, runtime_builder.py, readiness_presenter.py
│       ├── tune/                               # PyQt6 Settings window (tune_window.py, field_factory.py, app_entry.py)
│       ├── logs/                               # Preserved System Logs viewer (log_viewer.py, app_entry.py)
│       └── tray/                               # pystray tray menu (tray_app.py) & progress overlay (progress_popup.py)
│
├── packaging/
│   ├── offline_models.manifest.json            # Pinned SHA-256 inventory for Silero v6.2, Whisper tiny/base, DeepFilterNet3
│   ├── manifests/                              # notices_generator.py (SBOM & notices), release-manifest.schema.json
│   ├── pyinstaller/                            # core.spec, shim.spec, version_info.py (Windows PE Details metadata)
│   ├── runtime_packs/                          # Cross-platform pack archive builder (build_pack.py)
│   └── windows/                                # installer.iss (Inno Setup 6 script), mortem.ico
│
├── scripts/
│   ├── ci.ps1                                  # Single fail-fast entrypoint for local & CI stages
│   ├── clean_install.py                        # Safe uninstaller & leftover cleaner (preserves logs by default)
│   ├── stage_offline_models.py                 # Downloads & SHA-256 verifies offline neural model weights
│   ├── verify_frozen_offline.py                # Clean-room verifier: PE VersionInfo, --check, --about, offline AI trims
│   ├── shell_shim.py                           # Fast <100ms Explorer context menu IPC shim
│   ├── pre_commit_check.py                     # Git-tracked 500-line & hygiene gate
│   ├── check_commit_msg.py                     # Conventional Commits validator
│   └── run_readiness.py / setup_dev.py / sign_manifest.py / run_sparse_sample_matrix.py
│
└── tests/
    ├── conftest.py / fixtures/smoke_speech.wav # Deterministic media synthesis & offline speech smoke WAV
    ├── unit/                                   # Branding parity, UI attribution, cleaner, planners, runtime, tray/logs
    └── integration/                            # IPC coalescing, HTTP Range downloads, golden AV pipelines
```

---

## Troubleshooting

| Issue | Solution |
|---|---|
| Setup prompts to close running app on upgrade | Upgrade using latest installer (`PrepareToInstall` stops background tray/shim processes automatically) or run `python scripts/clean_install.py` first |
| Inspect why a right-click job failed | Click **View Logs** on the progress popup or open **System Logs - Mortem Primer** (`--logs`) — all history in `app.log` is preserved append-only |
| Override storage / logs directory in portable runs | Set `AUTOSILENTTRIMMER_DATA_DIR=<folder>` before launching |
| CUDA unavailable warning on CPU-only PC | Expected under `G2 GPU Preferred` — processing automatically uses CPU inference & `libx264` cleanly |
| Custom FFmpeg binary needed | Configure **Custom FFmpeg Executable** in Settings (`--tune`) or pass `-f / --ffmpeg <path>` |

---

## License

Copyright (c) 2026 Fadhiilah Ahmad Zikri. This project is open source and licensed under the [MIT License](LICENSE).

## Credits

Mortem Primer is an independent project by Fadhiilah Ahmad Zikri built atop external open-source libraries, tools, and pretrained models whose separate copyrights and licenses remain intact (see `THIRD_PARTY_NOTICES.txt` in distributed builds or **Help -> About -> Third-Party Notices**):

- [Silero VAD](https://github.com/snakers4/silero-vad) (MIT License)
- [Faster-Whisper](https://github.com/SYSTRAN/faster-whisper) / OpenAI Whisper (MIT License)
- [DeepFilterNet](https://github.com/Rikorose/DeepFilterNet) (MIT / Apache-2.0 License)
- [PyTorch](https://pytorch.org/) (BSD-3-Clause License), [PyQt6](https://riverbankcomputing.com/), [FFmpeg](https://ffmpeg.org/), and [GitHub Octicons](https://github.com/primer/octicons) (MIT License)

---

## Star This Repo

If this tool saved you time, please **star [fadhiilahahmadzikri/mortemtrimmer](https://github.com/fadhiilahahmadzikri/mortemtrimmer)** — it helps others discover it!

---

<p align="center">
  <strong>by <a href="https://github.com/fadhiilahahmadzikri">Fadhiilah Ahmad Zikri</a></strong>
</p>

<!-- SEO Tags & Keywords -->
<!-- mortem primer, mortem trimmer, mortemtrimmer, auto silence remover, remove silence from video,
     remove silence from audio, silence trimmer, auto cut silence, automatic silence removal,
     offline ai video trimmer, windows silence remover, ffmpeg silence detection, voice activity detection,
     silero vad, whisper vad, deepfilternet3, noise reduction, background noise removal, podcast editor,
     youtube editor, ai audio cleaner, non-destructive video editor -->
