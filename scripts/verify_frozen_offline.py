"""Clean-room frozen executable & installed app offline AI verification."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time
import wave
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SAMPLE_WAV = PROJECT_ROOT / "tests" / "fixtures" / "smoke_speech.wav"


def _wav_duration_sec(path: Path) -> float:
    with wave.open(str(path), "rb") as wf:
        frames = wf.getnframes()
        rate = wf.getframerate()
    if rate <= 0:
        raise RuntimeError(f"Invalid WAV sample rate in {path}: {rate}")
    return frames / float(rate)


def _build_isolated_env(work_dir: Path) -> tuple[dict[str, str], dict[str, Path]]:
    iso_root = work_dir / "isolated_env"
    dirs = {
        "torch_hub": iso_root / "torch_hub",
        "hf_home": iso_root / "hf_home",
        "localappdata": iso_root / "localappdata",
        "appdata": iso_root / "appdata",
        "temp": iso_root / "temp",
    }
    for d in dirs.values():
        d.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env.pop("AUTOSILENTTRIMMER_MODELS_DIR", None)
    env["AUTOSILENTTRIMMER_DATA_DIR"] = str(dirs["localappdata"] / "autosilenttrimmer")
    env["HF_HUB_OFFLINE"] = "1"
    env["TRANSFORMERS_OFFLINE"] = "1"
    env["TORCH_HOME"] = str(dirs["torch_hub"])
    env["HF_HOME"] = str(dirs["hf_home"])
    env["HUGGINGFACE_HUB_CACHE"] = str(dirs["hf_home"] / "hub")
    env["LOCALAPPDATA"] = str(dirs["localappdata"])
    env["APPDATA"] = str(dirs["appdata"])
    env["TEMP"] = str(dirs["temp"])
    env["TMP"] = str(dirs["temp"])
    env["QT_QPA_PLATFORM"] = "offscreen"
    return env, dirs


def _run_cli(
    cli_exe: Path,
    args: list[str],
    *,
    work_dir: Path,
    env: dict[str, str],
    timeout_sec: int = 180,
) -> subprocess.CompletedProcess[str]:
    cmd = [str(cli_exe), *args]
    print(f"-> ({work_dir}) {' '.join(cmd)}")
    proc = subprocess.run(
        cmd,
        cwd=str(work_dir),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout_sec,
    )
    if proc.returncode != 0:
        print("STDOUT:\n" + proc.stdout)
        print("STDERR:\n" + proc.stderr)
        raise RuntimeError(f"Frozen CLI command failed ({proc.returncode}): {' '.join(args)}")
    return proc


def _verify_version_and_pe_metadata(
    cli_exe: Path,
    exe_dir: Path,
    *,
    work_dir: Path,
    env: dict[str, str],
) -> None:
    res = _run_cli(cli_exe, ["--version"], work_dir=work_dir, env=env, timeout_sec=30)
    out = res.stdout
    for required in (
        "Mortem Primer",
        "Fadhiilah Ahmad Zikri",
        "Copyright (c) 2026 Fadhiilah Ahmad Zikri",
        "https://github.com/fadhiilahahmadzikri/mortemtrimmer",
    ):
        if required not in out:
            raise RuntimeError(
                f"Missing expected attribution token '{required}' in --version output:\n{out}"
            )

    targets = [
        exe_dir / "autosilenttrimmer.exe",
        exe_dir / "autosilenttrimmer-cli.exe",
    ]
    shim_same_dir = exe_dir / "trim-shim.exe"
    shim_parent_dir = exe_dir.parent / "trim-shim.exe"
    if shim_same_dir.is_file():
        targets.append(shim_same_dir)
    elif shim_parent_dir.is_file():
        targets.append(shim_parent_dir)

    ps_check = (
        "$files = @(" + ",".join(f"'{p}'" for p in targets) + "); "
        "foreach ($f in $files) { "
        "$vi = (Get-Item $f).VersionInfo; "
        "Write-Host ($f + ' => Company=' + $vi.CompanyName + ' | Product=' + $vi.ProductName + ' | Copyright=' + $vi.LegalCopyright); "
        "if ($vi.CompanyName -notmatch 'Fadhiilah Ahmad Zikri' -or $vi.LegalCopyright -notmatch 'Fadhiilah Ahmad Zikri' -or $vi.ProductName -notmatch 'Mortem Primer') { "
        "throw ('Invalid Windows VersionInfo metadata on ' + $f) } }"
    )
    pe_proc = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps_check],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    print(pe_proc.stdout.strip())
    if pe_proc.returncode != 0:
        raise RuntimeError(f"PE VersionInfo check failed:\n{pe_proc.stderr}")


def _verify_readiness(cli_exe: Path, *, work_dir: Path, env: dict[str, str]) -> None:
    res = _run_cli(cli_exe, ["--check"], work_dir=work_dir, env=env, timeout_sec=120)
    out = res.stdout
    for required in (
        "READY FOR INFERENCE",
        "FFmpeg Binary",
        "Silero Acoustic VAD",
        "Spectral Gating Denoiser",
        "DeepFilterNet3 Neural Denoiser",
        "Whisper Semantic VAD",
        "PyQt6 Tune UI",
    ):
        if required not in out:
            raise RuntimeError(f"Missing expected readiness marker '{required}' in --check output")
    if "[ERROR]" in out or "CRITICAL DEPENDENCY FAILURE" in out:
        raise RuntimeError("Critical error reported in --check output")
    for line in out.splitlines():
        if "[OPTIONAL_MISSING]" in line and "Shell Context Menu" not in line:
            raise RuntimeError(f"Unexpected missing AI/media component in --check: {line}")
    print("Readiness check passed cleanly.")


def _verify_offline_trims(
    cli_exe: Path,
    *,
    sample_wav: Path,
    work_dir: Path,
    env: dict[str, str],
    dirs: dict[str, Path],
) -> None:
    if not sample_wav.is_file():
        raise FileNotFoundError(f"Smoke speech sample WAV not found: {sample_wav}")
    in_wav = work_dir / "input.wav"
    shutil.copy2(sample_wav, in_wav)
    orig_dur = _wav_duration_sec(in_wav)

    cases: list[tuple[str, list[str]]] = [
        (
            "silero",
            [
                "-i",
                str(in_wav),
                "-o",
                str(work_dir / "out_silero.wav"),
                "--vad",
                "silero",
                "-m",
                "none",
                "--min-silence",
                "0.2",
                "--pad",
                "0.05",
                "--gpu-policy",
                "g3_cpu_only",
            ],
        ),
        (
            "whisper",
            [
                "-i",
                str(in_wav),
                "-o",
                str(work_dir / "out_whisper.wav"),
                "--vad",
                "whisper",
                "-m",
                "none",
                "--min-silence",
                "0.2",
                "--pad",
                "0.05",
                "--lang",
                "en",
                "--gpu-policy",
                "g3_cpu_only",
            ],
        ),
        (
            "deepfilter",
            [
                "-i",
                str(in_wav),
                "-o",
                str(work_dir / "out_deepfilter.wav"),
                "--vad",
                "silero",
                "-m",
                "deepfilter",
                "--min-silence",
                "0.2",
                "--pad",
                "0.05",
                "--gpu-policy",
                "g3_cpu_only",
            ],
        ),
    ]

    for label, args in cases:
        out_path = Path(args[args.index("-o") + 1])
        _run_cli(cli_exe, args, work_dir=work_dir, env=env, timeout_sec=180)
        if not out_path.is_file():
            raise RuntimeError(f"Offline {label} trim produced no output file: {out_path}")
        trimmed_dur = _wav_duration_sec(out_path)
        print(f"Offline {label} trim verified: {orig_dur:.2f}s -> {trimmed_dur:.2f}s")
        if trimmed_dur <= 0.3 or trimmed_dur >= orig_dur:
            raise RuntimeError(
                f"Unexpected {label} trimmed duration {trimmed_dur:.2f}s (orig={orig_dur:.2f}s)"
            )

    downloaded_torch = [p for p in dirs["torch_hub"].rglob("*") if p.is_file()]
    downloaded_hf = [p for p in dirs["hf_home"].rglob("*") if p.is_file()]
    if downloaded_torch or downloaded_hf:
        raise RuntimeError(
            f"Offline invariant violated! Unexpected hub files written: "
            f"torch={downloaded_torch}, hf={downloaded_hf}"
        )

    app_log = dirs["localappdata"] / "autosilenttrimmer" / "logs" / "app.log"
    if not app_log.is_file() or app_log.stat().st_size == 0:
        raise RuntimeError(f"Expected non-empty application log file at {app_log}")


def _verify_ui_flag(cli_exe: Path, flag: str, *, work_dir: Path, env: dict[str, str]) -> None:
    print(f"-> Verifying offscreen Qt entrypoint: {cli_exe.name} {flag}")
    proc = subprocess.Popen(
        [str(cli_exe), flag],
        cwd=str(work_dir),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    time.sleep(2.5)
    rc = proc.poll()
    if rc is not None:
        out, err = proc.communicate(timeout=5)
        if rc != 0:
            raise RuntimeError(
                f"Frozen UI {flag} exited abnormally ({rc}):\nSTDOUT:\n{out}\nSTDERR:\n{err}"
            )
    else:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)


def run_verification(
    exe_dir: Path,
    *,
    sample_wav: Path = DEFAULT_SAMPLE_WAV,
    work_dir: Path | None = None,
    skip_ui: bool = False,
) -> None:
    """Execute complete frozen offline readiness, inference, and UI smoke checks."""
    cli_exe = exe_dir / "autosilenttrimmer-cli.exe"
    gui_exe = exe_dir / "autosilenttrimmer.exe"
    for binary in (cli_exe, gui_exe):
        if not binary.is_file():
            raise FileNotFoundError(f"Expected frozen executable not found: {binary}")

    if work_dir is not None:
        work_dir.mkdir(parents=True, exist_ok=True)
        _run_inside(cli_exe, sample_wav=sample_wav, work_dir=work_dir, skip_ui=skip_ui)
    else:
        with tempfile.TemporaryDirectory(prefix="ast_frozen_smoke_") as tmp:
            _run_inside(cli_exe, sample_wav=sample_wav, work_dir=Path(tmp), skip_ui=skip_ui)


def _run_inside(cli_exe: Path, *, sample_wav: Path, work_dir: Path, skip_ui: bool) -> None:
    env, dirs = _build_isolated_env(work_dir)
    _verify_version_and_pe_metadata(cli_exe, cli_exe.parent, work_dir=work_dir, env=env)
    _verify_readiness(cli_exe, work_dir=work_dir, env=env)
    _verify_offline_trims(
        cli_exe,
        sample_wav=sample_wav,
        work_dir=work_dir,
        env=env,
        dirs=dirs,
    )
    if not skip_ui:
        _verify_ui_flag(cli_exe, "--tune", work_dir=work_dir, env=env)
        _verify_ui_flag(cli_exe, "--logs", work_dir=work_dir, env=env)
        _verify_ui_flag(cli_exe, "--about", work_dir=work_dir, env=env)
    print(f"All frozen offline smoke checks PASSED for {cli_exe.parent}")


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for frozen bundle & silent-installed offline verification."""
    parser = argparse.ArgumentParser(description="Verify frozen AutoSilentTrimmer offline bundle.")
    parser.add_argument(
        "--exe-dir", type=Path, required=True, help="Directory holding frozen exes."
    )
    parser.add_argument("--sample-wav", type=Path, default=DEFAULT_SAMPLE_WAV)
    parser.add_argument("--work-dir", type=Path, default=None)
    parser.add_argument("--skip-ui", action="store_true")
    args = parser.parse_args(argv)
    run_verification(
        args.exe_dir.resolve(),
        sample_wav=args.sample_wav.resolve(),
        work_dir=args.work_dir.resolve() if args.work_dir else None,
        skip_ui=args.skip_ui,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
