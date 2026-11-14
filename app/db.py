"""Database KostFlow + data awal (seed).

Dua mode, otomatis dipilih:
  * DATABASE_URL ada di .env / environment  ->  Supabase (PostgreSQL)   <- mode utama
  * DATABASE_URL tidak ada                  ->  SQLite lokal di data/kostflow.db (untuk tes / cadangan)

Seluruh logika bisnis (services.py) tetap memakai q() dan run() dengan placeholder `?`,
jadi tidak perlu diubah: lapisan ini yang menerjemahkannya ke PostgreSQL.
"""
import hashlib
import logging
import os
import secrets
import sqlite3
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

try:  # .env opsional; kalau python-dotenv belum terpasang, pakai environment biasa
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / '.env')
except ImportError:  # pragma: no cover
    pass

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get('KOSTFLOW_DATA', BASE_DIR / 'data'))
UPLOAD_DIR = DATA_DIR / 'uploads'
DB_PATH = DATA_DIR / 'kostflow.db'
SCHEMA_SQL = BASE_DIR / 'supabase_schema.sql'

DATABASE_URL = (os.environ.get('DATABASE_URL') or '').strip()
USE_PG = bool(DATABASE_URL)

log = logging.getLogger('kostflow.db')

# ---------------------------------------------------------------- skema SQLite (mode cadangan)
SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS users(
  id INTEGER PRIMARY KEY, username TEXT UNIQUE, password_hash TEXT,
  role TEXT, full_name TEXT, phone TEXT);
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS rooms(
  id INTEGER PRIMARY KEY, code TEXT UNIQUE, type_name TEXT, floor INTEGER, size TEXT,
  price INTEGER, facilities TEXT, description TEXT, photo TEXT, status TEXT DEFAULT 'Tersedia');
CREATE TABLE IF NOT EXISTS reservations(
  id INTEGER PRIMARY KEY, code TEXT UNIQUE, room_id INTEGER, user_id INTEGER, name TEXT, phone TEXT,
  id_file TEXT, proof_file TEXT, deposit INTEGER, start_date TEXT, months INTEGER,
  status TEXT DEFAULT 'Menunggu', reject_reason TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS contracts(
  id INTEGER PRIMARY KEY, tenant_id INTEGER, room_id INTEGER, start_date TEXT,
  end_date TEXT, rent INTEGER, status TEXT DEFAULT 'Aktif');
CREATE TABLE IF NOT EXISTS invoices(
  id INTEGER PRIMARY KEY, number TEXT UNIQUE, contract_id INTEGER, tenant_id INTEGER,
  type TEXT, description TEXT, amount INTEGER, due_date TEXT, status TEXT DEFAULT 'Belum Dibayar',
  proof_file TEXT, reject_reason TEXT, ticket_id INTEGER, created_at TEXT, paid_at TEXT);
CREATE TABLE IF NOT EXISTS ledger(
  id INTEGER PRIMARY KEY, date TEXT, kind TEXT, category TEXT, description TEXT,
  amount INTEGER, invoice_id INTEGER);
CREATE TABLE IF NOT EXISTS tickets(
  id INTEGER PRIMARY KEY, number TEXT UNIQUE, tenant_id INTEGER, type TEXT, category TEXT,
  description TEXT, photo TEXT, priority TEXT, status TEXT DEFAULT 'Baru',
  reject_reason TEXT, schedule_note TEXT, cost INTEGER, rating INTEGER,
  created_at TEXT, updated_at TEXT);
CREATE TABLE IF NOT EXISTS notifications(
  id INTEGER PRIMARY KEY, user_id INTEGER, message TEXT, created_at TEXT, is_read INTEGER DEFAULT 0);
"""

# ---------------------------------------------------------------- koneksi PostgreSQL (Supabase)
_pool = None


def _get_pool():
    """Pool koneksi dibuat sekali. Pooler Supabase tidak mendukung prepared statement -> prepare_threshold=None."""
    global _pool
    if _pool is None:
        try:
            from psycopg.rows import dict_row
            from psycopg_pool import ConnectionPool
        except ImportError as e:  # pragma: no cover
            raise RuntimeError("Paket 'psycopg' belum terpasang. Jalankan: pip install -r requirements.txt") from e
        _pool = ConnectionPool(
            DATABASE_URL, min_size=1, max_size=5, open=False,
            kwargs={'autocommit': True, 'row_factory': dict_row, 'prepare_threshold': None, 'connect_timeout': 15},
            check=ConnectionPool.check_connection,
        )
        try:
            _pool.open(wait=True, timeout=30)
        except Exception as e:
            _pool = None
            raise RuntimeError(
                'Gagal terhubung ke Supabase. Periksa DATABASE_URL di file .env '
                '(pakai "Session pooler" dari tombol Connect di dashboard Supabase, dan password sudah benar). '
                f'Detail: {e}') from e
    return _pool


def _pg_sql(sql: str) -> str:
    """Terjemahkan placeholder SQLite (?) ke PostgreSQL (%s)."""
    return sql.replace('%', '%%').replace('?', '%s')


def _clean(row):
    """PostgreSQL mengembalikan Decimal untuk AVG/SUM tertentu; ubah ke angka biasa seperti SQLite."""
    for k, v in row.items():
        if isinstance(v, Decimal):
            row[k] = int(v) if v == v.to_integral_value() else float(v)
    return row


_NO_ID_TABLES = {'settings', 'files'}  # tabel tanpa kolom id


def _table_of_insert(sql: str) -> str:
    parts = sql.split(None, 3)  # INSERT INTO nama(...) ...
    return parts[2].split('(')[0].strip().lower() if len(parts) >= 3 else ''


# ---------------------------------------------------------------- SQLite
def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------------------- antarmuka q() / run()
def q(sql: str, params: tuple = (), one: bool = False):
    """Jalankan SELECT. one=True -> satu baris (atau None)."""
    if USE_PG:
        with _get_pool().connection() as conn:
            rows = [_clean(r) for r in conn.execute(_pg_sql(sql), params).fetchall()]
    else:
        conn = connect()
        try:
            rows = conn.execute(sql, params).fetchall()
        finally:
            conn.close()
    return (rows[0] if rows else None) if one else rows


def run(sql: str, params: tuple = ()) -> int:
    """Jalankan INSERT/UPDATE/DELETE. Untuk INSERT mengembalikan id baris baru."""
    if USE_PG:
        stmt = _pg_sql(sql)
        is_insert = sql.lstrip()[:6].upper() == 'INSERT'
        wants_id = is_insert and _table_of_insert(sql) not in _NO_ID_TABLES and 'RETURNING' not in stmt.upper()
        if wants_id:
            stmt += ' RETURNING id'
        with _get_pool().connection() as conn:
            cur = conn.execute(stmt, params)
            if wants_id:
                row = cur.fetchone()
                return row['id'] if row else 0
            return cur.rowcount
    conn = connect()
    try:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def store_file(fname: str, data: bytes) -> None:
    """Simpan file upload. Mode Supabase: di tabel `files` (permanen, tidak hilang saat server restart).
    Mode SQLite lokal: di folder data/uploads."""
    if USE_PG:
        run('INSERT INTO files(name,content) VALUES(?,?)', (fname, data))
    else:
        (UPLOAD_DIR / fname).write_bytes(data)


def load_file(fname: str) -> bytes | None:
    """Ambil isi file upload, atau None bila tidak ada."""
    if USE_PG:
        row = q('SELECT content FROM files WHERE name=?', (fname,), one=True)
        return bytes(row['content']) if row else None
    path = UPLOAD_DIR / fname
    return path.read_bytes() if path.is_file() else None


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(8)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100_000).hex()
    return f'{salt}${digest}'


def check_password(password: str, stored: str) -> bool:
    salt, _ = stored.split('$')
    return secrets.compare_digest(hash_password(password, salt), stored)


def backend_name() -> str:
    return 'Supabase (PostgreSQL)' if USE_PG else f'SQLite lokal ({DB_PATH})'


def init_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    if USE_PG:
        try:
            q('SELECT 1 FROM users LIMIT 1')
            q('SELECT 1 FROM rooms LIMIT 1')
            q('SELECT 1 FROM files LIMIT 1')
        except Exception as e:
            raise RuntimeError(
                'Tabel di Supabase belum ada / belum lengkap. Buka Supabase > SQL Editor, tempel isi file '
                f'"{SCHEMA_SQL.name}" lalu klik Run, kemudian jalankan ulang aplikasi. Detail: {e}') from e
    else:
        conn = connect()
        try:
            conn.executescript(SQLITE_SCHEMA)
            conn.commit()
        finally:
            conn.close()
    # Database lama: samakan nama akun demo penghuni (data awal sekarang "Adam Richie").
    run("UPDATE users SET full_name='Adam Richie' WHERE username='penghuni' AND full_name='Andi Pratama'")
    if not q('SELECT 1 FROM users', one=True):
        seed()
        from . import services
        services.seed_demo_history()
    print(f'[KostFlow] Database: {backend_name()}')


def seed() -> None:
    defaults = {
        'kost_name': 'Kost Harmoni',
        'tagline': 'Hunian nyaman, bersih, dan terkelola rapi untuk mahasiswa dan pekerja.',
        'address': 'Jl. Melati No. 12, Cikarang, Jawa Barat',
        'contact': 'WhatsApp pemilik: 0811-0001-11',
        'bank_info': 'BCA 1234567890 a.n. Sari Wulandari',
    }
    for k, v in defaults.items():
        run('INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value', (k, v))
    run('INSERT INTO users(username,password_hash,role,full_name,phone) VALUES(?,?,?,?,?)',
        ('pemilik', hash_password('pemilik123'), 'owner', 'Bu Sari (Pemilik)', '0811000111'))
    tid = run('INSERT INTO users(username,password_hash,role,full_name,phone) VALUES(?,?,?,?,?)',
              ('penghuni', hash_password('penghuni123'), 'tenant', 'Adam Richie', '0812000222'))
    desc = {
        'Standard': 'Kamar sederhana dan bersih dengan ventilasi baik. Cocok untuk yang mencari harga terjangkau.',
        'Deluxe': 'Kamar ber-AC dengan kamar mandi dalam. Tenang, sejuk, dan nyaman untuk istirahat maupun belajar.',
        'Premium': 'Kamar terluas dengan AC, water heater, dan fasilitas lengkap. Pilihan paling nyaman di kost ini.',
    }
    rooms = [
        ('A1', 'Standard', 1, '3x4 m', 900_000, 'Kasur, lemari, kipas angin, kamar mandi luar', 'Terisi'),
        ('A2', 'Standard', 1, '3x4 m', 900_000, 'Kasur, lemari, kipas angin, kamar mandi luar', 'Tersedia'),
        ('A3', 'Standard', 1, '3x4 m', 950_000, 'Kasur, lemari, kipas angin, jendela besar', 'Tersedia'),
        ('B1', 'Deluxe', 2, '3x4 m', 1_200_000, 'AC, kasur, lemari, kamar mandi dalam', 'Terisi'),
        ('B2', 'Deluxe', 2, '3x4 m', 1_200_000, 'AC, kasur, lemari, kamar mandi dalam', 'Tersedia'),
        ('B3', 'Premium', 2, '4x4 m', 1_500_000, 'AC, water heater, meja kerja, kamar mandi dalam', 'Tersedia'),
        ('C1', 'Premium', 3, '4x4 m', 1_600_000, 'AC, water heater, balkon, kamar mandi dalam', 'Tersedia'),
        ('C2', 'Premium', 3, '4x5 m', 1_900_000, 'AC, water heater, balkon, dapur kecil, kamar mandi dalam', 'Tersedia'),
    ]
    for code, typ, floor, size, price, fac, st in rooms:
        run('INSERT INTO rooms(code,type_name,floor,size,price,facilities,description,status) VALUES(?,?,?,?,?,?,?,?)',
            (code, typ, floor, size, price, fac, desc[typ], st))
    room = q("SELECT id FROM rooms WHERE code='A1'", one=True)
    start = date.today().replace(day=1) - timedelta(days=62)
    start = start.replace(day=1)
    end = date(start.year + 1, start.month, 1)
    run('INSERT INTO contracts(tenant_id,room_id,start_date,end_date,rent) VALUES(?,?,?,?,?)',
        (tid, room['id'], start.isoformat(), end.isoformat(), 900_000))
