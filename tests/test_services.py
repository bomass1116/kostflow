"""Tes logika bisnis KostFlow. Jalankan dari folder proyek:  python -m unittest discover -s tests -v
Memakai database sementara, tidak menyentuh data/ asli."""
import os
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

os.environ['KOSTFLOW_DATA'] = tempfile.mkdtemp(prefix='kostflow-test-')
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import services as sv  # noqa: E402
from app.db import init_db, q, run  # noqa: E402

init_db()


def new_applicant(name: str) -> int:
    return sv.register_user(name, 'rahasia1', name.title(), '0800' + name)


def free_room() -> int:
    return sv.rooms('Tersedia')[0]['id']


def book(uid: int, months: int = 6, start: date | None = None) -> str:
    return sv.create_reservation(uid, free_room(), 'ktp.png', 'bukti.png', (start or date.today()).isoformat(), months)


class Reservation(unittest.TestCase):
    def test_approve_creates_contract_invoice_and_ledger(self):
        uid = new_applicant('budi1')
        book(uid)
        rid = sv.pending_reservations()[-1]['id']
        sv.approve_reservation(rid)
        self.assertEqual(sv.get_user(uid)['role'], 'tenant')
        c = sv.tenant_contract(uid)
        self.assertIsNotNone(c)
        self.assertEqual(q('SELECT status FROM rooms WHERE id=?', (c['room_id'],), one=True)['status'], 'Terisi')
        self.assertTrue(q("SELECT 1 FROM invoices WHERE tenant_id=? AND status='Lunas'", (uid,), one=True))
        self.assertTrue(q("SELECT 1 FROM ledger WHERE kind='Pemasukan' AND description LIKE ?", (f'%{c["room_code"]}%',), one=True))

    def test_double_approve_and_reject_are_blocked(self):
        uid = new_applicant('citra')
        book(uid)
        rid = sv.pending_reservations()[-1]['id']
        sv.approve_reservation(rid)
        before = q('SELECT COUNT(*) n FROM contracts', one=True)['n']
        with self.assertRaises(ValueError):
            sv.approve_reservation(rid)
        with self.assertRaises(ValueError):
            sv.reject_reservation(rid, 'x')
        self.assertEqual(q('SELECT COUNT(*) n FROM contracts', one=True)['n'], before)

    def test_reject_frees_room(self):
        uid = new_applicant('dodi1')
        book(uid)
        r = sv.pending_reservations()[-1]
        sv.reject_reservation(r['id'], 'dokumen buram')
        self.assertEqual(sv.get_room(r['room_id'])['status'], 'Tersedia')

    def test_validation(self):
        uid = new_applicant('erik1')
        with self.assertRaises(ValueError):
            book(uid, months=5)
        with self.assertRaises(ValueError):
            book(uid, start=date.today() - timedelta(days=1))
        with self.assertRaises(ValueError):
            sv.create_reservation(uid, free_room(), 'ktp.png', 'b.png', 'bukan-tanggal', 6)
        with self.assertRaises(ValueError):
            sv.create_reservation(uid, free_room(), '', 'b.png', date.today().isoformat(), 6)

    def test_tenant_cannot_book(self):
        with self.assertRaises(ValueError):
            sv.create_reservation(2, free_room(), 'a.png', 'b.png', date.today().isoformat(), 6)  # akun demo penghuni


class Billing(unittest.TestCase):
    def test_invoice_issued_h7_and_not_duplicated(self):
        uid = new_applicant('fani1')
        book(uid, start=date.today())
        sv.approve_reservation(sv.pending_reservations()[-1]['id'])
        cid = sv.tenant_contract(uid)['id']
        sv.run_billing_engine(date.today() + timedelta(days=24))   # bulan ke-2 jatuh tempo +31 hari -> H-7
        n1 = q("SELECT COUNT(*) n FROM invoices WHERE contract_id=? AND type='Sewa'", (cid,), one=True)['n']
        sv.run_billing_engine(date.today() + timedelta(days=24))
        n2 = q("SELECT COUNT(*) n FROM invoices WHERE contract_id=? AND type='Sewa'", (cid,), one=True)['n']
        self.assertEqual(n1, 2)
        self.assertEqual(n1, n2)

    def test_payment_flow_and_double_verify(self):
        uid = new_applicant('gina1')
        book(uid, start=date.today())
        sv.approve_reservation(sv.pending_reservations()[-1]['id'])
        sv.run_billing_engine(date.today() + timedelta(days=30))
        inv = q("SELECT * FROM invoices WHERE tenant_id=? AND status='Belum Dibayar'", (uid,), one=True)
        sv.submit_proof(inv['id'], 'bukti.png')
        with self.assertRaises(ValueError):            # bukti kedua saat menunggu verifikasi
            sv.submit_proof(inv['id'], 'lagi.png')
        sv.verify_invoice(inv['id'], True)
        with self.assertRaises(ValueError):            # verifikasi ganda tidak boleh dobel masuk kas
            sv.verify_invoice(inv['id'], True)
        self.assertEqual(q('SELECT COUNT(*) n FROM ledger WHERE invoice_id=?', (inv['id'],), one=True)['n'], 1)

    def test_rejected_proof_can_be_resubmitted(self):
        uid = new_applicant('hana1')
        book(uid, start=date.today())
        sv.approve_reservation(sv.pending_reservations()[-1]['id'])
        sv.run_billing_engine(date.today() + timedelta(days=30))
        inv = q("SELECT * FROM invoices WHERE tenant_id=? AND status='Belum Dibayar'", (uid,), one=True)
        sv.submit_proof(inv['id'], 'a.png')
        sv.verify_invoice(inv['id'], False, 'buram')
        sv.submit_proof(inv['id'], 'b.png')
        self.assertEqual(q('SELECT status FROM invoices WHERE id=?', (inv['id'],), one=True)['status'], 'Menunggu Verifikasi')


class ContractLifecycle(unittest.TestCase):
    def _tenant(self, name, months=3):
        uid = new_applicant(name)
        book(uid, months=months, start=date.today())
        sv.approve_reservation(sv.pending_reservations()[-1]['id'])
        return uid, sv.tenant_contract(uid)

    def test_expired_contract_closes_and_frees_room(self):
        uid, c = self._tenant('ivan1')
        sv.run_billing_engine(date.today() + timedelta(days=120))
        sv.run_billing_engine(date.today() + timedelta(days=120))   # idempotent
        self.assertEqual(q('SELECT status FROM contracts WHERE id=?', (c['id'],), one=True)['status'], 'Selesai')
        self.assertEqual(sv.get_room(c['room_id'])['status'], 'Tersedia')

    def test_tenant_with_unpaid_invoice_keeps_access_until_settled(self):
        uid, c = self._tenant('joko1')
        sv.run_billing_engine(date.today() + timedelta(days=120))
        self.assertEqual(sv.get_user(uid)['role'], 'tenant')       # masih ada tagihan
        for inv in q("SELECT * FROM invoices WHERE tenant_id=? AND status!='Lunas'", (uid,)):
            sv.submit_proof(inv['id'], 'x.png')
            sv.verify_invoice(inv['id'], True)
        self.assertEqual(sv.get_user(uid)['role'], 'applicant')    # lunas semua -> boleh memesan lagi

    def test_extend_and_end(self):
        uid, c = self._tenant('kiki1')
        old_end = date.fromisoformat(c['end_date'])
        sv.extend_contract(c['id'], 6)
        self.assertEqual(sv.tenant_contract(uid)['end_date'], sv.add_months(old_end, 6).isoformat())
        with self.assertRaises(ValueError):
            sv.extend_contract(c['id'], 7)
        sv.end_contract(c['id'])
        with self.assertRaises(ValueError):
            sv.end_contract(c['id'])
        self.assertEqual(sv.get_room(c['room_id'])['status'], 'Tersedia')


class Tickets(unittest.TestCase):
    def test_service_request_with_quote(self):
        n = sv.create_ticket(2, 'Permintaan', 'Laundry', 'cuci 5kg', None)
        t = q('SELECT * FROM tickets WHERE number=?', (n,), one=True)
        sv.accept_ticket(t['id'], 50_000)
        sv.respond_quote(t['id'], True)
        with self.assertRaises(ValueError):                         # tidak boleh setuju dua kali
            sv.respond_quote(t['id'], True)
        self.assertEqual(q("SELECT COUNT(*) n FROM invoices WHERE ticket_id=?", (t['id'],), one=True)['n'], 1)

    def test_complaint_flow_and_guards(self):
        n = sv.create_ticket(2, 'Keluhan', 'Air', 'keran bocor', None)
        t = q('SELECT * FROM tickets WHERE number=?', (n,), one=True)
        with self.assertRaises(ValueError):
            sv.finish_ticket(t['id'])                               # belum diproses
        sv.accept_ticket(t['id'])
        sv.start_ticket(t['id'], 'besok pagi')
        sv.finish_ticket(t['id'])
        sv.confirm_ticket(t['id'], 99)                              # rating dibatasi 1..5
        self.assertEqual(q('SELECT rating FROM tickets WHERE id=?', (t['id'],), one=True)['rating'], 5)
        with self.assertRaises(ValueError):
            sv.reopen_ticket(t['id'])

    def test_invalid_ticket_rejected(self):
        with self.assertRaises(ValueError):
            sv.create_ticket(2, 'Keluhan', 'KategoriNgawur', 'x', None)
        with self.assertRaises(ValueError):
            sv.create_ticket(2, 'Keluhan', 'Air', '   ', None)


class AccountsAndFiles(unittest.TestCase):
    def test_change_password(self):
        uid = new_applicant('lina1')
        with self.assertRaises(ValueError):
            sv.change_password(uid, 'salah', 'barubaru')
        with self.assertRaises(ValueError):
            sv.change_password(uid, 'rahasia1', '123')
        sv.change_password(uid, 'rahasia1', 'barubaru')
        from app.db import check_password
        self.assertTrue(check_password('barubaru', sv.get_user(uid)['password_hash']))

    def test_store_and_load_file(self):
        from app.db import load_file, store_file
        store_file('dddddddddddd.png', b'\x89PNG\r\n\x1a\nabc')
        self.assertEqual(load_file('dddddddddddd.png'), b'\x89PNG\r\n\x1a\nabc')
        self.assertIsNone(load_file('eeeeeeeeeeee.png'))

    def test_file_permissions(self):
        a, b = new_applicant('mira1'), new_applicant('nino1')
        run('INSERT INTO reservations(code,room_id,user_id,name,id_file,proof_file,created_at) VALUES(?,?,?,?,?,?,?)',
            ('RSV-T1', 1, a, 'Mira', 'aaaaaaaaaaaa.png', 'bbbbbbbbbbbb.png', 'x'))
        ua, ub, owner = sv.get_user(a), sv.get_user(b), sv.get_user(1)
        self.assertTrue(sv.can_view_file(ua, 'aaaaaaaaaaaa.png'))
        self.assertTrue(sv.can_view_file(owner, 'aaaaaaaaaaaa.png'))
        self.assertFalse(sv.can_view_file(ub, 'aaaaaaaaaaaa.png'))   # pengguna lain
        self.assertFalse(sv.can_view_file(None, 'aaaaaaaaaaaa.png'))  # tanpa login
        run("UPDATE rooms SET photo='cccccccccccc.jpg' WHERE id=1")
        self.assertTrue(sv.can_view_file(None, 'cccccccccccc.jpg'))   # foto kamar publik

    def test_login_throttle(self):
        for _ in range(sv.LOGIN_MAX_FAILS):
            sv.login_failed('penyerang')
        self.assertGreater(sv.login_wait('penyerang'), 0)
        sv.login_ok('penyerang')
        self.assertEqual(sv.login_wait('penyerang'), 0)

    def test_csv_injection_and_expense_validation(self):
        sv.add_expense('Lainnya', '=HYPERLINK("http://x")', 1000, date.today().isoformat())
        self.assertIn("\"'=HYPERLINK", sv.ledger_csv())
        with self.assertRaises(ValueError):
            sv.add_expense('Air', 'x', 0, date.today().isoformat())
        with self.assertRaises(ValueError):
            sv.add_expense('Air', 'x', 100, 'kemarin')


if __name__ == '__main__':
    unittest.main()
