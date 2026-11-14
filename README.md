# KostFlow

Platform web manajemen rumah kost (NiceGUI + Supabase/PostgreSQL; SQLite lokal sebagai cadangan). Tiga tampilan berdasarkan peran
(Pemilik, Penghuni, Calon Penghuni) plus billing engine otomatis. Tampilan menyesuaikan laptop dan HP.

## Struktur folder

```
kostflow/
├── main.py              # titik masuk: route file berizin, scheduler billing, ui.run()
├── requirements.txt
├── supabase_schema.sql  # tempel di Supabase > SQL Editor (membuat 9 tabel + RLS)
├── .env.example         # contoh isi .env (DATABASE_URL)
├── render.yaml          # konfigurasi deploy Render (opsional)
├── app/
│   ├── db.py            # koneksi Supabase (Postgres) / SQLite cadangan + data awal (seed)
│   ├── services.py      # SEMUA logika bisnis (reservasi, billing, kontrak, pembayaran, tiket, laporan)
│   ├── theme.py         # tema warna (5 tema, gelap/terang), CSS global, animasi, logo
│   ├── shell.py         # sidebar, bilah atas, header publik
│   ├── ui_common.py     # hero/tile, upload aman, dialog, ganti password
│   ├── ui_rooms.py      # kartu & detail kamar (SOLD abu-abu)
│   ├── static/          # logo + ilustrasi kamar bawaan
│   └── pages/           # public (/), login, applicant, tenant, owner
├── tests/test_services.py   # 18 tes logika bisnis
└── data/                # dibuat otomatis: uploads/, .secret (kostflow.db hanya di mode SQLite)
```

## Setup Supabase (sekali saja)

1. **Buat tabel**: Supabase > *SQL Editor* > *New query* > tempel seluruh isi `supabase_schema.sql` > *Run*.
   (Kalau dulu sudah pernah membuat tabel dengan struktur lain, hapus tanda `--` pada blok `DROP TABLE` di bagian atas file itu dulu.)
2. **Ambil connection string**: klik tombol *Connect* di Supabase > tab *Session pooler* > salin URI-nya.
3. **Buat file `.env`** (salin dari `.env.example`) berisi satu baris `DATABASE_URL=...` dengan password database yang benar.
   Jika password mengandung karakter khusus (`@ : / # ?`), ubah ke bentuk URL-encoded (`@` -> `%40`, dst.) atau reset password jadi huruf+angka saja.
4. Jalankan `python main.py`. Saat pertama kali, kamar & akun demo otomatis diisi. Terminal akan menampilkan
   `[KostFlow] Database: Supabase (PostgreSQL)`. Jika tertulis `SQLite lokal`, berarti `.env` belum terbaca.

## Jalankan di komputer

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Buka http://localhost:8080. Untuk mengulang dari data awal di Supabase: jalankan `TRUNCATE users, settings, rooms, reservations, contracts, invoices, ledger, tickets, notifications RESTART IDENTITY;` di SQL Editor, lalu jalankan ulang aplikasi.

Akun demo:

| Peran | Username | Password |
|---|---|---|
| Pemilik | pemilik | pemilik123 |
| Penghuni (Adam Richie) | penghuni | penghuni123 |
| Calon penghuni | daftar sendiri di tab **Daftar** | - |

**Sebelum dipakai sungguhan:** ganti password akun demo lewat menu avatar > *Ganti password*.

## Menjalankan tes

```bash
python -m unittest discover -s tests -v
```

Tes memakai database sementara, tidak menyentuh `data/`.

## Fitur utama

| Proses | Di aplikasi |
|---|---|
| Onboarding | daftar akun, reservasi + KTP + bukti deposit, pemilik setujui/tolak, akun jadi penghuni, kamar `Terisi` |
| Billing engine | tagihan terbit H-7 jatuh tempo, pengingat, jalan tiap jam + tombol manual |
| Verifikasi pembayaran | penghuni unggah bukti, pemilik valid/tolak, masuk buku kas |
| Kontrak | tab **Kontrak** (pemilik): perpanjang 1/3/6/12 bulan atau akhiri. Kontrak yang habis ditutup otomatis, kamar kembali `Tersedia`, penghuni yang sudah lunas kembali jadi calon penghuni. Pengingat 30 hari sebelum habis |
| Keluhan & permintaan | Baru > Diterima/Ditolak > Diproses > Selesai > Dikonfirmasi (rating) / Dibuka Ulang; permintaan berbiaya lewat penawaran |
| Laporan | okupansi, arus kas, tunggakan, rating, ekspor CSV |

## Keamanan (ringkas)

- File upload **tidak publik**: foto kamar terbuka untuk umum; KTP, bukti transfer, dan foto keluhan hanya bisa dibuka
  pemilik kost dan penggunggahnya (route `/uploads/...` di `main.py`).
- Upload dibatasi JPG/PNG/WEBP/GIF/PDF, maks 5 MB, dan isi file dicek sesuai ekstensinya (SVG/HTML ditolak).
- `STORAGE_SECRET` dari env; bila kosong dibuat acak otomatis dan disimpan di `data/.secret`.
- Login dikunci sementara setelah 5 kali salah dalam 5 menit.
- Aksi ganda (klik dua kali, dua tab) diblokir: reservasi, verifikasi pembayaran, dan tiket memeriksa status terakhir.
- Ekspor CSV aman dari "CSV injection".

## Deploy gratis (Render)

1. Upload folder ini ke repository GitHub.
2. render.com > **New > Blueprint** > pilih repo (atau Web Service: Build `pip install -r requirements.txt`, Start `python main.py`).
3. Buka `https://kostflow-xxxx.onrender.com`.

Catatan paket gratis: server tidur setelah ~15 menit; **database dan upload kembali ke data awal saat restart/redeploy**
(cukup untuk demo). Untuk data permanen, pakai disk berbayar Render (arahkan `KOSTFLOW_DATA` ke path disk) atau
database eksternal. Variabel lingkungan: `DATABASE_URL` (wajib untuk Supabase), `PORT`, `STORAGE_SECRET`, `KOSTFLOW_DATA`.
Dengan Supabase, data tabel kini permanen walau Render restart; yang masih sementara hanya file upload (KTP/bukti) di `data/uploads/`.

Kirim WhatsApp bisa ditambahkan dengan memanggil API gateway (mis. Fonnte) di fungsi `notify()` pada `services.py`.
