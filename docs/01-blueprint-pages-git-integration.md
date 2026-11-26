# Blueprint A — Cloudflare Pages + Next.js (Git Integration)

> Paradigma: **Cloudflare yang membangun & men-deploy sendiri** setiap ada `git push`.
> Tidak ada file CI di repo. Paling sedikit konfigurasi, tapi setup awal sekali harus lewat dashboard.

## 0. Tujuan & Hasil Akhir

- Landing page statis (Next.js) berisi tautan unduh aplikasi.
- Domain gratis: `https://<nama-proyek>.pages.dev`.
- `git push` ke `main` → otomatis build → live (Production).
- `git push` ke branch lain / Pull Request → otomatis dapat URL Preview (`<branch>.<nama-proyek>.pages.dev`).

## 1. Prasyarat & Dependensi

| Alat | Fungsi | Cek |
|---|---|---|
| Bun (≥ 1.2) | Package manager + runner script | `bun -v` |
| Node.js LTS (≥ 20) | Tetap dibutuhkan: Next.js dan Wrangler berjalan di atas Node | `node -v` |
| Git | Versioning | `git --version` |
| GitHub CLI (`gh`) | Buat repo & push dari terminal | `gh --version` |
| Wrangler (CLI Cloudflare) | Cek login, lihat deployment, deploy manual | `bunx wrangler --version` |

Catatan: Bun menggantikan npm untuk install dan menjalankan script, tetapi Node.js sebaiknya tetap terpasang karena Next.js dan Wrangler membutuhkannya. Python **tidak diperlukan** untuk sisi frontend ini. Python hanya relevan kalau backend/aplikasi Anda memakainya.

## 2. Keputusan Arsitektur (jangan diubah tanpa alasan)

1. Next.js dipakai sebagai **static export** (`output: "export"`). Artinya tidak ada SSR, tidak ada API route runtime. Cocok untuk landing page.
2. Output build ada di folder `out/`.
3. File installer besar **jangan** ditaruh di repo/Pages. Simpan di GitHub Releases (atau R2) lalu tautkan dari landing page. (Pages punya batas ukuran per file; verifikasi batas terbaru di dokumentasi Cloudflare.)
4. Catatan industri: Cloudflare kini menyarankan **Workers (Static Assets)** untuk proyek baru, tetapi Pages masih didukung penuh dan sesuai permintaan blueprint ini. Lihat Blueprint B untuk catatan migrasi.

## 3. Langkah Setup

### 3.1 Buat proyek Next.js

```bash
bun create next-app@latest landing --ts --app --eslint --no-tailwind --src-dir --import-alias "@/*" --use-bun
cd landing
```

Edit `next.config.ts`:

```ts
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export",          // hasil statis ke folder out/
  images: { unoptimized: true }, // wajib, karena tidak ada server image optimizer
  trailingSlash: true,
};

export default nextConfig;
```

Tes lokal:

```bash
bun run build      # harus menghasilkan folder out/
```

### 3.2 Push ke GitHub (dari terminal)

```bash
git init -b main
git add . && git commit -m "init landing page"   # pastikan bun.lock ikut ter-commit
gh auth login                       # sekali saja
gh repo create <nama-repo> --private --source=. --push
```

### 3.3 Hubungkan repo ke Cloudflare Pages (sekali, via dashboard)

Bagian ini **tidak bisa sepenuhnya lewat CLI** karena butuh otorisasi aplikasi GitHub milik Cloudflare:

1. Dashboard Cloudflare → **Workers & Pages** → **Create** → tab **Pages** → **Connect to Git**.
2. Pilih repo GitHub → **Begin setup**.
3. Isi build settings:

| Opsi | Nilai |
|---|---|
| Framework preset | Next.js (Static HTML Export) |
| Production branch | `main` |
| Build command | `bun run build` |
| Build output directory | `out` |

4. (Disarankan) Environment variable: `BUN_VERSION` = versi Bun lokal Anda (cek `bun -v`) supaya build di Cloudflare sama dengan lokal. Image build Cloudflare sudah menyertakan Bun (default 1.2.15 pada dokumentasi yang saya baca), tetapi versinya bisa berubah.
5. Cek log build pertama: pastikan dependensi terpasang dengan Bun. Jika ternyata memakai npm, set `SKIP_DEPENDENCY_INSTALL` = `1` dan ubah Build command menjadi `bun install --frozen-lockfile && bun run build`.
6. **Save and Deploy**.

Selesai. Mulai sekarang setiap push otomatis ter-deploy.

## 4. Alur Kerja Harian

```bash
git add . && git commit -m "ubah hero" && git push
```

Cloudflare akan: clone → install dependensi → `bun run build` → publish `out/`. Riwayat deployment tampil di dashboard proyek.

## 5. Peran CLI (Wrangler) di paradigma ini

Wrangler tidak dipakai untuk deploy utama, tapi berguna untuk memantau dan darurat:

```bash
bunx wrangler login                                   # OAuth lewat browser, sekali saja
bunx wrangler pages project list                      # daftar proyek
bunx wrangler pages deployment list --project-name <nama-proyek>
bun run build && bunx wrangler pages deploy out --project-name <nama-proyek>   # deploy manual darurat
```

Untuk lingkungan tanpa browser (server/agen), pakai API token (lihat Blueprint B bagian 3).

## 6. Domain

- **Gratis**: `<nama-proyek>.pages.dev` otomatis diberikan.
- **Custom domain** (opsional, berbayar karena beli domain): Dashboard → proyek → **Custom domains** → tambahkan.

## 7. Batas & Gotcha

- Tier gratis: bandwidth statis tanpa batas, jumlah build per bulan terbatas (sekitar 500 saat dokumen ini ditulis; verifikasi ulang).
- Static export: tidak bisa memakai SSR, `middleware`, atau route handler dinamis. Kalau butuh backend kecil, pakai Pages Functions (folder `functions/`) atau Worker terpisah.
- `next/image` wajib `unoptimized: true`.
- Rahasia (API key) **jangan** ditaruh di kode frontend. Apa pun yang dikirim ke browser bersifat publik.

## 8. Checklist Verifikasi

- [ ] `bun run build` lokal sukses dan `out/index.html` ada
- [ ] Repo ada di GitHub, branch `main`
- [ ] Proyek Pages terhubung ke repo, build pertama hijau
- [ ] `https://<nama-proyek>.pages.dev` bisa dibuka
- [ ] Push commit kecil → deployment baru muncul otomatis
- [ ] Tautan unduh aplikasi berfungsi

## 9. Sumber

- Cloudflare Docs: *Deploy a static Next.js site* — https://developers.cloudflare.com/pages/framework-guides/nextjs/deploy-a-static-nextjs-site/
