# macOS Packaging Target Contract (Future Phase)

This directory defines the platform extension boundary for `darwin-arm64` (Apple Silicon) and `darwin-x86_64`.

## Architecture Mapping
- **App Bundle**: PyInstaller `--onedir` -> `AutoSilentTrimmer.app` packaged inside notarized `.dmg`.
- **Compute Backend**: Automatically resolved by `CrossPlatformCapabilityProber`:
  - `ai_device`: `"mps"` (PyTorch Metal Performance Shaders) -> CPU fallback under Policy G2.
  - `video_encoder`: `"h264_videotoolbox"` hardware encoder validated via 1-frame FFmpeg probe.
- **Notifications**: `DesktopNotifierAdapter` handles Cocoa `UNUserNotificationCenter` natively.
- **Tray UI**: `PystrayTrayUI` binds Cocoa `NSStatusBar` icon natively.
- **Shell Integration**: Replace `StubShellIntegrationAdapter` with `MacOSQuickActionAdapter` installing an Automator / Finder Quick Action workflow invoking `autosilenttrimmer --enqueue "$@"` over Unix domain socket (`IPlatformPaths.cache_dir`).
- **Release Manifest Slot**: Emits `installers["darwin-arm64"]` and `runtime_packs["ffmpeg-darwin-arm64"]` / `runtime_packs["ai-mps-darwin-arm64"]`.
