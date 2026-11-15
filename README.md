<div align="center">

<img src="app/static/logo.svg" alt="Logo KostFlow" width="80" />

# KostFlow

**Platform web manajemen rumah kost: dari reservasi kamar, tagihan otomatis, sampai laporan keuangan, dalam satu aplikasi.**

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![NiceGUI](https://img.shields.io/badge/NiceGUI-3.x-5898D4)
![PostgreSQL](https://img.shields.io/badge/Supabase-PostgreSQL-3ECF8E?logo=supabase&logoColor=white)
![Tests](https://img.shields.io/badge/tes-19%20lulus-brightgreen)

</div>

---

## Daftar Isi

- [Tentang Proyek](#tentang-proyek)
- [Fitur Utama](#fitur-utama)
- [Tampilan Aplikasi](#tampilan-aplikasi)
- [Teknologi yang Digunakan](#teknologi-yang-digunakan)
- [Cara Menjalankan](#cara-menjalankan)
- [Akun Demo](#akun-demo)
- [Struktur Proyek](#struktur-proyek)
- [Keamanan](#keamanan)
- [Pengujian](#pengujian)
- [Deploy ke Render](#deploy-ke-render)
- [Keterbatasan & Rencana Pengembangan](#keterbatasan--rencana-pengembangan)
- [Pembuat](#pembuat)
- [Lisensi](#lisensi)

---

## Tentang Proyek

Banyak pemilik kost masih mengelola usahanya secara manual: pendaftaran lewat chat, bukti transfer yang tercecer di galeri HP, tagihan yang diingatkan satu per satu, dan pembukuan di buku tulis. Cara ini rawan salah catat, sulit dilacak, dan memakan waktu.

**KostFlow** menyatukan seluruh proses itu dalam satu aplikasi web. Pemilik kost mendapat dasbor untuk memantau okupansi, pembayaran, dan keuangan. Penghuni bisa melihat tagihan, mengunggah bukti bayar, dan mengajukan keluhan. Calon penghuni bisa memilih kamar dan memesannya secara online. Tampilan menyesuaikan layar laptop maupun HP.

## Fitur Utama

Aplikasi memiliki **tiga peran pengguna** dengan tampilan masing-masing, ditambah **billing engine** yang berjalan otomatis.

### Calon Penghuni

- Melihat katalog kamar publik (tipe, lantai, ukuran, harga, fasilitas). Kamar yang sudah terisi ditandai abu-abu dengan label **SOLD**.
- Mendaftar akun, lalu memesan kamar dengan mengunggah KTP dan bukti deposit.
- Memantau status reservasi: menunggu, disetujui, atau ditolak (beserta alasannya).

### Penghuni

- Melihat tagihan sewa dan mengunggah bukti pembayaran.
- Mengajukan **keluhan** atau **permintaan layanan** dengan foto, lalu memantau statusnya dan memberi rating setelah selesai.
- Melihat riwayat pembayaran dan kuitansi.
- Menerima notifikasi pengingat tagihan dan kontrak.

### Pemilik

- **Laporan**: okupansi, arus kas, tunggakan, rating layanan, dan ekspor CSV.
- **Reservasi**: menyetujui atau menolak pendaftar. Jika disetujui, akun otomatis menjadi penghuni dan kamar berstatus `Terisi`.
- **Pembayaran**: memverifikasi bukti transfer (valid/tolak), yang otomatis tercatat di buku kas.
- **Ajuan**: mengelola keluhan dan permintaan layanan, termasuk penawaran biaya.
- **Kontrak**: memperpanjang (1/3/6/12 bulan) atau mengakhiri kontrak.
- **Kamar**: menambah dan mengubah data kamar.
- **Buku kas**: mencatat pemasukan dan pengeluaran.

### Billing Engine Otomatis

Berjalan di latar belakang setiap jam (dan bisa dipicu manual oleh pemilik):

| Proses             | Perilaku                                                              |
| ------------------ | --------------------------------------------------------------------- |
| Penerbitan tagihan | Tagihan sewa terbit otomatis **7 hari sebelum jatuh tempo**           |
| Pengingat tagihan  | Notifikasi ke penghuni saat jatuh tempo ≤ 3 hari atau sudah terlambat |
| Pengingat kontrak  | Notifikasi ke penghuni dan pemilik **30 hari sebelum kontrak habis**  |
| Penutupan kontrak  | Kontrak yang habis ditutup otomatis, kamar kembali `Tersedia`         |

### Alur Siklus Hidup Penghuni

```mermaid
flowchart LR
    A[Daftar akun] --> B[Pilih kamar<br/>+ unggah KTP & deposit]
    B --> C{Pemilik<br/>memeriksa}
    C -- Ditolak --> D[Kamar kembali tersedia]
    C -- Disetujui --> E[Jadi penghuni<br/>kontrak dibuat]
    E --> F[Tagihan terbit otomatis]
    F --> G[Unggah bukti bayar]
    G --> H{Pemilik<br/>verifikasi}
    H -- Valid --> I[Masuk buku kas]
    H -- Ditolak --> G
    E --> J[Kontrak habis /<br/>diakhiri]
    J --> K[Kamar kembali tersedia]
```

## Tampilan Aplikasi

### Pemilik: Laporan Kost

![Dasbor Pemilik](pemilik.jpeg)

Ringkasan okupansi, pemasukan dan pengeluaran bulan ini, laba bersih, tagihan belum lunas, serta daftar hal yang perlu ditindaklanjuti.

### Penghuni: Beranda & Tagihan

![Beranda Penghuni](penghuni.jpeg)

Penghuni melihat sewa per bulan, tagihan aktif, sisa masa kontrak, dan ajuan yang sedang berjalan.

### Calon Penghuni: Pilih Kamar

![Pilih Kamar](calon-penghuni.png)

Calon penghuni memilih kamar yang tersedia, lalu mengunggah KTP dan bukti deposit.

### Tampilan di HP

<img src="mobile.jpeg" alt="Tampilan HP" width="300" />

Halaman depan menyesuaikan layar HP.

Aplikasi menyediakan **5 tema warna** (Homie, Malam, Hutan, Samudra, Sakura), masing-masing dengan mode gelap dan terang.

## Teknologi yang Digunakan

| Bagian                | Teknologi                                            |
| --------------------- | ---------------------------------------------------- |
| Bahasa                | Python                                               |
| Framework UI & server | [NiceGUI](https://nicegui.io) (berbasis FastAPI)     |
| Database utama        | Supabase (PostgreSQL) lewat `psycopg`                |
| Database cadangan     | SQLite (otomatis dipakai jika `DATABASE_URL` kosong) |
| Konfigurasi           | `python-dotenv`                                      |
| Pengujian             | `unittest` bawaan Python                             |
| Hosting               | Render (opsional, lewat `render.yaml`)               |

## Cara Menjalankan

### Prasyarat

- Python 3.10 atau lebih baru
- (Opsional) Akun [Supabase](https://supabase.com) untuk database PostgreSQL. Tanpa ini, aplikasi tetap jalan memakai SQLite lokal.

### Opsi 1: Cepat dengan SQLite (tanpa setup database)

```bash
git clone https://github.com/bomass1116/kostflow.git
cd kostflow

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python main.py
```

Buka **http://localhost:8080**. Saat pertama kali jalan, data kamar dan akun demo terisi otomatis.

### Opsi 2: Dengan Supabase (PostgreSQL)

1. **Buat tabel.** Di Supabase, buka _SQL Editor_ → _New query_, tempel seluruh isi `supabase_schema.sql`, lalu _Run_. Ini membuat 10 tabel beserta aturan RLS.
2. **Ambil connection string.** Klik _Connect_ di Supabase → tab _Session pooler_ → salin URI-nya.
3. **Buat file `.env`** di folder utama proyek:
   ```env
   DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/postgres
   ```
   Jika password mengandung karakter khusus (`@ : / # ?`), ubah ke bentuk URL-encoded (misalnya `@` menjadi `%40`), atau reset password menjadi huruf dan angka saja.
4. **Jalankan** `python main.py`. Terminal akan menampilkan `[KostFlow] Database: Supabase (PostgreSQL)`. Jika yang tampil `SQLite lokal`, berarti file `.env` belum terbaca.

Untuk mengulang dari data awal di Supabase, jalankan perintah ini di SQL Editor, lalu start ulang aplikasi:

```sql
TRUNCATE users, settings, rooms, reservations, contracts, invoices, ledger, tickets, notifications RESTART IDENTITY;
```

### Variabel Lingkungan

| Variabel         | Fungsi                                                              | Wajib?                    |
| ---------------- | ------------------------------------------------------------------- | ------------------------- |
| `DATABASE_URL`   | Koneksi Supabase/PostgreSQL                                         | Hanya untuk mode Supabase |
| `PORT`           | Port server (default `8080`)                                        | Tidak                     |
| `STORAGE_SECRET` | Kunci sesi. Jika kosong, dibuat acak dan disimpan di `data/.secret` | Tidak                     |
| `KOSTFLOW_DATA`  | Lokasi folder data/upload (default `./data`)                        | Tidak                     |

## Akun Demo

| Peran          | Username                            | Password      |
| -------------- | ----------------------------------- | ------------- |
| Pemilik        | `pemilik`                           | `pemilik123`  |
| Penghuni       | `penghuni`                          | `penghuni123` |
| Calon penghuni | Daftar sendiri lewat tab **Daftar** | -             |

> ⚠️ Akun ini hanya untuk demo. **Ganti password** lewat menu avatar → _Ganti password_ sebelum aplikasi dipakai sungguhan.

Data awal berisi 8 kamar contoh (tipe Standard, Deluxe, Premium; harga Rp900.000 sampai Rp1.900.000 per bulan).

## Struktur Proyek

```
kostflow/
├── main.py                 # Titik masuk: route file berizin, scheduler billing, ui.run()
├── requirements.txt        # Dependensi Python
├── supabase_schema.sql     # Skema database (10 tabel + RLS)
├── render.yaml             # Konfigurasi deploy Render
├── app/
│   ├── db.py               # Koneksi Supabase/SQLite + data awal (seed)
│   ├── services.py         # Seluruh logika bisnis (reservasi, billing, kontrak, pembayaran, tiket, laporan)
│   ├── theme.py            # Tema warna, CSS global, animasi
│   ├── shell.py            # Sidebar, bilah atas, header publik
│   ├── ui_common.py        # Komponen bersama: upload aman, dialog, ganti password
│   ├── ui_rooms.py         # Kartu dan detail kamar
│   ├── static/             # Logo dan ilustrasi kamar bawaan
│   └── pages/              # Halaman per peran
│       ├── public.py       #   /           katalog kamar publik
│       ├── login.py        #   /login      masuk & daftar
│       ├── applicant.py    #   /applicant  calon penghuni
│       ├── tenant.py       #   /tenant     penghuni
│       └── owner.py        #   /owner      pemilik
├── docs/
│   └── screenshots/        # Gambar tampilan aplikasi untuk README
├── tests/
│   └── test_services.py    # 19 tes logika bisnis
└── data/                   # Dibuat otomatis: uploads/, .secret (kostflow.db hanya di mode SQLite)
```

Logika bisnis sengaja dipisahkan di `services.py`, terpisah dari tampilan (`pages/`), sehingga bisa diuji tanpa membuka antarmuka.

## Keamanan

- **File upload tidak publik.** Foto kamar terbuka untuk umum, tetapi KTP, bukti transfer, dan foto keluhan hanya bisa dibuka oleh pemilik kost dan pengunggahnya (route `/uploads/...`).
- **Validasi upload.** Hanya JPG, PNG, WEBP, GIF, dan PDF dengan ukuran maksimal 5 MB. Isi file dicek sesuai ekstensinya, dan SVG/HTML ditolak.
- **Pembatasan login.** Akun dikunci sementara setelah 5 kali salah password dalam 5 menit.
- **Perlindungan aksi ganda.** Klik dua kali atau dua tab sekaligus tidak menghasilkan data ganda, karena reservasi, verifikasi pembayaran, dan tiket memeriksa status terakhir.
- **Ekspor CSV aman** dari _CSV injection_.
- **Rahasia tidak masuk repo.** `.env`, `data/.secret`, dan database lokal sudah masuk `.gitignore`.

## Pengujian

```bash
python -m unittest discover -s tests -v
```

Terdapat **19 tes** yang mencakup alur reservasi, penerbitan tagihan (tidak ganda), verifikasi pembayaran, penutupan dan perpanjangan kontrak, alur keluhan dan permintaan layanan, izin akses file, pembatasan login, dan keamanan ekspor CSV. Tes memakai database sementara dan tidak menyentuh folder `data/`.

## Deploy ke Render

1. Unggah proyek ke repository GitHub.
2. Di [render.com](https://render.com), pilih **New → Blueprint** lalu pilih repository ini (atau buat Web Service manual dengan Build `pip install -r requirements.txt` dan Start `python main.py`).
3. Isi `DATABASE_URL` di dashboard Render. Nilai ini sengaja tidak ditulis di `render.yaml` agar tidak bocor ke GitHub.
4. Buka alamat `https://kostflow-xxxx.onrender.com`.

Endpoint `/healthz` tersedia untuk layanan ping (UptimeRobot, cron-job.org) agar server tidak tertidur dan database Supabase tidak di-pause.

> **Catatan paket gratis Render:** server tidur setelah sekitar 15 menit tidak aktif. Data tabel tetap permanen jika memakai Supabase, tetapi **file upload (KTP, bukti transfer) kembali kosong saat restart atau redeploy**. Cukup untuk demo; untuk produksi gunakan disk berbayar (arahkan `KOSTFLOW_DATA` ke path disk) atau penyimpanan eksternal.

## Keterbatasan & Rencana Pengembangan

- [ ] Notifikasi WhatsApp lewat API gateway (misalnya Fonnte), dengan memanggil gateway dari fungsi `notify()` di `services.py`
- [ ] Penyimpanan file upload yang permanen (misalnya Supabase Storage)
- [ ] Integrasi pembayaran online
- [ ] Dukungan beberapa properti kost dalam satu akun pemilik

## Pembuat

Dibuat oleh tim yang beranggotakan tiga orang:

| Nama                            | NIM      |
| ------------------------------- | -------- |
| Adam Richie Wijaya              | 52250064 |
| Boma Satrio Wicaksono Dewantoro | 52250061 |
| Syafif Azmi Lontoh              | 52250060 |

Proyek untuk **Sains Data Industri**.
