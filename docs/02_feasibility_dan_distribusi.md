# 02 — Validasi Kelayakan, Risiko & Blueprint Distribusi: "Trim This Video"

> **Status:** Draft v0.1 — fase validasi ide
> **Sifat dokumen:** *technology-agnostic* — menjelaskan **apa yang harus benar**, bukan tool mana yang dipakai. Bila Python dipilih sebagai bahasa implementasi, bagian yang spesifik ditandai jelas (§5.4).
> **Pendamping:** `01_blueprint_produk_arsitektur.md`

---

## 1. Verdict Ringkas

**Kesimpulan: secara teknis FEASIBLE.** Tidak ada persyaratan yang mustahil. Namun ada **tiga hal yang perlu dikoreksi/diputuskan** sebelum membangun, karena mengubah arsitektur dan pengalaman pengguna:

1. **Definisi "Trim"** menentukan apakah paralelisme & GPU relevan sama sekali.
2. **"GPU wajib" bertentangan dengan "tidak semua orang punya GPU"** — perlu kebijakan yang tegas.
3. **Analogi IDM benar sebagian** — memecah video tidak sebebas memecah file unduhan.

| # | Persyaratan | Verdict | Ringkasan |
|---|-------------|---------|-----------|
| R1 | Entri klik kanan "Trim This Video" di File Explorer | ⚠️ Feasible dengan syarat | Mudah di menu klasik; di Windows 11 menu baru butuh mekanisme berbeda (§2.4). |
| R2 | Langsung berjalan sebagai background job | ✅ Feasible | Pola standar: handler tipis + layanan single-instance. |
| R3 | Paralel per-chunk ala IDM | ⚠️ Feasible dengan syarat | Valid untuk tahap compute-bound; tidak untuk semua mode (§2.2). |
| R4 | Notifikasi native Windows | ⚠️ Feasible dengan syarat | Wajib identitas aplikasi terdaftar (§2.6). |
| R5 | Binary standalone, tanpa setup Python manual | ✅ Feasible | Umum dilakukan; ukuran & false-positive antivirus perlu dikelola. |
| R6 | GPU "wajib" | ❓ Perlu keputusan | Kontradiksi dengan realita pengguna (§2.3). |
| R7 | Venv & dependensi diunduh saat setup | ⚠️ Feasible, ada pendekatan lebih baik | Gunakan *Runtime Pack* terkelola, bukan venv mentah (§5.2). |
| R8 | Distribusi profesional untuk orang lain | ✅ Feasible | Butuh code signing, installer, update, kepatuhan lisensi (§5). |

---

## 2. Analisis Kritis Poin Berisiko

### 2.1 "Trim" bukan satu hal

Kata "trim" bisa berarti tiga pekerjaan yang sangat berbeda:

| Interpretasi | Pekerjaan nyata | Perlu GPU? | Perlu paralelisme? |
|--------------|-----------------|-----------|--------------------|
| **(a) Potong rentang manual** (mulai–akhir) | Cut di keyframe tanpa re-encode | Tidak | Hampir tidak (IO-bound, bisa selesai dalam detik) |
| **(b) Auto-trim bagian senyap/kosong** | Analisis sinyal + potong | Tidak wajib | Ya, pada fase analisis |
| **(c) Auto-trim berbasis konten (ML)** | Analisis model + potong/encode ulang | Ya, bermanfaat | Ya |

Konsekuensi: kebutuhan **GPU wajib**, **venv + dependensi berat**, dan **chunk paralel** hanya masuk akal untuk (b)/(c), atau untuk (a) dengan re-encode. Untuk (a) tanpa re-encode, arsitektur yang dibayangkan **terlalu berat** — hasil bisa lebih cepat dengan satu proses sederhana.

> **Keputusan yang dibutuhkan (A1):** interpretasi mana yang menjadi MVP? Dari persyaratan GPU + dependensi yang diunduh, dugaan kuat: (b) atau (c). Dokumen 01 sudah menyiapkan `TrimStrategy` yang dapat dipasang agar pilihan ini tidak mengunci arsitektur.

### 2.2 Analogi IDM: apa yang sama, apa yang beda

| Aspek | Download manager (IDM) | Pemrosesan video |
|-------|------------------------|------------------|
| Pembagian pekerjaan | Rentang byte — independen total | Harus selaras **keyframe/GOP**; potong di tengah GOP = rusak |
| Gabung hasil | Sambung byte | Perlu menyambung stream, menjaga timestamp & sinkron A/V |
| Hambatan utama | Jaringan (bandwidth) | CPU/GPU, **disk IO**, batas sesi encoder hardware |
| Skala dengan jumlah thread | Cenderung naik sampai jenuh bandwidth | Naik sampai batas core/encoder/disk, lalu **datar atau turun** |
| Risiko tambahan | — | Banyak worker × memori per chunk → kehabisan RAM/VRAM |

**Kesimpulan:** konsep "pecah → proses bersamaan → sambung" **valid dan standar** di industri (mis. encoding terdistribusi per-segmen), selama pemecahan mengikuti aturan keyframe, jumlah worker **diukur** (bukan "makin banyak makin cepat"), dan mode tanpa re-encode tidak dipaksa paralel.

### 2.3 Kontradiksi "GPU wajib" vs "tidak semua orang punya GPU"

Dua pernyataan ini tidak bisa keduanya benar sebagai aturan produk. Tiga jalan keluar (detail di dokumen 01 §8):

| Opsi | Dampak produk | Rekomendasi |
|------|---------------|-------------|
| **G1 Hard gate** | Aplikasi menolak berjalan tanpa GPU yang didukung. | Hanya bila fitur inti benar-benar tidak mungkin tanpa GPU. Harus diumumkan **sebelum** pengguna mengunduh. |
| **G2 GPU diutamakan + fallback CPU** | GPU = jalur cepat; CPU = jalur tetap berfungsi, lebih lambat. | ✅ **Direkomendasikan** — memenuhi "GPU sebagai target performa" tanpa menyingkirkan pengguna. |
| **G3 CPU only** | Abaikan GPU. | Tidak memenuhi tujuan performa. |

Catatan tambahan bila GPU tetap dipakai:
- Beragam vendor/generasi/driver → **capability probe** wajib, bukan asumsi.
- Kegagalan driver/reset GPU di tengah job harus ditangani (fallback ke CPU, §7.8 dokumen 01).
- Persyaratan perangkat (minimum GPU/driver) harus tertulis di halaman unduhan.

### 2.4 Menu klik kanan di Windows 11

- Mekanisme berbasis entri registri menampilkan item di menu klasik, yang di Windows 11 berada di balik **"Show more options"**. Berfungsi, tetapi UX-nya satu klik lebih jauh.
- Untuk tampil di menu klik kanan **tingkat atas** Windows 11, dibutuhkan komponen shell tersendiri dan identitas paket aplikasi. Ini lebih rumit (build, signing, packaging), tetapi bisa dikerjakan.
- **Rekomendasi:** MVP di menu klasik (valid untuk Windows 10 & 11); entri menu Win11 baru dijadwalkan sebagai peningkatan UX setelah inti terbukti.

### 2.5 Multi-select dan "banjir" proses

Saat pengguna memilih beberapa file lalu klik "Trim This Video", Explorer dapat memanggil handler berkali-kali (satu per file, dengan batas jumlah seleksi). Tanpa koordinasi, ini memunculkan puluhan instance yang berebut GPU/CPU. **Solusi desain:** *Job Gateway* single-instance + IPC + antrian (sudah ada di dokumen 01).

### 2.6 Notifikasi native membutuhkan identitas aplikasi

Notifikasi toast Windows terhubung ke identitas aplikasi yang terdaftar. Untuk aplikasi desktop non-paket, identitas ini biasanya disiapkan lewat shortcut Start Menu dengan properti identitas yang benar. Jika terlewat: notifikasi **tidak muncul** atau tampil tanpa nama/ikon yang benar. Ini harus menjadi tugas **installer**, bukan baru dipikirkan belakangan. Pertimbangkan juga kondisi Focus Assist/Do Not Disturb → fallback ke tray.

### 2.7 Ukuran dan kerumitan paket GPU

Jika analisis/ML berbasis framework GPU: komponen runtime-nya bisa **berukuran gigabyte**, bergantung versi driver/komponen GPU, dan beragam antar vendor. Konsekuensi:
- Menggabungkan semuanya ke satu installer menghasilkan unduhan sangat besar.
- Varian per vendor/komputasi mungkin diperlukan.
- Jalur CPU-only menjadi **paket yang jauh lebih kecil** → mendukung opsi G2.

### 2.8 Kepercayaan: antivirus & SmartScreen

- Executable hasil pembungkus Python/skrip yang tidak ditandatangani sering memicu **false positive** antivirus dan peringatan SmartScreen. Bentuk "satu file self-extracting" cenderung lebih sering terkena dibanding bentuk folder terpasang.
- Aplikasi yang membuat entri shell, mengunduh runtime, dan berjalan di background adalah **pola yang mirip malware** bagi heuristik antivirus → penandatanganan kode dan reputasi menjadi kebutuhan, bukan kosmetik.

### 2.9 Lisensi & kepatuhan

- Engine media dan codec memiliki lisensi dan pertimbangan paten berbeda antar build (mis. varian lisensi longgar vs varian yang lebih mengikat). Ini mempengaruhi **cara** produk boleh didistribusikan.
- Model analisis (bila ada) punya lisensi sendiri (komersial/non-komersial).
- Perlu: pemberitahuan pihak ketiga (*third-party notices*), kebijakan privasi, EULA. Konsultasikan ke ahli hukum sebelum rilis komersial *(dokumen ini bukan nasihat hukum)*.

---

## 3. Register Risiko

| ID | Risiko | Kemungkinan | Dampak | Mitigasi | Validasi |
|----|--------|-------------|--------|----------|----------|
| K1 | Definisi "Trim" tidak jelas → salah arsitektur | Tinggi | Tinggi | Kunci A1; `TrimStrategy` plug-in | Keputusan owner |
| K2 | Paralelisme tidak memberi speedup (IO/encoder-bound) | Sedang | Sedang | Pilih mode eksekusi dulu; ukur jumlah worker optimal | S2 |
| K3 | Cut/merge merusak sinkron A/V atau timestamp | Sedang | Tinggi | Batas chunk di keyframe; Verify; golden media | S2 |
| K4 | GPU tidak tersedia/terdeteksi salah di mesin pengguna | Tinggi | Tinggi | Capability probe; fallback G2; persyaratan jelas | S3 |
| K5 | Runtime Pack gagal diunduh/rusak/ter-blok jaringan | Sedang | Tinggi | Hash+signature, resume unduhan, installer offline | S6 |
| K6 | Notifikasi tidak muncul (identitas, Focus Assist) | Sedang | Sedang | Installer menyiapkan identitas; fallback tray | S4 |
| K7 | Entri menu tidak tampil/membingungkan di Win 11 | Tinggi | Sedang | MVP menu klasik; roadmap menu baru | S1 |
| K8 | Antivirus/SmartScreen menandai installer | Tinggi | Tinggi | Code signing, bentuk folder terpasang, kirim sampel ke vendor AV | S7 |
| K9 | Ukuran unduhan terlalu besar | Sedang | Sedang | Core ramping + Runtime Pack on-demand; varian CPU | S6 |
| K10 | Masalah lisensi engine/model/codec | Sedang | Tinggi | Audit lisensi sejak awal; pilih build sesuai model distribusi | Review legal |
| K11 | Output korup bila proses terhenti | Rendah | Tinggi | File sementara + rename atomik setelah Verify | S2 |
| K12 | Update merusak instalasi pengguna | Rendah | Tinggi | Update bertanda tangan, staged rollout, rollback | S7 |

---

## 4. Rencana Validasi (PoC / Spike)

Tujuan: **membuktikan hal berisiko tinggi dengan usaha minimum** sebelum membangun produk. Setiap spike punya kriteria lulus/gagal yang jelas.

| Spike | Pertanyaan yang dijawab | Kriteria LULUS | Perkiraan waktu |
|-------|-------------------------|----------------|-----------------|
| **S1 — Shell** | Apakah entri klik kanan tampil, mendukung multi-select, dan tidak memblokir Explorer? | Entri muncul di Win 10 & 11 (menu klasik); handler < 100 ms; 10 file terpilih → 1 antrian | 1–2 hari |
| **S2 — Chunk & Merge** | Apakah chunk paralel + merge benar dan lebih cepat? | Output lolos Verify pada golden media; speedup terukur vs 1 worker; kurva speedup vs jumlah worker didokumentasikan | 3–5 hari |
| **S3 — Capability Probe** | Apakah deteksi GPU/CPU akurat dan fallback mulus? | Benar di ≥ 3 konfigurasi (GPU A, GPU B, tanpa GPU); fallback otomatis saat GPU dipaksa gagal | 2–3 hari |
| **S4 — Notifikasi** | Apakah notifikasi native muncul dengan nama/ikon/aksi benar? | Muncul di mesin bersih; aksi "Buka file" berfungsi; fallback tray saat DND | 1 hari |
| **S5 — Freeze/Package** | Apakah aplikasi berjalan di Windows bersih tanpa runtime yang terpasang? | Berjalan di VM bersih (tanpa dev tools); waktu start dan ukuran tercatat | 2–3 hari |
| **S6 — Runtime Pack** | Apakah unduh-verifikasi-pasang-pakai-uninstall bekerja andal? | Sukses di jaringan lambat/terputus (resume); hash salah → ditolak; uninstall bersih | 3–4 hari |
| **S7 — Signed Installer** | Apakah installer bertanda tangan lolos, dan update/rollback aman? | Install/update/uninstall bersih di VM; peringatan SmartScreen/AV tercatat; rollback berfungsi | 3–4 hari |

**Urutan yang disarankan:** S2 → S3 → S1 → S4 → S5 → S6 → S7 (risiko teknis inti dulu, baru risiko distribusi). Satu minggu pertama cukup untuk S1–S4.

---

## 5. Blueprint Distribusi

### 5.1 Artefak Rilis

| Artefak | Isi | Catatan |
|---------|-----|---------|
| **Installer utama** | Aplikasi inti + registrasi shell + identitas aplikasi + (opsional) pengunduh Runtime Pack | Ditandatangani; per-user, tanpa admin bila memungkinkan |
| **Installer offline** | Inti + Runtime Pack tertanam | Untuk jaringan terbatas/korporat; besar |
| **Runtime Pack** | Komponen berat (engine media, runtime analisis, komponen GPU) | Versi, hash, dan tanda tangan di manifest; varian CPU vs GPU |
| **Manifest rilis** | Daftar versi, URL, hash, ukuran, persyaratan minimum | Ditandatangani; dipakai Updater & Runtime Manager |
| **Catatan rilis & notices** | Changelog, lisensi pihak ketiga | Wajib untuk kepatuhan lisensi |

### 5.2 Strategi Runtime: tiga pendekatan

| Pendekatan | Cara kerja | Kelebihan | Kekurangan |
|------------|-----------|-----------|------------|
| **A. Bundle semua** | Semua ada di installer | Sederhana; bisa offline; satu artefak | Unduhan sangat besar; satu varian GPU saja; update berat |
| **B. Core ramping + Runtime Pack on-demand** ✅ | Installer kecil; first-run mengunduh pack sesuai hasil probe | Unduhan awal kecil; varian sesuai perangkat; update parsial | Perlu Runtime Manager, verifikasi, penanganan jaringan |
| **C. Bergantung pada sistem** | Mengandalkan komponen yang sudah ada di PC pengguna | Paling ringan | Tidak dapat diandalkan; sumber dukungan terbesar → **hindari** |

**Rekomendasi: B**, dengan **installer offline** sebagai jalur cadangan.

> **Tentang "venv diunduh saat setup":** tujuannya (pengguna tidak menyiapkan environment) tepat, tetapi **venv mentah di mesin pengguna** rapuh — terikat path, mudah rusak oleh aplikasi lain, sulit diverifikasi dan di-rollback. Pendekatan setara yang lebih kuat adalah **Runtime Pack terkelola**: terisolasi, versi terkunci (lockfile), diverifikasi hash+tanda tangan, dipasang di lokasi milik aplikasi, dapat diganti atomik dan dihapus bersih.

### 5.3 Alur First-Run Setup

```
1. Cek persyaratan minimum (OS, arsitektur, ruang disk)
2. Capability Probe  → GPU? vendor/driver? encoder yang tersedia?
3. Tentukan varian Runtime Pack (GPU-x / CPU) sesuai kebijakan G1/G2/G3
4. Tampilkan ke pengguna: apa yang akan diunduh, ukurannya, ruang yang dipakai
5. Unduh (resumable) → verifikasi hash + tanda tangan
6. Pasang ke lokasi terisolasi (direktori sementara → rename atomik)
7. Smoke test: jalankan job kecil bawaan untuk memverifikasi seluruh rantai
8. Tandai sukses; jika gagal di langkah mana pun → rollback + pesan + opsi coba lagi / installer offline
```

Prinsip: setiap langkah **idempoten**, dapat diulang, dan gagal dengan pesan yang bisa ditindaklanjuti.

### 5.4 Jika Python Dipilih (spesifik implementasi)

Bagian ini hanya berlaku bila bahasa implementasi adalah Python; seluruh bagian lain tetap agnostik.

| Topik | Panduan |
|-------|---------|
| **Bentuk freeze** | Utamakan **folder terpasang (one-dir)** daripada satu file self-extracting: start lebih cepat, lebih sedikit false-positive antivirus, update parsial lebih mudah. |
| **Alternatif** | Runtime tertanam milik aplikasi (embedded) + kode aplikasi; atau kompilasi ke native untuk performa/obfuskasi sedang. Pilih lewat spike S5 dengan metrik: ukuran, waktu start, tingkat false-positive. |
| **Dependensi** | Kunci versi (lockfile) dengan hash; build reproducible di CI; tidak ada instalasi dependensi di mesin pengguna saat runtime. |
| **Komponen berat** | Pisahkan komponen GPU/ML ke Runtime Pack (§5.2-B), bukan ke inti. |
| **Proses pekerja** | Pertimbangkan proses terpisah (bukan hanya thread) untuk isolasi crash dan menghindari batasan eksekusi bersamaan pada interpreter; jalankan engine media sebagai proses anak. |
| **Dev vs prod** | Environment developer tidak pernah menjadi bagian dari artefak rilis. |

Pertimbangkan juga: bila performa start, ukuran, atau integrasi Windows menjadi masalah di S5, **ganti bahasa/runtime inti** tanpa mengubah blueprint (berkat §2 P1/P2 di dokumen 01).

### 5.5 Instalasi & Uninstalasi

- Instalasi **per-user** default (tanpa hak admin); per-machine opsional untuk lingkungan terkelola.
- Installer: mendaftarkan entri shell, identitas notifikasi, lokasi data (`settings`, `cache`, `logs`), dan entri Add/Remove Programs.
- **Uninstall bersih**: hapus entri shell, identitas aplikasi, tugas terjadwal; tanya pengguna apakah Runtime Pack/cache ikut dihapus; **tidak boleh ada entri yatim** di menu klik kanan.
- Upgrade in-place mempertahankan settings; Runtime Pack lama dibersihkan setelah yang baru terverifikasi.

### 5.6 Code Signing & Kepercayaan

| Item | Praktik |
|------|---------|
| **Tanda tangan** | Tandatangani **semua** biner yang dieksekusi (aplikasi, installer, helper, isi Runtime Pack yang berupa executable) dengan cap waktu (timestamp). |
| **Kunci** | Simpan kunci di HSM/layanan signing berbasis cloud; jangan di mesin developer atau repo. |
| **Reputasi SmartScreen** | Dibangun seiring waktu & volume unduhan yang konsisten dari identitas penandatangan yang sama; sertifikat tertentu tidak otomatis menghilangkan peringatan awal — rencanakan masa "pemanasan". |
| **False positive AV** | Kirim sampel rilis ke vendor AV utama sebelum rilis publik; hindari pola mencurigakan (mis. mengunduh dan mengeksekusi tanpa verifikasi). |
| **Transparansi** | Dokumentasikan apa yang diunduh, dari mana, dan kenapa (halaman "Privasi & Jaringan"). |

### 5.7 Pembaruan (Update)

- **Versi:** *semantic versioning*; Runtime Pack berversi independen dari inti, dengan matriks kompatibilitas di manifest.
- **Kanal:** `stable` dan `beta` (opt-in).
- **Mekanisme:** cek manifest bertanda tangan → unduh → verifikasi → terapkan saat aplikasi idle → rollback otomatis bila smoke test gagal.
- **Delta/parsial:** perbarui hanya bagian yang berubah (terutama Runtime Pack besar).
- **Tidak memotong job yang sedang berjalan**; update menunggu antrian kosong.
- **Staged rollout:** lepas ke sebagian kecil pengguna dulu, pantau, lalu perluas.

### 5.8 Pipeline CI/CD

```
Commit → Lint & test unit → Test properti/golden media
      → Build reproducible (lockfile ter-hash)
      → Bangun Runtime Pack (varian CPU / GPU)
      → Sign semua biner → Bangun installer → Sign installer
      → Smoke test di VM Windows bersih (install → trim → notifikasi → uninstall)
      → Pindai (AV/malware) & audit lisensi + SBOM
      → Publikasikan manifest bertanda tangan + artefak ke saluran distribusi
```

Gerbang kualitas: rilis diblokir bila smoke test VM bersih, audit lisensi, atau verifikasi tanda tangan gagal.

### 5.9 Kanal Distribusi

| Kanal | Kelebihan | Catatan |
|-------|-----------|---------|
| **Situs resmi / rilis repositori** | Kontrol penuh; mudah dimulai | Tanggung jawab update, hosting, dan kepercayaan ada pada Anda |
| **Package manager Windows (mis. winget)** | Mudah dipasang & diperbarui; kredibel | Butuh URL installer stabil + hash; dukungan switch instalasi senyap |
| **Microsoft Store (paket MSIX)** | Kepercayaan bawaan, update otomatis, instal/uninstall bersih | Batasan sandbox/paket; integrasi shell & unduhan runtime perlu dikaji; proses review |
| **Installer korporat (MSI/script)** | Untuk lingkungan terkelola | Instalasi per-machine, tanpa interaksi |

Urutan yang disarankan: situs resmi → package manager → (opsional) Store.

### 5.10 Telemetri, Crash Report, Dukungan

- Telemetri & crash report **opt-in**, anonim, tanpa konten/nama file video.
- *Export diagnostics*: satu tombol yang menghimpun log terstruktur + hasil capability probe + versi komponen (tanpa data pribadi).
- Pesan error memakai taksonomi stabil (dokumen 01 §6.4) agar dukungan bisa langsung memetakan masalah.

---

## 6. Peta Jalan

| Fase | Tujuan | Keluaran |
|------|--------|----------|
| **0 — Validasi** *(sekarang)* | Menjawab keputusan A1–A3; menjalankan S1–S4 | Keputusan terkunci; bukti kelayakan inti |
| **1 — MVP internal** | Satu `TrimStrategy` end-to-end; kebijakan GPU; installer bertanda tangan untuk uji internal | Aplikasi berjalan di VM bersih; Definition of Done dokumen 01 §15 |
| **2 — Beta tertutup** | Runtime Pack, updater, telemetri opt-in, hardening | Uji di beragam mesin/GPU; metrik keandalan |
| **3 — Rilis publik (GA)** | Kanal distribusi, dokumentasi, dukungan, kepatuhan lisensi | Rilis stabil; proses update & rollback teruji |
| **4 — Peningkatan** | Menu Win 11 tingkat atas, strategi trim tambahan, ARM64, resume job | Sesuai umpan balik |

---

## 7. Kriteria Go / No-Go (akhir Fase 0)

**GO** bila semua terpenuhi:
- [ ] A1 (arti "Trim"), A2 (batas UI "Hex Flow"), dan A3 (kebijakan GPU G1/G2/G3) telah diputuskan.
- [ ] S2 membuktikan chunk + merge benar (lolos Verify) dan **speedup bermakna** pada mode yang dipilih.
- [ ] S3 membuktikan deteksi GPU/CPU akurat dan fallback berfungsi.
- [ ] S1 & S4 membuktikan integrasi shell dan notifikasi dapat diandalkan di mesin bersih.
- [ ] Tidak ditemukan hambatan lisensi yang memblokir model distribusi yang direncanakan.

**TINJAU ULANG** bila: speedup paralel tidak bermakna (→ sederhanakan ke pemrosesan non-paralel atau ubah strategi), atau ukuran/kompleksitas runtime GPU tak tertangani (→ turunkan ke CPU-first).

**NO-GO** bila: tujuan produk hanya mungkin dengan GPU wajib *dan* target pengguna mayoritas tanpa GPU, tanpa jalan kompromi yang diterima owner.

---

## 8. Pertanyaan Terbuka (butuh keputusan owner)

1. **Apa arti "Trim"** dalam produk ini — potong rentang manual, auto-trim senyap, atau auto-trim berbasis konten? *(A1)*
2. **Apa yang dimaksud "Hex Flow model"** — seberapa minimal UI yang diharapkan (tray saja, overlay, jendela kecil)? *(A2)*
3. **Kebijakan GPU:** hard gate (G1), GPU + fallback CPU (G2), atau CPU saja (G3)? *(A3)*
4. **Output:** selalu file baru di samping sumber, atau perlu opsi timpa/lokasi kustom?
5. **Target pengguna & model bisnis:** gratis/open source, berbayar, atau internal? (mempengaruhi lisensi engine, signing, dan kanal distribusi)
6. **Dukungan OS minimum:** Windows 10 22H2 masih perlu didukung, atau hanya Windows 11?
7. **Bahasa implementasi inti:** tetap Python, atau terbuka mengevaluasi alternatif bila spike S5 menunjukkan masalah ukuran/start/false-positive?
8. **Format wajib MVP:** cukup Tier 1 (MP4, MKV, MOV, WEBM)?
