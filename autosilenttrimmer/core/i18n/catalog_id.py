# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Fadhiilah Ahmad Zikri
"""Indonesian UI and error catalog."""

from __future__ import annotations

from types import MappingProxyType

MESSAGES_ID: MappingProxyType[str, str] = MappingProxyType(
    {
        "app.title": "Mortem Trimmer",
        "shell.menu_label": "Trim This Video",
        "tray.status_idle": "Mortem Trimmer — Siap",
        "tray.status_queued": "Dalam Antrean — {filename}",
        "tray.status_running": "Memproses ({percent:.0f}%) — {filename}",
        "tray.status_paused": "Dijeda — {filename}",
        "tray.status_completed": "Selesai: {filename} (-{reduction:.1f}%)",
        "tray.status_failed": "Gagal: {filename} ({error_code})",
        "tray.action_tune": "Pengaturan",
        "tray.action_logs": "Log Sistem",
        "tray.action_pause": "Jeda Proses Aktif",
        "tray.action_resume": "Lanjutkan Proses",
        "tray.action_cancel": "Batalkan Tugas Saat Ini",
        "tray.action_export_diag": "Ekspor Diagnostik",
        "tray.action_language": "Bahasa (EN / ID)",
        "tray.action_about": "Tentang Mortem Trimmer",
        "tray.action_github": "Repositori GitHub",
        "tray.action_quit": "Keluar",
        "popup.title": "Mortem Trimmer",
        "popup.queued": "{stage}...",
        "popup.stage": "Tahap: {stage}...",
        "popup.eta": "Estimasi sisa: {eta}",
        "popup.backend": "Mesin: {backend}",
        "popup.cancel": "Batal",
        "popup.pause": "Jeda",
        "popup.resume": "Lanjut",
        "popup.logs": "Lihat Log",
        "popup.dismiss": "Tutup",
        "popup.failed": "{code}: {message}",
        "notify.completed_title": "Pemotongan Selesai",
        "notify.completed_body": "Tersimpan {filename} ({reduction:.1f}% bagian senyap dihapus)",
        "notify.failed_title": "Pemotongan Gagal",
        "notify.action_open": "Buka File",
        "notify.action_folder": "Tampilkan di Folder",
        "notify.fallback_cpu": "GPU tidak tersedia ({reason}); melanjutkan pemrosesan di CPU.",
        "error.unsupported_format": "Format media atau codec tidak didukung oleh dekoder.",
        "error.no_compute_backend": "Tidak ada mesin GPU atau CPU yang memenuhi kebijakan aktif.",
        "error.runtime_missing": "Komponen runtime media atau AI tidak ditemukan atau rusak.",
        "error.disk_full": "Ruang penyimpanan kosong pada drive tujuan tidak mencukupi.",
        "error.source_locked": "File sumber sedang dikunci atau diubah oleh aplikasi lain.",
        "error.chunk_failed": "Pemrosesan gagal pada salah satu segmen setelah percobaan ulang.",
        "error.merge_failed": "Gagal menyambung segmen hasil menjadi file akhir.",
        "error.verify_failed": "Verifikasi hasil gagal; file asli tetap aman tidak berubah.",
        "error.cancelled_by_user": "Proses dibatalkan oleh pengguna.",
        "error.media_not_found": "File media sumber tidak ditemukan.",
        "error.manifest_invalid": "Validasi checksum atau tanda tangan digital manifest gagal.",
        "error.ipc_failed": "Gagal terhubung ke layanan latar belakang Mortem Trimmer.",
        "error.dependency_missing": "Komponen dependensi opsional yang diperlukan belum terpasang.",
        "error.internal_error": "Terjadi kesalahan internal yang tidak terduga.",
        "dialog.choose_output_title": "Di mana Anda ingin menyimpan proyek ini?",
        "dialog.disk_full_title": "Ruang Disk Rendah di {drive}",
        "dialog.disk_full_body": (
            "Drive {drive} tidak memiliki ruang penyimpanan kosong yang cukup "
            "({free_gb} tersedia, {required_gb} disarankan). "
            "Di mana Anda ingin menyimpan proyek ini?"
        ),
        "dialog.choose_folder_btn": "Pilih Folder...",
        "dialog.cancel_btn": "Batal",
    }
)
