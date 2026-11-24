# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Fadhiilah Ahmad Zikri
"""Resumable HTTP manifest fetcher and pack downloader powered by httpx."""

from __future__ import annotations

import json
import os
from typing import Any

import httpx
from autosilenttrimmer.core.constants import (
    DEFAULT_RELEASE_CHANNEL,
    RUNTIME_DOWNLOAD_CHUNK_BYTES,
    RUNTIME_DOWNLOAD_TIMEOUT_SEC,
)
from autosilenttrimmer.core.exceptions import ErrorCode, RuntimePackException
from autosilenttrimmer.domain.contracts.event_bus import IEventBus
from autosilenttrimmer.domain.models.events import RuntimeDownloadProgress
from autosilenttrimmer.domain.models.runtime_pack import (
    InstallerArtifact,
    ReleaseManifest,
    RuntimePackArtifact,
)


class HttpManifestClient:
    """Downloads release manifests and runtime archives with HTTP Range resume support."""

    def __init__(self, event_bus: IEventBus | None = None) -> None:
        self._event_bus = event_bus

    def fetch_raw_manifest(self, manifest_url: str) -> dict[str, Any]:
        """Fetch raw JSON manifest document (supports http(s):// or file:// local testing)."""
        if manifest_url.startswith("file://"):
            local_path = manifest_url[7:]
            with open(local_path, encoding="utf-8") as f:
                return json.load(f)
        if os.path.isfile(manifest_url):
            with open(manifest_url, encoding="utf-8") as f:
                return json.load(f)

        try:
            with httpx.Client(
                timeout=RUNTIME_DOWNLOAD_TIMEOUT_SEC, follow_redirects=True
            ) as client:
                resp = client.get(manifest_url)
                resp.raise_for_status()
                return resp.json()
        except Exception as exc:
            raise RuntimePackException(
                f"Failed to fetch release manifest from '{manifest_url}': {exc}",
                code=ErrorCode.RUNTIME_MISSING,
            ) from exc

    @staticmethod
    def parse_manifest(
        raw: dict[str, Any], channel: str = DEFAULT_RELEASE_CHANNEL
    ) -> ReleaseManifest:
        """Map raw JSON catalog into strongly typed ReleaseManifest."""
        channels = raw.get("channels", {})
        if channel not in channels:
            raise RuntimePackException(
                f"Release channel '{channel}' not found in manifest.",
                code=ErrorCode.MANIFEST_INVALID,
            )

        ch_data = channels[channel]
        installers: dict[str, InstallerArtifact] = {}
        for tag, meta in ch_data.get("installers", {}).items():
            installers[tag] = InstallerArtifact(
                platform_tag=tag,
                url=meta.get("url"),
                sha256=meta.get("sha256", ""),
                signature_ed25519=meta.get("sig_ed25519", ""),
                size_bytes=int(meta.get("size_bytes", 0)),
                status=str(meta.get("status", "planned")),
                min_os_version=str(meta.get("min_os_version", "")),
            )

        packs: dict[str, RuntimePackArtifact] = {}
        for pack_id, meta in ch_data.get("runtime_packs", {}).items():
            packs[pack_id] = RuntimePackArtifact(
                pack_id=pack_id,
                pack_type=str(meta.get("pack_type", "")),
                platform_tag=str(meta.get("platform_tag", "")),
                version=str(meta.get("version", "0.0.0")),
                url=str(meta.get("url", "")),
                sha256=str(meta.get("sha256", "")),
                signature_ed25519=str(meta.get("sig_ed25519", "")),
                size_bytes=int(meta.get("size_bytes", 0)),
                requires_gpu=bool(meta.get("requires_gpu", False)),
                vendor=meta.get("vendor"),
            )

        return ReleaseManifest(
            schema_version=str(raw.get("schema_version", "1.0")),
            app_version=str(raw.get("app_version", "1.0.0")),
            channel=channel,
            installers=installers,
            runtime_packs=packs,
            release_notes_url=raw.get("release_notes_url"),
        )

    def download_resumable(
        self, pack_id: str, url: str, dest_path: str, expected_total_bytes: int = 0
    ) -> str:
        """Download archive to <dest_path>.part using HTTP Range resume when interrupted."""
        part_path = f"{dest_path}.part"
        os.makedirs(os.path.dirname(os.path.abspath(dest_path)), exist_ok=True)
        existing_bytes = os.path.getsize(part_path) if os.path.isfile(part_path) else 0

        headers: dict[str, str] = {}
        if existing_bytes > 0:
            headers["Range"] = f"bytes={existing_bytes}-"

        try:
            with (
                httpx.Client(timeout=RUNTIME_DOWNLOAD_TIMEOUT_SEC, follow_redirects=True) as client,
                client.stream("GET", url, headers=headers) as resp,
            ):
                if resp.status_code == 416 and expected_total_bytes == existing_bytes:
                    os.replace(part_path, dest_path)
                    return dest_path

                if resp.status_code == 200 and existing_bytes > 0:
                    # Server ignored Range header; restart clean write
                    existing_bytes = 0
                    mode = "wb"
                elif resp.status_code == 206:
                    mode = "ab"
                else:
                    resp.raise_for_status()
                    mode = "wb"

                content_len = int(resp.headers.get("Content-Length") or 0)
                total = (
                    existing_bytes + content_len
                    if content_len > 0
                    else max(expected_total_bytes, existing_bytes)
                )

                downloaded = existing_bytes
                with open(part_path, mode) as out_f:
                    for chunk in resp.iter_bytes(chunk_size=RUNTIME_DOWNLOAD_CHUNK_BYTES):
                        if not chunk:
                            continue
                        out_f.write(chunk)
                        downloaded += len(chunk)
                        if self._event_bus is not None:
                            self._event_bus.publish(
                                RuntimeDownloadProgress(
                                    pack_id=pack_id,
                                    downloaded_bytes=downloaded,
                                    total_bytes=total,
                                )
                            )
        except Exception as exc:
            raise RuntimePackException(
                f"Download interrupted for '{pack_id}': {exc}",
                code=ErrorCode.RUNTIME_MISSING,
            ) from exc

        os.replace(part_path, dest_path)
        return dest_path
