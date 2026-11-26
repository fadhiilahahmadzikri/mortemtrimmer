# Blueprint B — Cloudflare Pages + Next.js (GitHub Actions + Wrangler, CLI-first)

> Paradigma: **GitHub Actions yang membangun, lalu Wrangler meng-upload** hasilnya ke Cloudflare (Direct Upload).
> Hampir semua bisa dikerjakan dari terminal / agen. Satu-satunya langkah manual: membuat API token.
> Pipeline-nya tertulis sebagai kode di repo, jadi bisa di-review, diubah, dan direproduksi.

## 0. Tujuan & Hasil Akhir

- Landing page statis Next.js, domain gratis `https://<nama-proyek>.pages.dev`.
- `git push` ke `main` → GitHub Actions build + deploy → **Production**.
- Push ke branch lain / PR → deploy **Preview** dengan URL sendiri.
- Deploy tercatat di tab Actions GitHub dan di dashboard Cloudflare.

## 1. Prasyarat & Dependensi

| Alat | Fungsi | Instal / Cek |
|---|---|---|
| Bun (≥ 1.2) | Package manager + runner script | `bun -v` |
| Node.js LTS (≥ 20) | Tetap dibutuhkan: Next.js dan Wrangler berjalan di atas Node | `node -v` |
| Git | Versioning | `git --version` |
| GitHub CLI `gh` | Buat repo, set secret, lihat run | `gh --version` |
| Wrangler v4 | CLI Cloudflare (buat proyek, deploy) | `bun add -d wrangler` lalu `bunx wrangler --version` |

Python tidak diperlukan untuk bagian ini.

## 2. Keputusan Arsitektur

1. Next.js **static export** (`output: "export"`), hasil di `out/`.
2. Deploy memakai `cloudflare/wrangler-action@v3` dengan perintah `pages deploy`. Catatan: `cloudflare/pages-action` sudah **deprecated**; Cloudflare menyarankan pindah ke `wrangler-action`.
3. Autentikasi di CI memakai **API token** (bukan login OAuth).
4. Installer besar disimpan di GitHub Releases / R2, bukan di Pages.
5. Catatan masa depan: Cloudflare kini mendorong **Workers Static Assets** (`wrangler deploy`) untuk proyek baru. Bila nanti ingin migrasi, struktur build (`out/`) tetap sama; yang berubah hanya perintah deploy dan file `wrangler.toml`.

## 3. Langkah Setup

### 3.1 Proyek Next.js

```bash
bun create next-app@latest landing --ts --app --eslint --no-tailwind --src-dir --import-alias "@/*" --use-bun
cd landing
bun add -d wrangler
```

`next.config.ts`:

```ts
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export",
  images: { unoptimized: true },
  trailingSlash: true,
};

export default nextConfig;
```

```bash
bun run build   # pastikan out/ terbentuk
```

### 3.2 Buat API Token Cloudflare (satu-satunya langkah manual)

1. Dashboard Cloudflare → ikon profil → **My Profile** → **API Tokens** → **Create Token**.
2. **Custom token** → **Get started**.
3. Permissions: **Account → Cloudflare Pages → Edit**.
4. **Continue to summary → Create Token**. Salin token (hanya tampil sekali).
5. Catat juga **Account ID** (terlihat di URL dashboard `dash.cloudflare.com/<ACCOUNT_ID>/...` atau di halaman Workers & Pages).

Prinsip keamanan: token hanya diberi izin Pages Edit, jangan pakai Global API Key.

### 3.3 Buat proyek Pages dari terminal

```bash
export CLOUDFLARE_API_TOKEN="<token>"
export CLOUDFLARE_ACCOUNT_ID="<account-id>"

bunx wrangler pages project create <nama-proyek> --production-branch=main
```

### 3.4 Repo GitHub + secret (semua via `gh`)

```bash
git init -b main
git add . && git commit -m "init"   # pastikan bun.lock ikut ter-commit
gh auth login
gh repo create <nama-repo> --private --source=. --push

gh secret set CLOUDFLARE_API_TOKEN --body "$CLOUDFLARE_API_TOKEN"
gh secret set CLOUDFLARE_ACCOUNT_ID --body "$CLOUDFLARE_ACCOUNT_ID"
```

### 3.5 Workflow CI/CD

Buat `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Cloudflare Pages

on:
  push:
    branches: [main]
  pull_request:

concurrency:
  group: deploy-${{ github.ref }}
  cancel-in-progress: true

jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      deployments: write
      pull-requests: write
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: 22

      - uses: oven-sh/setup-bun@v2
        with:
          bun-version: latest   # disarankan dipin, mis. 1.2.15

      - run: bun install --frozen-lockfile
      - run: bun run build

      - name: Deploy
        uses: cloudflare/wrangler-action@v3
        with:
          apiToken: ${{ secrets.CLOUDFLARE_API_TOKEN }}
          accountId: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}
          command: pages deploy out --project-name=<nama-proyek> --branch=${{ github.head_ref || github.ref_name }}
```

Catatan Bun: `setup-bun` memasang Bun di runner, `--frozen-lockfile` memastikan versi dependensi identik dengan `bun.lock`. Node tetap dipasang karena Next.js/Wrangler memerlukannya. Jika langkah Deploy gagal menemukan Wrangler, pastikan `wrangler` ada di `devDependencies` dan langkah `bun install` sudah jalan sebelumnya.

Cara kerja branch: Pages menentukan Production vs Preview dari nama branch. Branch `main` (production branch yang Anda set saat `project create`) menjadi Production; branch lain menjadi Preview.

Commit & push workflow:

```bash
git add .github && git commit -m "ci: deploy to cloudflare pages" && git push
gh run watch     # pantau jalannya pipeline dari terminal
```

## 4. Alur Kerja Harian

```bash
git add . && git commit -m "update" && git push
gh run list --limit 5
bunx wrangler pages deployment list --project-name <nama-proyek>
```

## 5. Deploy Manual Darurat (tanpa CI)

```bash
bun run build
bunx wrangler pages deploy out --project-name <nama-proyek>
```

## 6. Domain

- **Gratis**: `<nama-proyek>.pages.dev`.
- Custom domain: opsional, tambahkan di dashboard proyek → **Custom domains** (domain dibeli terpisah).

## 7. Batas yang Perlu Diketahui (soal "CLI ada batasannya")

| Hal | Bisa via CLI? |
|---|---|
| Buat proyek Pages (Direct Upload) | Ya |
| Deploy, lihat daftar deployment | Ya |
| Set secret GitHub | Ya (`gh`) |
| Membuat API token pertama kali | Manual lewat dashboard |
| Menghubungkan Git integration bawaan Cloudflare | Manual lewat dashboard (lihat Blueprint A) |
| Custom domain | Bisa lewat API, paling mudah lewat dashboard |

Peringatan: proyek Pages yang dibuat dengan Direct Upload **tidak bisa** diubah menjadi Git integration belakangan (perlu membuat proyek baru). Pilih salah satu paradigma sejak awal.

## 8. Aturan Keamanan untuk Agen

- Jangan pernah mencetak atau meng-commit token. Simpan di `.env` lokal yang masuk `.gitignore`, dan di GitHub Secrets untuk CI.
- Token dibatasi: hanya Pages Edit.
- Jangan taruh rahasia di kode frontend; semua yang masuk `out/` bersifat publik.

## 9. Checklist Verifikasi

- [ ] `bun run build` lokal sukses
- [ ] `wrangler pages project create` sukses
- [ ] Dua secret ada: `gh secret list`
- [ ] Workflow hijau setelah push ke `main`
- [ ] `https://<nama-proyek>.pages.dev` terbuka
- [ ] PR/branch lain menghasilkan URL Preview
- [ ] Tautan unduh aplikasi berfungsi

## 10. Sumber

- Cloudflare Docs: *Deploy a static Next.js site* — https://developers.cloudflare.com/pages/framework-guides/nextjs/deploy-a-static-nextjs-site/
- `cloudflare/wrangler-action` (pengganti `pages-action` yang deprecated) — https://github.com/cloudflare/wrangler-action
- Cloudflare Docs: Pages Direct Upload with CI — https://developers.cloudflare.com/pages/get-started/direct-upload/
