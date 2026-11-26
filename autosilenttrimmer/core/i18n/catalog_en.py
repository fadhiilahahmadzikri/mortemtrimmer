# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Fadhiilah Ahmad Zikri
"""English UI and error catalog."""

from __future__ import annotations

from types import MappingProxyType

MESSAGES_EN: MappingProxyType[str, str] = MappingProxyType(
    {
        "app.title": "Mortem Trimmer",
        "shell.menu_label": "Trim This Video",
        "tray.status_idle": "Mortem Trimmer — Ready",
        "tray.status_queued": "Queued — {filename}",
        "tray.status_running": "Processing ({percent:.0f}%) — {filename}",
        "tray.status_paused": "Paused — {filename}",
        "tray.status_completed": "Completed: {filename} (-{reduction:.1f}%)",
        "tray.status_failed": "Failed: {filename} ({error_code})",
        "tray.action_tune": "Settings",
        "tray.action_logs": "System Logs",
        "tray.action_pause": "Pause Active Jobs",
        "tray.action_resume": "Resume Jobs",
        "tray.action_cancel": "Cancel Current Job",
        "tray.action_export_diag": "Export Diagnostics",
        "tray.action_language": "Language (EN / ID)",
        "tray.action_about": "About Mortem Trimmer",
        "tray.action_github": "GitHub Repository",
        "tray.action_quit": "Exit",
        "popup.title": "Mortem Trimmer",
        "popup.queued": "{stage}...",
        "popup.stage": "Stage: {stage}...",
        "popup.eta": "Remaining: {eta}",
        "popup.backend": "Engine: {backend}",
        "popup.cancel": "Cancel",
        "popup.pause": "Pause",
        "popup.resume": "Resume",
        "popup.logs": "View Logs",
        "popup.dismiss": "Close",
        "popup.failed": "{code}: {message}",
        "notify.completed_title": "Trim Complete",
        "notify.completed_body": "Saved {filename} ({reduction:.1f}% silence removed)",
        "notify.failed_title": "Trim Failed",
        "notify.action_open": "Open File",
        "notify.action_folder": "Show in Folder",
        "notify.fallback_cpu": "GPU encoder unavailable ({reason}); continuing on CPU.",
        "error.unsupported_format": "Media format or codec is not supported by this decoder.",
        "error.no_compute_backend": "No compatible GPU or CPU backend is available under the active policy.",
        "error.runtime_missing": "Required media or AI runtime component is missing or corrupted.",
        "error.disk_full": "Insufficient free disk space on the destination volume.",
        "error.source_locked": "Source file was modified or locked by another application.",
        "error.chunk_failed": "Processing failed on one or more media segments after retries.",
        "error.merge_failed": "Failed to join processed segments into the output container.",
        "error.verify_failed": "Output verification failed; original file left untouched.",
        "error.cancelled_by_user": "Job was cancelled by user request.",
        "error.media_not_found": "Source media file was not found.",
        "error.manifest_invalid": "Runtime manifest checksum or signature validation failed.",
        "error.ipc_failed": "Could not communicate with the Mortem Trimmer background service.",
        "error.dependency_missing": "A required optional dependency is not installed.",
        "error.internal_error": "An unexpected internal error occurred.",
        "dialog.choose_output_title": "Where would you like to save this project?",
        "dialog.disk_full_title": "Low Disk Space on {drive}",
        "dialog.disk_full_body": (
            "Drive {drive} does not have enough free disk space "
            "({free_gb} available, {required_gb} recommended). "
            "Where would you like to save this project?"
        ),
        "dialog.choose_folder_btn": "Choose Folder...",
        "dialog.cancel_btn": "Cancel",
    }
)
