"""Indonesian UI and error catalog."""

from __future__ import annotations

from types import MappingProxyType

MESSAGES_ID: MappingProxyType[str, str] = MappingProxyType(
    {
        "app.title": "Trim This Video",
        "shell.menu_label": "Trim This Video",
        "tray.status_idle": "Trim This Video - Siap",
        "tray.status_running": "Memproses ({percent:.0f}%) - {filename}",
        "tray.status_paused": "Dijeda - {filename}",
        "tray.action_tune": "Tune (Konfigurasi)",
        "tray.action_pause": "Jeda Proses Aktif",
        "tray.action_resume": "Lanjutkan Proses",
        "tray.action_cancel": "Batalkan Tugas Saat Ini",
        "tray.action_export_diag": "Ekspor Diagnostik ZIP",
        "tray.action_language": "Ganti Bahasa (EN/ID)",
        "tray.action_quit": "Keluar",
        "popup.title": "Trim This Video",
        "popup.eta": "Estimasi sisa: {eta}",
        "popup.backend": "Backend: {backend}",
        "popup.cancel": "Batal",
        "popup.pause": "Jeda",
        "popup.resume": "Lanjut",
        "notify.completed_title": "Pemotongan Selesai",
        "notify.completed_body": "Tersimpan {filename} ({reduction:.1f}% bagian senyap dihapus)",
        "notify.failed_title": "Pemotongan Gagal",
        "notify.action_open": "Buka File",
        "notify.action_folder": "Tampilkan di Folder",
        "notify.fallback_cpu": "GPU tidak tersedia ({reason}); melanjutkan pemrosesan di CPU.",
        "error.unsupported_format": "Format media atau codec tidak didukung oleh dekoder.",
        "error.no_compute_backend": "Tidak ada backend komputasi GPU/CPU yang memenuhi kebijakan aktif.",
        "error.runtime_missing": "Paket runtime media atau AI tidak ditemukan atau rusak.",
        "error.disk_full": "Ruang penyimpanan kosong pada drive tujuan tidak mencukupi.",
        "error.source_locked": "File sumber sedang dikunci atau diubah oleh aplikasi lain.",
        "error.chunk_failed": "Pemrosesan gagal pada salah satu segmen setelah percobaan ulang.",
        "error.merge_failed": "Gagal menyambung segmen hasil menjadi file akhir.",
        "error.verify_failed": "Verifikasi hasil gagal; file asli tetap aman tidak berubah.",
        "error.cancelled_by_user": "Proses dibatalkan oleh pengguna.",
        "error.media_not_found": "File media sumber tidak ditemukan.",
        "error.manifest_invalid": "Validasi checksum atau tanda tangan digital manifest gagal.",
        "error.ipc_failed": "Gagal terhubung ke layanan latar belakang Trim This Video.",
        "error.dependency_missing": "Komponen dependensi opsional yang diperlukan belum terpasang.",
        "error.internal_error": "Terjadi kesalahan internal yang tidak terduga.",
    }
)
