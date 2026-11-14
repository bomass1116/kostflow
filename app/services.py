"""Logika bisnis KostFlow: reservasi, billing engine, pembayaran, tiket, laporan."""
import calendar
import random
import string
from collections import defaultdict
from datetime import date, datetime, timedelta

from .db import check_password, hash_password, q, run

REMIND_DAYS = 7  # tagihan terbit H-7 sebelum jatuh tempo


# ---------- util ----------
def now() -> str:
    return datetime.now().strftime('%Y-%m-%d %H:%M')


def add_months(d: date, n: int) -> date:
    m = d.month - 1 + n
    y, m = d.year + m // 12, m % 12 + 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


BULAN = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 'Juli', 'Agustus',
         'September', 'Oktober', 'November', 'Desember']


def tgl(d) -> str:
    """'2026-11-09' -> '9 Nov 2026'"""
    if isinstance(d, str):
        d = date.fromisoformat(d[:10])
    return f'{d.day} {BULAN[d.month - 1][:3]} {d.year}'


def rp(n) -> str:
    return 'Rp ' + f'{int(n or 0):,}'.replace(',', '.')


def notify(user_id: int, message: str) -> None:
    run('INSERT INTO notifications(user_id,message,created_at) VALUES(?,?,?)', (user_id, message, now()))


def notify_owner(message: str) -> None:
    for o in q("SELECT id FROM users WHERE role='owner'"):
        notify(o['id'], message)


def notifications(user_id: int):
    return q('SELECT * FROM notifications WHERE user_id=? ORDER BY id DESC LIMIT 30', (user_id,))


def unread_count(user_id: int) -> int:
    return q('SELECT COUNT(*) c FROM notifications WHERE user_id=? AND is_read=0', (user_id,), one=True)['c']


def mark_read(user_id: int) -> None:
    run('UPDATE notifications SET is_read=1 WHERE user_id=?', (user_id,))


# ---------- akun & pengaturan ----------
def register_user(username: str, password: str, full_name: str, phone: str) -> int:
    """Daftar akun baru. Peran awal: calon penghuni (applicant)."""
    username = username.strip().lower()
    if len(username) < 4 or not username.isalnum():
        raise ValueError('Username minimal 4 karakter, hanya huruf dan angka')
    if len(password) < 6:
        raise ValueError('Password minimal 6 karakter')
    if not full_name.strip() or not phone.strip():
        raise ValueError('Nama lengkap dan nomor WhatsApp wajib diisi')
    if q('SELECT 1 FROM users WHERE username=?', (username,), one=True):
        raise ValueError('Username sudah dipakai, pilih yang lain')
    uid = run('INSERT INTO users(username,password_hash,role,full_name,phone) VALUES(?,?,?,?,?)',
              (username, hash_password(password), 'applicant', full_name.strip(), phone.strip()))
    notify(uid, 'Selamat datang di KostFlow. Pilih kamar yang Anda suka lalu ajukan reservasi.')
    return uid


_LOGIN_FAILS: dict[str, list[float]] = {}
LOGIN_MAX_FAILS, LOGIN_WINDOW = 5, 300  # 5 kali salah dalam 5 menit -> dikunci sementara


def login_wait(username: str) -> int:
    """Sisa detik penguncian login untuk username ini (0 = boleh mencoba)."""
    import time
    now_ = time.time()
    fails = [t for t in _LOGIN_FAILS.get(username, []) if now_ - t < LOGIN_WINDOW]
    _LOGIN_FAILS[username] = fails
    return int(LOGIN_WINDOW - (now_ - fails[0])) + 1 if len(fails) >= LOGIN_MAX_FAILS else 0


def login_failed(username: str) -> None:
    import time
    _LOGIN_FAILS.setdefault(username, []).append(time.time())


def login_ok(username: str) -> None:
    _LOGIN_FAILS.pop(username, None)


def change_password(user_id: int, old: str, new: str) -> None:
    u = get_user(user_id)
    if not u or not check_password(old or '', u['password_hash']):
        raise ValueError('Password lama salah')
    if len(new or '') < 6:
        raise ValueError('Password baru minimal 6 karakter')
    run('UPDATE users SET password_hash=? WHERE id=?', (hash_password(new), user_id))


def can_view_file(user, fname: str) -> bool:
    """Izin melihat file upload. Foto kamar publik; dokumen lain hanya pemilik kost atau penggunggahnya."""
    if q('SELECT 1 FROM rooms WHERE photo=?', (fname,), one=True):
        return True
    if not user:
        return False
    if user['role'] == 'owner':
        return True
    uid = user['id']
    return bool(
        q('SELECT 1 FROM reservations WHERE user_id=? AND (id_file=? OR proof_file=?)', (uid, fname, fname), one=True)
        or q('SELECT 1 FROM invoices WHERE tenant_id=? AND proof_file=?', (uid, fname), one=True)
        or q('SELECT 1 FROM tickets WHERE tenant_id=? AND photo=?', (uid, fname), one=True))


def get_user(uid: int):
    return q('SELECT * FROM users WHERE id=?', (uid,), one=True)


def setting(key: str) -> str:
    row = q('SELECT value FROM settings WHERE key=?', (key,), one=True)
    return row['value'] if row else ''


def set_setting(key: str, value: str) -> None:
    run('INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value', (key, value))


# ---------- 1. onboarding & manajemen unit ----------
ROOM_FIELDS = {'code', 'type_name', 'floor', 'size', 'price', 'facilities', 'description', 'photo', 'status'}


def rooms(status: str | None = None):
    if status:
        return q('SELECT * FROM rooms WHERE status=? ORDER BY code', (status,))
    return q("SELECT * FROM rooms ORDER BY CASE status WHEN 'Tersedia' THEN 0 ELSE 1 END, code")


def get_room(room_id: int):
    return q('SELECT * FROM rooms WHERE id=?', (room_id,), one=True)


def add_room(**f) -> None:
    f['code'] = f['code'].strip().upper()
    cols = [k for k in f if k in ROOM_FIELDS]
    run(f'INSERT INTO rooms({",".join(cols)}) VALUES({",".join("?" * len(cols))})', tuple(f[k] for k in cols))


def update_room(room_id: int, **f) -> None:
    cols = [k for k in f if k in ROOM_FIELDS]
    if cols:
        run(f'UPDATE rooms SET {", ".join(c + "=?" for c in cols)} WHERE id=?', (*(f[k] for k in cols), room_id))


def set_room_status(room_id: int, status: str) -> None:
    run('UPDATE rooms SET status=? WHERE id=?', (status, room_id))


def create_reservation(user_id: int, room_id: int, id_file: str, proof_file: str, start_date: str, months: int) -> str:
    r = get_room(room_id)
    if not r or r['status'] != 'Tersedia':
        raise ValueError('Maaf, kamar ini sudah tidak tersedia')
    if q("SELECT 1 FROM reservations WHERE user_id=? AND status='Menunggu'", (user_id,), one=True):
        raise ValueError('Anda masih punya reservasi yang menunggu ditinjau pemilik')
    u = get_user(user_id)
    if not u or u['role'] != 'applicant':
        raise ValueError('Pemesanan kamar hanya untuk akun calon penghuni')
    if months not in (3, 6, 12):
        raise ValueError('Lama sewa tidak valid')
    try:
        start = date.fromisoformat(start_date)
    except (TypeError, ValueError):
        raise ValueError('Tanggal mulai sewa tidak valid')
    if start < date.today():
        raise ValueError('Tanggal mulai sewa tidak boleh sebelum hari ini')
    if not id_file or not proof_file:
        raise ValueError('Dokumen identitas dan bukti transfer wajib diunggah')
    code = 'RSV-' + ''.join(random.choices(string.digits, k=5))
    run('INSERT INTO reservations(code,room_id,user_id,name,phone,id_file,proof_file,deposit,start_date,months,created_at) '
        'VALUES(?,?,?,?,?,?,?,?,?,?,?)',
        (code, room_id, user_id, u['full_name'], u['phone'], id_file, proof_file, r['price'], start_date, months, now()))
    set_room_status(room_id, 'Dipesan')
    notify_owner(f'Reservasi baru {code} dari {u["full_name"]} untuk kamar {r["code"]}. Tinjau dokumen dan bukti pembayaran.')
    return code


def reservations_of(user_id: int):
    return q('SELECT r.*, m.code room_code, m.type_name FROM reservations r JOIN rooms m ON m.id=r.room_id '
             'WHERE r.user_id=? ORDER BY r.id DESC', (user_id,))


def pending_reservations():
    return q("SELECT r.*, m.code room_code, m.type_name, m.price FROM reservations r JOIN rooms m ON m.id=r.room_id "
             "WHERE r.status='Menunggu' ORDER BY r.id")


def approve_reservation(rid: int) -> None:
    """Setujui: akun calon penghuni naik jadi penghuni, kontrak dibuat, deposit dicatat sebagai sewa bulan pertama."""
    r = q('SELECT r.*, m.price, m.code room_code FROM reservations r JOIN rooms m ON m.id=r.room_id WHERE r.id=?',
          (rid,), one=True)
    if not r or r['status'] != 'Menunggu':
        raise ValueError('Reservasi ini sudah diproses sebelumnya')
    start = date.fromisoformat(r['start_date'])
    cid = run('INSERT INTO contracts(tenant_id,room_id,start_date,end_date,rent) VALUES(?,?,?,?,?)',
              (r['user_id'], r['room_id'], r['start_date'], add_months(start, r['months']).isoformat(), r['price']))
    run("UPDATE users SET role='tenant' WHERE id=?", (r['user_id'],))
    desc = f"Sewa kamar {r['room_code']} - {BULAN[start.month - 1]} {start.year} (deposit booking)"
    today = date.today().isoformat()
    iid = run('INSERT INTO invoices(number,contract_id,tenant_id,type,description,amount,due_date,status,proof_file,created_at,paid_at) '
              "VALUES(?,?,?,?,?,?,?,'Lunas',?,?,?)",
              (f"INV-{cid:03d}-{start.strftime('%Y%m')}", cid, r['user_id'], 'Sewa', desc, r['deposit'],
               r['start_date'], r['proof_file'], now(), today))
    run('INSERT INTO ledger(date,kind,category,description,amount,invoice_id) VALUES(?,?,?,?,?,?)',
        (today, 'Pemasukan', 'Sewa', desc, r['deposit'], iid))
    run("UPDATE reservations SET status='Disetujui' WHERE id=?", (rid,))
    set_room_status(r['room_id'], 'Terisi')
    notify(r['user_id'], f'Reservasi {r["code"]} disetujui. Akun Anda kini penghuni kamar {r["room_code"]}.')
    run_billing_engine()


def reject_reservation(rid: int, reason: str) -> None:
    r = q('SELECT * FROM reservations WHERE id=?', (rid,), one=True)
    if not r or r['status'] != 'Menunggu':
        raise ValueError('Reservasi ini sudah diproses sebelumnya')
    run("UPDATE reservations SET status='Ditolak', reject_reason=? WHERE id=?", (reason, rid))
    set_room_status(r['room_id'], 'Tersedia')
    notify(r['user_id'], f'Reservasi {r["code"]} ditolak. Alasan: {reason}. Hubungi pemilik untuk pengembalian deposit.')


# ---------- siklus kontrak ----------
EXTEND_CHOICES = (1, 3, 6, 12)


def active_contracts():
    return q("SELECT c.*, m.code room_code, m.type_name, u.full_name, u.phone FROM contracts c "
             "JOIN rooms m ON m.id=c.room_id JOIN users u ON u.id=c.tenant_id "
             "WHERE c.status='Aktif' ORDER BY c.end_date")


def release_tenant_if_done(tenant_id: int) -> None:
    """Penghuni tanpa kontrak aktif dan tanpa tagihan tersisa kembali jadi calon penghuni (bisa memesan lagi)."""
    if (not q("SELECT 1 FROM contracts WHERE tenant_id=? AND status='Aktif'", (tenant_id,), one=True)
            and not q("SELECT 1 FROM invoices WHERE tenant_id=? AND status!='Lunas'", (tenant_id,), one=True)):
        run("UPDATE users SET role='applicant' WHERE id=? AND role='tenant'", (tenant_id,))


def _close_contract(c, why: str) -> None:
    run("UPDATE contracts SET status='Selesai' WHERE id=?", (c['id'],))
    run("UPDATE rooms SET status='Tersedia' WHERE id=? AND status='Terisi'", (c['room_id'],))
    release_tenant_if_done(c['tenant_id'])
    room = get_room(c['room_id'])['code']
    notify(c['tenant_id'], f'Kontrak kamar {room} {why}. Terima kasih telah tinggal bersama kami.')
    notify_owner(f'Kontrak kamar {room} {why}. Kamar kembali tersedia di katalog.')


def close_expired_contracts(today: date | None = None) -> int:
    today = today or date.today()
    n = 0
    for c in active_contracts():
        if date.fromisoformat(c['end_date']) < today:
            _close_contract(c, f'berakhir pada {tgl(c["end_date"])}')
            n += 1
    return n


def extend_contract(contract_id: int, months: int) -> None:
    c = q("SELECT * FROM contracts WHERE id=? AND status='Aktif'", (contract_id,), one=True)
    if not c:
        raise ValueError('Kontrak tidak aktif')
    if months not in EXTEND_CHOICES:
        raise ValueError('Lama perpanjangan tidak valid')
    new_end = add_months(date.fromisoformat(c['end_date']), months)
    run('UPDATE contracts SET end_date=? WHERE id=?', (new_end.isoformat(), contract_id))
    notify(c['tenant_id'], f'Kontrak Anda diperpanjang {months} bulan, kini berakhir {tgl(new_end)}.')
    run_billing_engine()


def end_contract(contract_id: int) -> None:
    c = q("SELECT * FROM contracts WHERE id=? AND status='Aktif'", (contract_id,), one=True)
    if not c:
        raise ValueError('Kontrak sudah tidak aktif')
    _close_contract(c, 'diakhiri oleh pemilik')


# ---------- 2. billing engine ----------
def run_billing_engine(today: date | None = None) -> dict:
    """Scheduler: tutup kontrak habis, terbitkan tagihan sewa otomatis, kirim pengingat."""
    today = today or date.today()
    created = reminded = 0
    for c in active_contracts():  # pengingat kontrak hampir habis (sekali saja)
        left = (date.fromisoformat(c['end_date']) - today).days
        if 0 <= left <= 30:
            msg = f'Pengingat kontrak: kamar {c["room_code"]} berakhir pada {tgl(c["end_date"])}. Hubungi pemilik bila ingin memperpanjang.'
            if not q('SELECT 1 FROM notifications WHERE user_id=? AND message=?', (c['tenant_id'], msg), one=True):
                notify(c['tenant_id'], msg)
                notify_owner(f'Kontrak {c["full_name"]} (kamar {c["room_code"]}) berakhir {tgl(c["end_date"])} ({left} hari lagi).')
                reminded += 1
    for c in q("SELECT c.*, m.code room_code FROM contracts c JOIN rooms m ON m.id=c.room_id "
               "WHERE c.status='Aktif'"):
        start, end = date.fromisoformat(c['start_date']), date.fromisoformat(c['end_date'])
        k = q("SELECT COUNT(*) n FROM invoices WHERE contract_id=? AND type='Sewa'", (c['id'],), one=True)['n']
        while True:
            due = add_months(start, k)
            if due >= end or (due - today).days > REMIND_DAYS:
                break
            number = f"INV-{c['id']:03d}-{due.strftime('%Y%m')}"
            desc = f"Sewa kamar {c['room_code']} - {BULAN[due.month - 1]} {due.year}"
            run('INSERT INTO invoices(number,contract_id,tenant_id,type,description,amount,due_date,created_at) '
                "VALUES(?,?,?,?,?,?,?,?)",
                (number, c['id'], c['tenant_id'], 'Sewa', desc, c['rent'], due.isoformat(), now()))
            notify(c['tenant_id'], f'Tagihan baru: {desc} sebesar {rp(c["rent"])}, jatuh tempo {tgl(due)}.')
            created += 1
            k += 1
    # Tutup kontrak yang habis SETELAH tagihan tertinggal terbit (mis. server sempat mati/tidur berminggu-minggu).
    closed = close_expired_contracts(today)
    for inv in q("SELECT * FROM invoices WHERE status IN ('Belum Dibayar','Ditolak')"):
        days = (date.fromisoformat(inv['due_date']) - today).days
        if days <= 3:
            label = 'terlambat %d hari' % -days if days < 0 else f'jatuh tempo {days} hari lagi'
            msg = f'Pengingat ({tgl(today)}): {inv["description"]} {label}.'
            if not q('SELECT 1 FROM notifications WHERE user_id=? AND message=?', (inv['tenant_id'], msg), one=True):
                notify(inv['tenant_id'], msg)
                reminded += 1
    return {'created': created, 'reminded': reminded, 'closed': closed}


# ---------- 3. pembayaran & verifikasi ----------
def tenant_contract(user_id: int):
    return q("SELECT c.*, m.code room_code FROM contracts c JOIN rooms m ON m.id=c.room_id "
             "WHERE c.tenant_id=? AND c.status='Aktif'", (user_id,), one=True)


def invoices_of(user_id: int):
    return q('SELECT * FROM invoices WHERE tenant_id=? ORDER BY due_date DESC, id DESC', (user_id,))


def submit_proof(invoice_id: int, filename: str) -> None:
    cur = q('SELECT status FROM invoices WHERE id=?', (invoice_id,), one=True)
    if not cur or cur['status'] not in ('Belum Dibayar', 'Ditolak'):
        raise ValueError('Tagihan ini tidak menerima bukti pembayaran (sudah dikirim atau lunas)')
    run("UPDATE invoices SET proof_file=?, status='Menunggu Verifikasi', reject_reason=NULL WHERE id=?",
        (filename, invoice_id))
    inv = q('SELECT * FROM invoices WHERE id=?', (invoice_id,), one=True)
    notify_owner(f'Bukti pembayaran masuk untuk {inv["number"]} ({inv["description"]}).')


def pending_invoices():
    return q("SELECT i.*, u.full_name FROM invoices i JOIN users u ON u.id=i.tenant_id "
             "WHERE i.status='Menunggu Verifikasi' ORDER BY i.id")


def all_invoices():
    return q("SELECT i.*, u.full_name FROM invoices i JOIN users u ON u.id=i.tenant_id "
             "ORDER BY i.due_date DESC, i.id DESC")


def verify_invoice(invoice_id: int, valid: bool, reason: str = '') -> None:
    inv = q('SELECT * FROM invoices WHERE id=?', (invoice_id,), one=True)
    if not inv or inv['status'] != 'Menunggu Verifikasi':
        raise ValueError('Bukti pembayaran ini sudah diverifikasi sebelumnya')
    if valid:
        today = date.today().isoformat()
        run("UPDATE invoices SET status='Lunas', paid_at=? WHERE id=?", (today, invoice_id))
        run('INSERT INTO ledger(date,kind,category,description,amount,invoice_id) VALUES(?,?,?,?,?,?)',
            (today, 'Pemasukan', 'Sewa' if inv['type'] == 'Sewa' else 'Layanan Tambahan',
             inv['description'], inv['amount'], invoice_id))
        notify(inv['tenant_id'], f'Pembayaran {inv["number"]} dikonfirmasi. Kuitansi tersedia di menu Riwayat.')
        if inv['ticket_id']:
            run("UPDATE tickets SET status='Diproses', updated_at=? WHERE id=?", (now(), inv['ticket_id']))
        release_tenant_if_done(inv['tenant_id'])
    else:
        run("UPDATE invoices SET status='Ditolak', reject_reason=? WHERE id=?", (reason, invoice_id))
        notify(inv['tenant_id'], f'Bukti pembayaran {inv["number"]} ditolak: {reason}. Silakan unggah ulang.')


def add_expense(category: str, description: str, amount: int, on: str) -> None:
    if not amount or amount <= 0:
        raise ValueError('Jumlah harus lebih dari 0')
    try:
        date.fromisoformat(on)
    except (TypeError, ValueError):
        raise ValueError('Tanggal tidak valid')
    run('INSERT INTO ledger(date,kind,category,description,amount) VALUES(?,?,?,?,?)',
        (on, 'Pengeluaran', category, description, amount))


def ledger_rows():
    return q('SELECT * FROM ledger ORDER BY date DESC, id DESC')


# ---------- 4. keluhan & permintaan ----------
TICKET_CATEGORIES = {
    'Keluhan': ['AC / Listrik', 'Air', 'Bangunan / Atap', 'Kebersihan', 'Tetangga / Kebisingan', 'Lainnya'],
    'Permintaan': ['Ganti galon', 'Tambah kunci', 'Laundry', 'Perpanjang kontrak', 'Lainnya'],
}


def _need(t, *states) -> None:
    if not t or t['status'] not in states:
        raise ValueError('Status ajuan sudah berubah. Muat ulang halaman.')


def create_ticket(user_id, ttype, category, description, photo) -> str:
    if ttype not in TICKET_CATEGORIES or category not in TICKET_CATEGORIES[ttype]:
        raise ValueError('Jenis atau kategori ajuan tidak valid')
    if not (description or '').strip():
        raise ValueError('Deskripsi wajib diisi')
    n = q('SELECT COUNT(*) n FROM tickets', one=True)['n'] + 1
    number = f'TKT-{n:04d}'
    run('INSERT INTO tickets(number,tenant_id,type,category,description,photo,created_at,updated_at) '
        'VALUES(?,?,?,?,?,?,?,?)', (number, user_id, ttype, category, description, photo, now(), now()))
    u = q('SELECT full_name FROM users WHERE id=?', (user_id,), one=True)
    notify_owner(f'Tiket baru {number} ({ttype}: {category}) dari {u["full_name"]}.')
    return number


def tickets_of(user_id: int):
    return q('SELECT * FROM tickets WHERE tenant_id=? ORDER BY id DESC', (user_id,))


def all_tickets():
    return q('SELECT t.*, u.full_name, c.room_code FROM tickets t JOIN users u ON u.id=t.tenant_id '
             'LEFT JOIN (SELECT c.tenant_id, m.code room_code FROM contracts c JOIN rooms m ON m.id=c.room_id '
             "WHERE c.status='Aktif') c ON c.tenant_id=t.tenant_id ORDER BY t.id DESC")


def _ticket(tid):
    return q('SELECT * FROM tickets WHERE id=?', (tid,), one=True)


def _set(tid: int, **fields) -> None:
    fields['updated_at'] = now()
    cols = ', '.join(f'{k}=?' for k in fields)
    run(f'UPDATE tickets SET {cols} WHERE id=?', (*fields.values(), tid))


def set_priority(tid: int, priority: str) -> None:
    _set(tid, priority=priority)


def accept_ticket(tid: int, cost: int | None = None) -> None:
    """Keluhan: langsung Diterima. Permintaan: pemilik menetapkan biaya (0 = gratis)."""
    t = _ticket(tid)
    _need(t, 'Baru')
    if t['type'] == 'Keluhan':
        _set(tid, status='Diterima')
        notify(t['tenant_id'], f'Tiket {t["number"]} diterima pemilik.')
    elif not cost:
        _set(tid, status='Diterima', cost=0)
        notify(t['tenant_id'], f'Tiket {t["number"]} diterima (gratis).')
    else:
        _set(tid, status='Menunggu Persetujuan Biaya', cost=cost)
        notify(t['tenant_id'], f'Penawaran untuk {t["number"]}: biaya {rp(cost)}. Setujui atau tolak di menu Tiket.')


def reject_ticket(tid: int, reason: str) -> None:
    t = _ticket(tid)
    _need(t, 'Baru')
    _set(tid, status='Ditolak', reject_reason=reason)
    notify(t['tenant_id'], f'Tiket {t["number"]} ditolak. Alasan: {reason}')


def start_ticket(tid: int, note: str = '') -> None:
    t = _ticket(tid)
    _need(t, 'Diterima', 'Dibuka Ulang')
    _set(tid, status='Diproses', schedule_note=note or None)
    notify(t['tenant_id'], f'Tiket {t["number"]} sedang diproses.' + (f' Catatan: {note}' if note else ''))


def finish_ticket(tid: int) -> None:
    t = _ticket(tid)
    _need(t, 'Diproses')
    _set(tid, status='Selesai')
    notify(t['tenant_id'], f'Tiket {t["number"]} selesai. Mohon konfirmasi dan beri rating.')


def respond_quote(tid: int, approve: bool) -> None:
    t = _ticket(tid)
    _need(t, 'Menunggu Persetujuan Biaya')
    if not approve:
        _set(tid, status='Dibatalkan')
        notify_owner(f'Penghuni menolak biaya tiket {t["number"]}. Tiket dibatalkan.')
        return
    c = tenant_contract(t['tenant_id'])
    run('INSERT INTO invoices(number,contract_id,tenant_id,type,description,amount,due_date,ticket_id,created_at) '
        'VALUES(?,?,?,?,?,?,?,?,?)',
        (f'INV-{t["number"]}', c['id'] if c else None, t['tenant_id'], 'Layanan Tambahan',
         f'{t["category"]} ({t["number"]})', t['cost'], (date.today() + timedelta(days=3)).isoformat(),
         tid, now()))
    _set(tid, status='Menunggu Pembayaran')
    notify(t['tenant_id'], f'Tagihan layanan tambahan untuk {t["number"]} terbit: {rp(t["cost"])}.')
    notify_owner(f'Penghuni menyetujui biaya tiket {t["number"]}. Tagihan layanan tambahan diterbitkan.')


def confirm_ticket(tid: int, rating: int) -> None:
    t = _ticket(tid)
    _need(t, 'Selesai')
    rating = max(1, min(5, int(rating)))
    _set(tid, status='Dikonfirmasi', rating=rating)
    notify_owner(f'Tiket {t["number"]} dikonfirmasi selesai (rating {rating}/5).')


def reopen_ticket(tid: int) -> None:
    t = _ticket(tid)
    _need(t, 'Selesai')
    _set(tid, status='Dibuka Ulang')
    notify_owner(f'Tiket {t["number"]} dibuka ulang: masalah belum beres.')


# ---------- laporan ----------
def dashboard() -> dict:
    total = q('SELECT COUNT(*) n FROM rooms', one=True)['n']
    filled = q("SELECT COUNT(*) n FROM rooms WHERE status='Terisi'", one=True)['n']
    month = date.today().strftime('%Y-%m')
    inc = q("SELECT COALESCE(SUM(amount),0) s FROM ledger WHERE kind='Pemasukan' AND date LIKE ?",
            (month + '%',), one=True)['s']
    exp = q("SELECT COALESCE(SUM(amount),0) s FROM ledger WHERE kind='Pengeluaran' AND date LIKE ?",
            (month + '%',), one=True)['s']
    total_inc = q("SELECT COALESCE(SUM(amount),0) s FROM ledger WHERE kind='Pemasukan'", one=True)['s']
    total_exp = q("SELECT COALESCE(SUM(amount),0) s FROM ledger WHERE kind='Pengeluaran'", one=True)['s']
    unpaid = q("SELECT COALESCE(SUM(amount),0) s FROM invoices WHERE status!='Lunas'", one=True)['s']
    by_month = defaultdict(lambda: [0, 0])
    for r in q('SELECT date, kind, amount FROM ledger'):
        by_month[r['date'][:7]][0 if r['kind'] == 'Pemasukan' else 1] += r['amount']
    months = sorted(by_month)[-6:]
    pending = {
        'reservasi': len(pending_reservations()),
        'pembayaran': len(pending_invoices()),
        'tiket': q("SELECT COUNT(*) n FROM tickets WHERE status IN ('Baru','Dibuka Ulang')", one=True)['n'],
    }
    exp_cat = [{'name': r['category'], 'value': r['s']} for r in
               q("SELECT category, SUM(amount) s FROM ledger WHERE kind='Pengeluaran' GROUP BY category")]
    overdue = q("SELECT i.*, u.full_name FROM invoices i JOIN users u ON u.id=i.tenant_id "
                "WHERE i.status!='Lunas' AND i.due_date < ? ORDER BY i.due_date", (date.today().isoformat(),))
    tk = q("SELECT COUNT(*) n, SUM(CASE WHEN status IN ('Dikonfirmasi','Selesai') THEN 1 ELSE 0 END) done, AVG(rating) avg FROM tickets", one=True)
    return {
        'total': total, 'filled': filled, 'occupancy': round(filled / total * 100) if total else 0,
        'income_month': inc, 'expense_month': exp, 'total_income': total_inc, 'total_expense': total_exp,
        'unpaid': unpaid, 'months': months, 'income': [by_month[m][0] for m in months],
        'expense': [by_month[m][1] for m in months], 'pending': pending, 'expense_cat': exp_cat,
        'overdue': overdue, 'tickets_total': tk['n'] or 0, 'tickets_done': int(tk['done'] or 0),
        'avg_rating': round(tk['avg'], 1) if tk['avg'] else None,
    }


def ledger_csv() -> str:
    def cell(v) -> str:  # cegah "CSV injection" (=, +, -, @ di awal sel dibaca Excel sebagai rumus)
        t = str(v or '')
        if t[:1] in ('=', '+', '-', '@', '\t', '\r'):
            t = "'" + t
        return '"' + t.replace('"', '""') + '"'

    lines = ['tanggal,jenis,kategori,keterangan,jumlah']
    for r in reversed(list(ledger_rows())):
        lines.append(f'{r["date"]},{cell(r["kind"])},{cell(r["category"])},{cell(r["description"])},{r["amount"]}')
    return '\n'.join(lines)


# ---------- data demo ----------
def seed_demo_history() -> None:
    """Isi riwayat awal agar dashboard tidak kosong saat pertama dijalankan."""
    run_billing_engine()
    invs = list(q("SELECT * FROM invoices WHERE type='Sewa' ORDER BY due_date"))
    for inv in invs[:-1]:
        run("UPDATE invoices SET status='Lunas', paid_at=? WHERE id=?", (inv['due_date'], inv['id']))
        run('INSERT INTO ledger(date,kind,category,description,amount,invoice_id) VALUES(?,?,?,?,?,?)',
            (inv['due_date'], 'Pemasukan', 'Sewa', inv['description'], inv['amount'], inv['id']))
    for i, (cat, desc, amt) in enumerate([('Listrik', 'Token listrik area umum', 450_000),
                                          ('Air', 'Tagihan PDAM', 180_000),
                                          ('Perbaikan', 'Servis pompa air', 250_000)]):
        d = date.today().replace(day=1) - timedelta(days=30 * (i % 2))
        add_expense(cat, desc, amt, d.isoformat())
