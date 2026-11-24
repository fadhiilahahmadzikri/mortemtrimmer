# Linux Packaging Target Contract (Future Phase)

This directory defines the platform extension boundary for `linux-x86_64` and `linux-aarch64`.

## Architecture Mapping
- **Distribution Format**: Self-contained `AppImage` + `.deb` package built from `packaging/pyinstaller/core.spec`.
- **Compute Backend**: Automatically resolved by `CrossPlatformCapabilityProber`:
  - `ai_device`: `"cuda"` / `"rocm"` -> CPU fallback under Policy G2.
  - `video_encoder`: `"h264_nvenc"` / `"h264_vaapi"` validated via 1-frame FFmpeg probe.
- **Notifications**: `DesktopNotifierAdapter` uses `dbus-fast` (`org.freedesktop.Notifications`) natively.
- **IPC Transport**: `LocalIPCGateway` automatically selects `AF_UNIX` under `$XDG_RUNTIME_DIR` or `cache_dir`.
- **Shell Integration**: Replace `StubShellIntegrationAdapter` with `LinuxDesktopShellAdapter` writing `~/.local/share/applications/trim-this-video.desktop` + Nautilus/Dolphin service menu actions.
- **Release Manifest Slot**: Emits `installers["linux-x86_64"]` and `runtime_packs["ffmpeg-linux-x86_64"]` / `runtime_packs["ai-cpu-linux-x86_64"]`.
