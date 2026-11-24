# 01 — Blueprint Produk & Arsitektur: "Trim This Video"

> **Status:** Draft v0.1 — fase validasi ide
> **Sifat dokumen:** *technology-agnostic*. Setiap komponen didefinisikan lewat **tanggung jawab, kontrak, dan batasan**, bukan lewat library atau bahasa pemrograman tertentu. Pilihan teknologi hanya muncul di §13 sebagai opsi yang tidak mengikat.
> **Pendamping:** `02_feasibility_dan_distribusi.md` (penilaian kelayakan, risiko, PoC, packaging & distribusi)

---

## 1. Ringkasan Produk

Utilitas Windows ringan: pengguna klik kanan file video di File Explorer → pilih **"Trim This Video"** → job langsung berjalan di background, diproses paralel per-chunk → saat selesai, muncul **notifikasi native Windows**. Tidak ada aplikasi utama yang kompleks; interaksi utama terjadi di dalam shell Windows.

Produk ini harus bisa didistribusikan ke pengguna umum sebagai paket profesional (installer + executable), tanpa pengguna menyentuh environment developer.

**Prinsip nilai:** *satu klik, cepat, tidak mengganggu, tidak merusak file asli.*

---

## 2. Prinsip Desain Agnostik

| # | Prinsip | Implikasi |
|---|---------|-----------|
| P1 | **Capability over technology** | Sebut "Media Engine", bukan nama tool. Tool bisa diganti tanpa mengubah desain. |
| P2 | **Ports & Adapters** | Core domain tidak tahu OS, GPU, encoder, maupun UI. Semua lewat interface (port). |
| P3 | **Engine bisa jalan headless** | Seluruh pipeline dapat dijalankan dari CLI/test tanpa shell Windows → mudah di-test & di-benchmark. |
| P4 | **Shell handler setipis mungkin** | Handler klik-kanan hanya mengirim permintaan lalu keluar. Tidak ada kerja berat di sana. |
| P5 | **Job deterministik & dapat dilanjutkan** | Setiap job punya manifest; gagal di tengah ≠ mulai dari nol. |
| P6 | **Degrade, jangan crash** | Backend ideal tidak ada → turun ke backend berikutnya dengan pemberitahuan jelas. |
| P7 | **Non-destruktif** | File asli tidak pernah ditimpa. Output = file baru. |
| P8 | **Zero manual setup untuk end user** | Semua prasyarat disiapkan installer / first-run, terverifikasi, dan dapat di-rollback. |

---

## 3. Asumsi & Definisi yang Harus Dikonfirmasi

Beberapa keputusan di bawah **menentukan arsitektur** dan perlu dikunci oleh owner sebelum MVP.

| ID | Topik | Asumsi default dokumen ini | Status |
|----|-------|----------------------------|--------|
| A1 | **Arti "Trim"** | Arsitektur mendukung *TrimStrategy* yang dapat dipasang (plug-in). Kandidat: (a) potong rentang manual, (b) auto-trim bagian senyap/kosong, (c) auto-trim berbasis analisis konten (ucapan/scene). MVP memilih **satu**. | ❓ Perlu keputusan |
| A2 | **"Hex Flow"** | Ditafsirkan sebagai: UI minimal (ikon tray / jendela kecil / overlay progres), tanpa jendela utama. | ❓ Konfirmasi |
| A3 | **Peran GPU** | "Wajib" dibaca sebagai *"target performa utama"*. Lihat §8 dan dokumen 02 §2.3. | ❓ Perlu keputusan |
| A4 | **Output** | File baru di folder yang sama: `{nama}.trimmed.{ext}`; konflik nama → penomoran otomatis. | Default |
| A5 | **Platform** | Windows 10 (22H2+) dan Windows 11, x64. ARM64 = fase lanjut. | Default |
| A6 | **Konektivitas** | Berjalan penuh offline setelah setup. Jaringan hanya untuk setup, update, dan (opsional) crash report opt-in. | Default |
| A7 | **Bahasa UI** | Indonesia + Inggris sejak awal (string diekstrak, bukan hard-coded). | Default |

---

## 4. User Journey

```
INSTALL (sekali)
  └─ Installer per-user (tanpa admin bila memungkinkan)
       └─ Registrasi context menu + identitas aplikasi (untuk notifikasi)
            └─ First-run: Capability Probe → siapkan Runtime Pack bila perlu
                 └─ Siap

PENGGUNAAN
  Klik kanan video ──► "Trim This Video"
        │
        ▼
  Shell Handler (<100 ms) ──► kirim JobRequest ──► keluar
        │
        ▼
  Job Gateway (single instance) ──► Orchestrator
        │
        ▼
  PROBE → PLAN → EXECUTE (paralel) → MERGE → VERIFY
        │
        ▼
  Notifikasi: "Selesai — video_x.trimmed.mp4"
        [Buka file]  [Tampilkan di folder]
```

**UI minimal (A2):** ikon tray + popup progres kecil (persen, ETA, tombol Batal). Tidak ada jendela utama yang wajib dibuka. Halaman *Settings* sederhana boleh ada, diakses dari tray.

---

## 5. Peta Komponen

```
┌──────────────────┐   ┌───────────────────┐
│ Shell Integration│──►│ Job Gateway       │  (single-instance + IPC)
└──────────────────┘   └─────────┬─────────┘
                                 ▼
                       ┌───────────────────┐        ┌────────────────────┐
                       │ Orchestrator      │◄──────►│ Progress/Event Bus │──► Tray UI / Notifier
                       └─────────┬─────────┘        └────────────────────┘
                 ┌───────────────┼────────────────┐
                 ▼               ▼                ▼
          ┌───────────┐   ┌─────────────┐   ┌───────────┐
          │ Planner   │   │ Worker Pool │   │ Merger +  │
          │ (strategy)│   │ (N workers) │   │ Verifier  │
          └─────┬─────┘   └──────┬──────┘   └───────────┘
                │                ▼
                │        ┌───────────────┐
                └───────►│ Media Engine  │  (port) ──► adapter(s)
                         │ Compute Backend│ (port) ──► adapter(s): GPU* / CPU
                         └───────────────┘

Pendukung: Capability Prober · Runtime Manager · Settings · Logger/Diagnostics · Updater
```

| Komponen | Tanggung jawab | Catatan agnostik |
|----------|----------------|------------------|
| **Shell Integration** | Mendaftarkan entri menu untuk ekstensi yang didukung; meneruskan path terpilih. | Mekanisme bergantung versi Windows (lihat §9). |
| **Job Gateway** | Menjamin satu instance layanan; menerima request dari banyak pemanggil; antrian job. | Wajib karena multi-select memanggil handler berkali-kali. |
| **Orchestrator** | Mengelola siklus hidup job (state machine), cancel, pause, resume. | Satu-satunya pemilik state job. |
| **Planner** | Menjalankan `TrimStrategy`, menghasilkan *ChunkPlan* dan *CutList*. | Pluggable per strategi. |
| **Worker Pool** | Menjalankan chunk secara paralel dengan batas sumber daya adaptif. | Model eksekusi (thread/proses) adalah detail implementasi. |
| **Media Engine (port)** | `probe`, `extract`, `analyze`, `encode`, `concat`. | Adapter menyembunyikan tool/library nyata. |
| **Compute Backend (port)** | Menyatakan kapabilitas & batas konkurensi per perangkat (GPU/CPU). | Vendor-agnostic. |
| **Merger + Verifier** | Menyambung hasil chunk, memeriksa durasi, sinkron A/V, dapat didekode. | Gagal verifikasi = job gagal, output tidak dipublikasikan. |
| **Notifier** | Mengirim notifikasi native + aksi; fallback bila notifikasi dimatikan. | Perlu identitas aplikasi terdaftar (§9). |
| **Capability Prober** | Mendeteksi GPU/driver/encoder/dekoder, RAM, disk. Hasil di-cache. | Dijalankan saat first-run & saat perubahan driver terdeteksi. |
| **Runtime Manager** | Mengunduh, memverifikasi (hash+signature), memasang, dan memperbarui *Runtime Pack*. | Lihat dokumen 02 §5. |
| **Updater** | Cek & terapkan pembaruan aplikasi. | Lihat dokumen 02 §5.7. |

---

## 6. Kontrak Antar Komponen (bahasa-netral)

### 6.1 JobRequest

```yaml
JobRequest:
  job_id: <uuid>
  sources: [<absolute_path>, ...]        # 1..n file
  strategy: <strategy_id>                # mis. "manual-range", "auto-silence"
  strategy_params: { ... }
  output_policy:
    location: beside-source | custom
    naming: "{name}.trimmed.{ext}"
    on_conflict: increment | overwrite | ask   # default: increment
  execution_policy:
    backend_preference: [gpu, cpu]
    max_workers: auto | <int>
    priority: background | normal
```

### 6.2 State Machine Job

```
QUEUED → PROBING → PLANNING → RUNNING → MERGING → VERIFYING → DONE
                       │          │         │          │
                       └──────────┴─────────┴──────────┴──► FAILED
 (RUNNING ↔ PAUSED)    (semua state non-final) ──► CANCELLED
```

### 6.3 Event (Event Bus)

`JobQueued` · `JobStarted` · `ChunkCompleted{index, duration_ms}` · `ProgressUpdated{percent, eta}` · `BackendFallback{from, to, reason}` · `JobCompleted{output_path, stats}` · `JobFailed{code, hint}` · `JobCancelled`

### 6.4 Taksonomi Error (stabil, untuk UI & log)

`UNSUPPORTED_FORMAT` · `NO_COMPUTE_BACKEND` · `RUNTIME_MISSING` · `DISK_FULL` · `SOURCE_LOCKED` · `CHUNK_FAILED` · `MERGE_FAILED` · `VERIFY_FAILED` · `CANCELLED_BY_USER`

Setiap error membawa **pesan manusiawi + tindakan yang disarankan**, bukan hanya kode.

### 6.5 ComputeBackend (port)

```yaml
ComputeBackend:
  id: <string>                      # mis. "gpu-vendorA", "gpu-vendorB", "cpu"
  probe() -> Capabilities           # codec yang didukung, VRAM, batas sesi, dll.
  supports(task) -> bool
  max_concurrency() -> int          # batas paralel yang aman untuk backend ini
  create_worker() -> Worker
```

---

## 7. Pipeline & Strategi Paralelisme

### 7.1 Wawasan kunci

> Paralelisme **tidak sama bernilainya di setiap tahap**. Dipasang hanya pada tahap yang *compute-bound* (analisis dan encode). Tahap yang *IO-bound* (cut tanpa re-encode) tidak diuntungkan oleh banyak thread.

Jadi Planner memilih **mode eksekusi** dulu, baru memutuskan seberapa paralel.

| Mode | Cara kerja | Kecepatan | Akurasi cut | Paralelisme berguna? |
|------|-----------|-----------|-------------|----------------------|
| **COPY** | Potong tanpa re-encode | Sangat cepat (IO-bound) | Terbatas di keyframe | Minim |
| **SMART-CUT** | Re-encode hanya segmen batas, sisanya copy | Cepat | Frame-accurate | Sedang |
| **REENCODE** | Encode ulang penuh | Lambat (compute-bound) | Frame-accurate | **Tinggi** |
| **ANALYZE** (untuk auto-trim) | Analisis audio/video per chunk → menghasilkan cut list global | Compute-bound | — | **Tinggi** |

### 7.2 Tahapan

1. **Probe** — container, codec video/audio, durasi, indeks keyframe, jumlah track audio, subtitle, rotasi, HDR, VFR/CFR.
2. **Plan** — `TrimStrategy` menghasilkan *CutList* (rentang yang dipertahankan). Planner memilih mode eksekusi (COPY / SMART-CUT / REENCODE) berdasarkan hasil probe + kebutuhan akurasi.
3. **Chunking** — bagi pekerjaan (aturan §7.3).
4. **Execute** — Worker Pool memproses chunk secara paralel.
5. **Merge** — sambung hasil secara berurutan.
6. **Verify** — periksa hasil (§7.7).
7. **Publish** — rename atomik dari file sementara ke nama output final.

### 7.3 Aturan Chunking

- **Batas chunk harus selaras dengan keyframe/GOP.** Memotong di tengah GOP merusak decode dan sinkron.
- **Ukuran target adaptif** (hipotesis awal 30–120 detik), dihitung dari: durasi total, jumlah worker, overhead startup per chunk.
- **Overlap konteks** hanya untuk fase ANALYZE (agar keputusan tidak terpotong di tengah ucapan/kejadian); hasil overlap di-deduplikasi saat menggabungkan cut list.
- **Chunk minimum**: video pendek tidak dipecah (overhead > keuntungan).
- **Jumlah chunk > jumlah worker** agar beban merata (antrian kerja, bukan pembagian statis).

### 7.4 Penentuan Jumlah Worker (adaptif)

```
N = min(
  core_logis_tersedia − cadangan_untuk_sistem,
  anggaran_memori / perkiraan_memori_per_chunk,
  ComputeBackend.max_concurrency(),
  batas_throughput_disk (bila mode IO-bound)
)
```

Catatan: pada satu GPU, menambah worker **tidak linear** — encoder hardware punya batas sesi bersamaan dan batas throughput. Nilai optimal harus **diukur** (PoC S2), bukan diasumsikan.

### 7.5 Penjadwalan & "sopan santun" sistem

- Prioritas proses rendah secara default (`priority: background`) agar PC tetap responsif.
- Opsi: jeda otomatis saat baterai rendah / mode hemat daya.
- Batasi penggunaan disk sementara; pra-cek ruang kosong (perkiraan = ukuran sumber × faktor aman).

### 7.6 Merge

- Penyambungan **lossless** bila parameter stream antar chunk identik.
- Pastikan kontinuitas timestamp dan sinkron A/V; tangani video VFR secara eksplisit.
- Jika parameter tidak identik → fallback ke re-mux/re-encode segmen bermasalah.

### 7.7 Verify

- Durasi output ≈ total CutList (toleransi yang didefinisikan).
- Sampling decode di beberapa titik (awal, tengah, akhir, tiap sambungan).
- Jumlah & jenis stream sesuai ekspektasi (audio track, subtitle yang dipertahankan sesuai kebijakan).
- Gagal → output **tidak dipublikasikan**; file sementara dibersihkan; error `VERIFY_FAILED`.

### 7.8 Toleransi Kegagalan

| Situasi | Perilaku |
|---------|----------|
| Satu chunk gagal | Retry (batas N); bila tetap gagal → fallback backend; bila masih gagal → job `FAILED` dengan indikasi chunk. |
| Backend GPU error/driver reset | Event `BackendFallback`, lanjutkan di CPU. |
| Aplikasi/PC tertutup di tengah job | Manifest menyimpan chunk selesai → *resume* pada start berikutnya (opsional di MVP, wajib di GA). |
| Cancel oleh pengguna | Hentikan worker, hapus file sementara, status `CANCELLED`. |
| Disk penuh | Berhenti bersih, pesan jelas, tidak meninggalkan file separuh jadi. |
| File sumber terkunci/diubah saat proses | Deteksi (ukuran/mtime), gagal dengan `SOURCE_LOCKED`. |

### 7.9 Progres

Progres **berbobot durasi chunk** (bukan jumlah chunk), ditambah bobot tetap untuk tahap probe/merge/verify. ETA dihaluskan (moving average) agar tidak melompat-lompat.

---

## 8. Abstraksi Compute Backend & Kebijakan GPU

Tiga kebijakan GPU yang valid; pilih salah satu (keputusan A3):

| Kebijakan | Perilaku | Kelebihan | Kekurangan |
|-----------|----------|-----------|------------|
| **G1 — Hard gate** | Tanpa GPU yang didukung, aplikasi menolak menjalankan job. | Performa konsisten, QA sederhana. | Menyingkirkan banyak pengguna; harus dikomunikasikan sebelum unduh. |
| **G2 — GPU diutamakan + fallback CPU** *(rekomendasi)* | GPU dipakai bila ada; bila tidak, CPU dengan pemberitahuan estimasi lebih lambat. | Jangkauan pengguna luas; "wajib" tercapai sebagai target performa. | Dua jalur harus diuji. |
| **G3 — CPU only** | Abaikan GPU. | Paling sederhana. | Tidak memenuhi tujuan performa produk. |

Aturan umum:
- Backend dipilih berdasarkan **daftar preferensi + hasil probe**, bukan nama vendor yang di-hard-code.
- Pendeteksian GPU **tidak boleh** berasumsi satu vendor. Tambah vendor = tambah adapter.
- Hasil probe di-cache dan dibatalkan (di-probe ulang) saat versi driver berubah atau saat ada kegagalan backend.
- Pengguna melihat **alasan** pilihan backend di log/diagnostik ("GPU tidak ditemukan → memakai CPU").

---

## 9. Integrasi OS (persyaratan, bukan implementasi)

| Area | Persyaratan |
|------|-------------|
| **Entri context menu** | Muncul hanya untuk ekstensi didukung; mendukung multi-select; handler selesai < 100 ms; tidak memblokir Explorer. |
| **Windows 11** | Menu klik-kanan klasik tersembunyi di balik "Show more options". Entri tingkat atas pada menu baru memerlukan mekanisme berbeda (komponen shell + identitas paket). Pilih sadar: **MVP boleh di menu klasik**, menu baru = peningkatan UX terjadwal. |
| **Multi-select** | Explorer dapat memanggil handler per file. Gateway harus menggabungkan ke satu antrian (single instance + IPC). |
| **Identitas aplikasi** | Notifikasi native membutuhkan identitas aplikasi yang terdaftar; harus disiapkan installer. |
| **Notifikasi** | Aksi: *Buka file*, *Tampilkan di folder*. Fallback bila notifikasi dimatikan (Focus Assist/Do Not Disturb): badge/ikon tray + riwayat job. |
| **Path** | Dukung path panjang, Unicode, spasi, drive jaringan (dengan peringatan performa). |
| **Cakupan instalasi** | Prioritaskan instalasi **per-user** (tanpa hak admin). Per-machine = opsional untuk lingkungan terkelola. |
| **Uninstall** | Menghapus entri menu, identitas aplikasi, tugas terjadwal, dan (atas pilihan) Runtime Pack & cache. Tidak boleh ada sisa entri yatim. |

---

## 10. Persyaratan Non-Fungsional

> Angka berikut adalah **hipotesis target awal**, divalidasi/diubah di PoC (dokumen 02 §4).

| Kategori | Target |
|----------|--------|
| **Latensi klik → job mulai** | < 1 detik (tanpa cold-start berat) |
| **Speedup** (mode REENCODE/ANALYZE vs baseline satu worker) | ≥ 2× pada mesin 8 core; GPU lebih tinggi — **diukur**, bukan dijanjikan |
| **Mode COPY** | Mendekati kecepatan baca/tulis disk |
| **Kesopanan sistem** | UI desktop tetap responsif selama job (prioritas rendah) |
| **Ketahanan** | Tidak ada output korup; output hanya muncul setelah verifikasi lolos |
| **Keamanan** | Tanpa hak admin saat runtime; semua unduhan diverifikasi hash + tanda tangan; tanpa eksekusi kode dari sumber tak tepercaya |
| **Privasi** | Tidak ada video/metadata yang meninggalkan perangkat; telemetri **opt-in**, anonim |
| **Diagnostik** | Log lokal terstruktur + tombol "Export diagnostics" untuk dukungan |
| **Aksesibilitas & i18n** | Teks notifikasi/UI dapat dilokalkan; kontras & keyboard dasar |

---

## 11. Format yang Didukung

Dukungan ditentukan oleh **hasil probe**, bukan hanya ekstensi.

| Tingkat | Kontainer (ekstensi) | Catatan |
|---------|----------------------|---------|
| **Tier 1 (MVP)** | MP4, MKV, MOV, WEBM | Paling umum; fokus pengujian. |
| **Tier 2** | M4V, TS/MTS/M2TS, AVI | Perilaku keyframe/timestamp lebih beragam. |
| **Tier 3 (nanti)** | FLV, WMV, 3GP, dll. | Sesuai permintaan nyata pengguna. |

Kriteria "didukung": kontainer dapat di-seek, codec video/audio dapat didekode oleh Media Engine, dan (untuk mode COPY) codec cocok dengan kontainer output.

---

## 12. Modul & Batas Kode (netral repo/bahasa)

```
/core            Domain murni: Job, State Machine, Planner, kontrak (tanpa IO)
/strategies      Implementasi TrimStrategy (manual-range, auto-silence, ...)
/adapters
   /shell        Integrasi context menu
   /ipc          Gateway & kanal komunikasi antar proses
   /media        Adapter Media Engine
   /compute      Adapter backend (gpu-*, cpu) + Capability Prober
   /notify       Notifikasi native + fallback
   /storage      Manifest job, settings, cache
/app             Composition root (merangkai semua), tray UI minimal
/runtime         Runtime Manager (unduh/verifikasi/pasang Runtime Pack)
/packaging       Skrip installer, signing, manifest rilis
/tests
   /fixtures     Media golden (CFR/VFR, B-frame, multi-audio, rotasi, HDR, korup)
   /perf         Harness benchmark
```

Aturan ketergantungan: `core` tidak boleh mengimpor apa pun dari `adapters`. `adapters` bergantung pada `core`, tidak sebaliknya.

---

## 13. Peta Pilihan Teknologi (tidak mengikat)

| Kapabilitas | Opsi A | Opsi B | Opsi C | Pertimbangan |
|-------------|--------|--------|--------|--------------|
| **Bahasa inti** | Python | Rust | C# / .NET | Python cepat dibangun tetapi packaging runtime lebih berat; Rust/.NET menghasilkan binary lebih ramping & integrasi Windows lebih natural. |
| **Media Engine** | CLI tool eksternal yang di-bundle | Library native via binding | Framework media OS | CLI = isolasi proses & mudah diganti; library = overhead lebih kecil. |
| **Entri shell** | Registri (menu klasik) | Komponen shell + paket (menu Win11 baru) | Keduanya | Mulai dari A, tambahkan B kemudian. |
| **IPC** | Named pipe | Local socket | RPC lokal | Satu instance + antrian. |
| **Notifikasi** | API toast native | Library pembungkus | — | Wajib identitas aplikasi. |
| **Analisis konten (auto-trim)** | Heuristik sinyal (energi audio, deteksi scene) | Model ML ringan | Model ML berat (butuh GPU) | Menentukan seberapa "wajib" GPU benar-benar dibutuhkan (A1, A3). |
| **Installer** | Installer script klasik | Paket MSIX | MSI | Lihat dokumen 02 §5. |

---

## 14. Strategi Pengujian

| Jenis | Isi |
|-------|-----|
| **Golden media** | Kumpulan video uji: CFR/VFR, B-frame, banyak track audio, rotasi metadata, HDR, durasi ekstrem, file korup/terpotong. |
| **Properti invarian** | Durasi output = durasi CutList (± toleransi); A/V sinkron; jumlah stream sesuai; output dapat didekode penuh. |
| **Chaos test** | Matikan worker secara acak, cabut disk sementara, simulasikan GPU reset → job harus pulih/gagal bersih. |
| **Benchmark** | Harness perf: speedup vs jumlah worker, mode COPY vs SMART-CUT vs REENCODE, CPU vs GPU. |
| **Kompatibilitas OS** | Windows 10 22H2, Windows 11 (bersih), akun non-admin, path Unicode/panjang. |
| **Instalasi** | VM bersih: install → pakai → update → uninstall; verifikasi tidak ada sisa. |

---

## 15. Definition of Done — MVP

- [ ] Klik kanan pada file Tier 1 menampilkan "Trim This Video" (menu klasik Win 10/11).
- [ ] Job berjalan di background; klik berulang/multi-select masuk antrian tanpa konflik.
- [ ] Satu `TrimStrategy` bekerja end-to-end dengan hasil terverifikasi.
- [ ] Pemrosesan paralel terbukti memberi speedup terukur pada mode yang compute-bound.
- [ ] Kebijakan GPU (G1/G2/G3) terimplementasi dan pesan fallback jelas.
- [ ] Notifikasi native muncul dengan aksi *Buka file* / *Tampilkan di folder*.
- [ ] File asli tidak pernah berubah; output tidak pernah korup (lolos Verify).
- [ ] Installer per-user menginstal dan menghapus bersih di VM Windows bersih.
