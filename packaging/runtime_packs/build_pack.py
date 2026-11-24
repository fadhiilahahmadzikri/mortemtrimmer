"""Reproducible platform-arch Runtime Pack builder and release-manifest.json emitter."""

from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
import zipfile

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from autosilenttrimmer.core.constants import APP_VERSION, RELEASE_MANIFEST_SCHEMA_VERSION
from autosilenttrimmer.domain.models.compute import PlatformSpec
from autosilenttrimmer.infrastructure.runtime.pack_manager import compute_sha256


def package_ffmpeg_pack(
    out_dir: str, platform_tag: str, version: str = "7.1.0"
) -> tuple[str, str, int]:
    """Bundle platform binary from imageio-ffmpeg into verifiable runtime pack archive."""
    import imageio_ffmpeg

    exe_path = imageio_ffmpeg.get_ffmpeg_exe()
    pack_id = f"ffmpeg-{platform_tag}"
    os.makedirs(out_dir, exist_ok=True)
    archive_path = os.path.join(out_dir, f"{pack_id}-{version}.zip")
    bin_name = "ffmpeg.exe" if platform_tag.startswith("windows") else "ffmpeg"

    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(exe_path, arcname=os.path.join("bin", bin_name))

    sha = compute_sha256(archive_path)
    return archive_path, sha, os.path.getsize(archive_path)


def emit_release_manifest(
    *,
    out_path: str,
    base_download_url: str,
    ffmpeg_archive: str,
    ffmpeg_sha: str,
    ffmpeg_size: int,
    platform_tag: str,
    installer_path: str | None = None,
) -> str:
    """Emit unified cross-platform release-manifest.json ready for CDN/Landing Page."""
    installer_entry: dict[str, object] = {
        "platform_tag": platform_tag,
        "status": "planned",
        "url": None,
        "sha256": "",
        "size_bytes": 0,
        "min_os_version": "Windows 10 22H2+",
    }
    if installer_path and os.path.isfile(installer_path):
        installer_entry.update(
            {
                "status": "available",
                "url": f"{base_download_url.rstrip('/')}/{os.path.basename(installer_path)}",
                "sha256": compute_sha256(installer_path),
                "size_bytes": os.path.getsize(installer_path),
            }
        )

    ffmpeg_pack_id = f"ffmpeg-{platform_tag}"
    manifest = {
        "schema_version": RELEASE_MANIFEST_SCHEMA_VERSION,
        "app_version": APP_VERSION,
        "generated_at": datetime.datetime.now(datetime.UTC).isoformat(),
        "release_notes_url": None,
        "channels": {
            "stable": {
                "installers": {
                    platform_tag: installer_entry,
                    "darwin-arm64": {
                        "platform_tag": "darwin-arm64",
                        "url": None,
                        "status": "planned",
                    },
                    "darwin-x86_64": {
                        "platform_tag": "darwin-x86_64",
                        "url": None,
                        "status": "planned",
                    },
                    "linux-x86_64": {
                        "platform_tag": "linux-x86_64",
                        "url": None,
                        "status": "planned",
                    },
                    "linux-aarch64": {
                        "platform_tag": "linux-aarch64",
                        "url": None,
                        "status": "planned",
                    },
                },
                "runtime_packs": {
                    ffmpeg_pack_id: {
                        "pack_type": "ffmpeg",
                        "platform_tag": platform_tag,
                        "version": "7.1.0",
                        "url": f"{base_download_url.rstrip('/')}/{os.path.basename(ffmpeg_archive)}",
                        "sha256": ffmpeg_sha,
                        "size_bytes": ffmpeg_size,
                        "requires_gpu": False,
                        "vendor": None,
                    }
                },
            }
        },
    }

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")
    return out_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build verifiable Runtime Packs & release manifest"
    )
    parser.add_argument("--out-dir", default=os.path.join(PROJECT_ROOT, "dist", "release"))
    parser.add_argument(
        "--base-url",
        default="https://github.com/fadhiilahahmadzikri/autosilenttrimmer/releases/latest/download",
    )
    parser.add_argument(
        "--installer", default=None, help="Optional compiled Windows installer path"
    )
    args = parser.parse_args()

    tag = PlatformSpec.current().platform_tag
    archive, sha, size = package_ffmpeg_pack(args.out_dir, tag)
    manifest = emit_release_manifest(
        out_path=os.path.join(args.out_dir, "release-manifest.json"),
        base_download_url=args.base_url,
        ffmpeg_archive=archive,
        ffmpeg_sha=sha,
        ffmpeg_size=size,
        platform_tag=tag,
        installer_path=args.installer,
    )
    print(f"Built FFmpeg Runtime Pack: {archive} ({sha})")
    print(f"Emitted Release Manifest : {manifest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
