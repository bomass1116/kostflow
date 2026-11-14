from datetime import date

from nicegui import app, ui

from .. import services as sv
from .. import shell
from .. import ui_common as ux
from ..ui_rooms import room_card


def register() -> None:
    @ui.page('/owner')
    def owner_page():
        ux.theme()
        if not ux.require_role('owner'):
            return
        u = ux.current_user()

        def refresh_all():
            dashboard_view.refresh()
            reservations_view.refresh()
            payments_view.refresh()
            tickets_view.refresh()
            rooms_view.refresh()
            ledger_view.refresh()
            contracts_view.refresh()

        # ---------- laporan ----------
        @ui.refreshable
        def dashboard_view():
            d = sv.dashboard()
            pal = ux.th.palette()
            ux.hero(f'Selamat datang, {u["full_name"].split(" (")[0]}', 'Laporan Kost',
                    'Ringkasan okupansi, arus kas, tunggakan, dan layanan penghuni dalam satu layar.',
                    [dict(icon='apartment', label='Okupansi', value=d['occupancy'], fmt='pct', hint=f'{d["filled"]} dari {d["total"]} kamar terisi'),
                     dict(icon='payments', label='Pemasukan bulan ini', value=d['income_month'], fmt='rp', hint=f'Pengeluaran {sv.rp(d["expense_month"])}'),
                     dict(icon='account_balance_wallet', label='Laba bersih (total)', value=d['total_income'] - d['total_expense'], fmt='rp',
                          hint=f'Omzet {sv.rp(d["total_income"])}'),
                     dict(icon='warning_amber', label='Belum lunas', value=d['unpaid'], fmt='rp', hint=f'{len(d["overdue"])} lewat jatuh tempo')])
            p = d['pending']
            if any(p.values()):
                with ui.card().classes('kf-card p-4 w-full'):
                    ui.label('Perlu tindakan').classes('kf-title')
                    ui.label(f'{p["reservasi"]} reservasi menunggu · {p["pembayaran"]} bukti pembayaran menunggu verifikasi · '
                             f'{p["tiket"]} ajuan baru/dibuka ulang').classes('text-sm')
            with ui.row().classes('w-full gap-3 items-stretch'):
                with ui.card().classes('kf-card p-4 flex-[2] min-w-[300px]'):
                    ui.label('Arus kas 6 bulan terakhir').classes('kf-title')
                    if d['months']:
                        ui.echart({
                            'tooltip': {'trigger': 'axis'}, 'textStyle': {'color': pal['muted']},
                            'legend': {'data': ['Pemasukan', 'Pengeluaran'], 'top': 0, 'textStyle': {'color': pal['muted']}},
                            'grid': {'left': 70, 'right': 20, 'top': 40, 'bottom': 30},
                            'xAxis': {'type': 'category', 'data': d['months'], 'axisLabel': {'color': pal['muted']}},
                            'yAxis': {'type': 'value', 'axisLabel': {'color': pal['muted']}, 'splitLine': {'lineStyle': {'color': pal['border']}}},
                            'series': [
                                {'name': 'Pemasukan', 'type': 'bar', 'data': d['income'], 'itemStyle': {'color': pal['accent'], 'borderRadius': [6, 6, 0, 0]}},
                                {'name': 'Pengeluaran', 'type': 'bar', 'data': d['expense'], 'itemStyle': {'color': pal['accent2'], 'borderRadius': [6, 6, 0, 0]}},
                            ]}).classes('w-full h-64')
                    else:
                        ui.label('Belum ada transaksi tercatat.').classes('kf-muted')
                with ui.card().classes('kf-card p-4 flex-1 min-w-[260px]'):
                    ui.label('Pengeluaran per kategori').classes('kf-title')
                    if d['expense_cat']:
                        ui.echart({
                            'tooltip': {'trigger': 'item'}, 'legend': {'bottom': 0, 'textStyle': {'color': pal['muted']}},
                            'series': [{'type': 'pie', 'radius': ['42%', '70%'], 'center': ['50%', '44%'], 'data': d['expense_cat'],
                                        'label': {'show': False}}],
                            'color': [pal['accent'], pal['accent2'], '#7a5c3b', '#4C9BD6', '#C9503D']}).classes('w-full h-64')
                    else:
                        ui.label('Belum ada pengeluaran.').classes('kf-muted')
            with ui.card().classes('kf-card p-4 w-full gap-1'):
                ui.label('Tunggakan').classes('kf-title')
                if not d['overdue']:
                    ui.label('Tidak ada tagihan yang lewat jatuh tempo.').classes('kf-muted')
                for i in d['overdue']:
                    days = (date.today() - date.fromisoformat(i['due_date'])).days
                    ui.label(f'{i["full_name"]} · {i["description"]} · {sv.rp(i["amount"])} · terlambat {days} hari').classes('text-sm')
            with ui.card().classes('kf-card p-4 w-full gap-1'):
                ui.label('Layanan penghuni').classes('kf-title')
                rating = f'{d["avg_rating"]} / 5' if d['avg_rating'] else 'belum ada rating'
                ui.label(f'{d["tickets_total"]} ajuan masuk · {d["tickets_done"]} selesai · rata-rata kepuasan {rating}').classes('text-sm')

        # ---------- 1. reservasi ----------
        @ui.refreshable
        def reservations_view():
            rows = sv.pending_reservations()
            if not rows:
                ui.label('Tidak ada reservasi yang menunggu.').classes('kf-muted')
            for r in rows:
                with ui.card().classes('kf-card kf-reveal p-4 w-full gap-1'):
                    with ui.row().classes('items-center justify-between w-full'):
                        ui.label(f'{r["code"]} · {r["name"]}').classes('kf-title')
                        ux.badge('Dipesan')
                    ui.label(f'{r["type_name"]} kamar {r["room_code"]} · mulai {sv.tgl(r["start_date"])} · {r["months"]} bulan · WA {r["phone"]}').classes('text-sm')
                    ui.label(f'Deposit dibayar: {sv.rp(r["deposit"])}').classes('text-sm')
                    with ui.row().classes('gap-4'):
                        ux.file_link(r['id_file'], 'Lihat dokumen identitas')
                        ux.file_link(r['proof_file'], 'Lihat bukti transfer deposit')
                    with ui.row():
                        ui.button('Setujui', on_click=lambda r=r: approve(r)).props('no-caps')
                        ui.button('Tolak', on_click=lambda r=r: ux.confirm_dialog(
                            f'Tolak reservasi {r["code"]}?', lambda reason: (ux.guard(sv.reject_reservation, r['id'], reason), refresh_all()),
                            input_label='Alasan penolakan', yes_label='Tolak')).props('outline color=negative no-caps')

        def approve(r):
            if ux.guard(sv.approve_reservation, r['id']):
                ui.notify(f'{r["name"]} kini terdaftar sebagai penghuni kamar {r["room_code"]}', type='positive')
            refresh_all()

        # ---------- 2 & 3. billing & pembayaran ----------
        @ui.refreshable
        def payments_view():
            pend = sv.pending_invoices()
            ui.label('Menunggu verifikasi').classes('kf-title')
            if not pend:
                ui.label('Tidak ada bukti pembayaran yang menunggu.').classes('kf-muted')
            for i in pend:
                with ui.card().classes('kf-card p-4 w-full gap-1'):
                    with ui.row().classes('items-center justify-between w-full'):
                        ui.label(f'{i["number"]} · {i["full_name"]}').classes('kf-title')
                        ux.badge(i['status'])
                    ui.label(f'{i["description"]} · {sv.rp(i["amount"])} · {i["type"]}').classes('text-sm')
                    ux.file_link(i['proof_file'], 'Lihat bukti transfer')
                    with ui.row():
                        ui.button('Bukti valid', on_click=lambda i=i: (ux.guard(sv.verify_invoice, i['id'], True), refresh_all())).props('no-caps')
                        ui.button('Tolak bukti', on_click=lambda i=i: ux.confirm_dialog(
                            f'Tolak bukti {i["number"]}?', lambda reason: (ux.guard(sv.verify_invoice, i['id'], False, reason), refresh_all()),
                            input_label='Alasan penolakan', yes_label='Tolak')).props('outline color=negative no-caps')
            ui.label('Semua tagihan').classes('kf-title mt-2')
            cols = [
                {'name': 'number', 'label': 'No.', 'field': 'number', 'align': 'left'},
                {'name': 'who', 'label': 'Penghuni', 'field': 'who', 'align': 'left'},
                {'name': 'desc', 'label': 'Keterangan', 'field': 'desc', 'align': 'left'},
                {'name': 'amount', 'label': 'Jumlah', 'field': 'amount', 'align': 'right'},
                {'name': 'due', 'label': 'Jatuh tempo', 'field': 'due', 'align': 'left'},
                {'name': 'status', 'label': 'Status', 'field': 'status', 'align': 'left'},
            ]
            data = [{'number': i['number'], 'who': i['full_name'], 'desc': i['description'],
                     'amount': sv.rp(i['amount']), 'due': sv.tgl(i['due_date']), 'status': i['status']}
                    for i in sv.all_invoices()]
            ui.table(columns=cols, rows=data, row_key='number').classes('w-full').props('flat bordered dense')

        def run_engine():
            res = sv.run_billing_engine()
            ui.notify(f'Billing engine: {res["created"]} tagihan terbit, {res["reminded"]} pengingat terkirim, '
                      f'{res["closed"]} kontrak berakhir ditutup', type='positive')
            refresh_all()

        # ---------- 4. tiket ----------
        @ui.refreshable
        def tickets_view():
            rows = sv.all_tickets()
            if not rows:
                ui.label('Belum ada ajuan dari penghuni.').classes('kf-muted')
            for t in rows:
                with ui.card().classes('kf-card p-4 w-full gap-1'):
                    with ui.row().classes('items-center justify-between w-full'):
                        ui.label(f'{t["number"]} · {t["category"]}').classes('kf-title')
                        ux.badge(t['status'])
                    ui.label(f'{t["type"]} · {t["full_name"]}' + (f' (kamar {t["room_code"]})' if t['room_code'] else '') + f' · {t["created_at"]}').classes('kf-muted')
                    ui.label(t['description']).classes('text-sm')
                    ux.file_link(t['photo'], 'Lihat foto')
                    if t['cost'] is not None and t['type'] == 'Permintaan':
                        ui.label(f'Biaya: {sv.rp(t["cost"])}').classes('text-sm')
                    if t['schedule_note']:
                        ui.label(f'Catatan jadwal: {t["schedule_note"]}').classes('text-sm')
                    if t['rating']:
                        ui.label(f'Rating: {"★" * t["rating"]}').classes('text-sm')
                    owner_ticket_actions(t)

        def owner_ticket_actions(t):
            st = t['status']
            if st in ('Baru', 'Dibuka Ulang'):
                prio = ui.select(['Rendah', 'Sedang', 'Tinggi'], value=t['priority'] or 'Sedang', label='Prioritas').classes('w-40')
                cost = ui.number('Biaya (Rp, 0 = gratis)', value=0, min=0, step=10000).classes('w-52') if t['type'] == 'Permintaan' else None

                def accept():
                    if st == 'Dibuka Ulang':
                        ok = ux.guard(sv.start_ticket, t['id'], 'Dikerjakan ulang')
                    else:
                        ok = ux.guard(sv.accept_ticket, t['id'], int(cost.value or 0) if cost else None)
                    if ok:
                        sv.set_priority(t['id'], prio.value)
                    refresh_all()

                with ui.row():
                    ui.button('Terima' if st == 'Baru' else 'Kerjakan ulang', on_click=accept).props('no-caps')
                    if st == 'Baru':
                        ui.button('Tolak', on_click=lambda: ux.confirm_dialog(
                            f'Tolak ajuan {t["number"]}?', lambda reason: (ux.guard(sv.reject_ticket, t['id'], reason), refresh_all()),
                            input_label='Alasan penolakan', yes_label='Tolak')).props('outline color=negative no-caps')
            elif st == 'Diterima':
                note = ui.input('Catatan jadwal (terlihat penghuni, opsional)').classes('w-full max-w-md')
                ui.button('Tandai Diproses', on_click=lambda: (ux.guard(sv.start_ticket, t['id'], note.value or ''), refresh_all())).props('no-caps')
            elif st == 'Diproses':
                ui.button('Tandai Selesai', on_click=lambda: (ux.guard(sv.finish_ticket, t['id']), refresh_all())).props('no-caps')
            elif st == 'Menunggu Persetujuan Biaya':
                ui.label('Menunggu penghuni menyetujui biaya.').classes('kf-muted')
            elif st == 'Menunggu Pembayaran':
                ui.label('Menunggu penghuni membayar tagihan layanan tambahan.').classes('kf-muted')

        # ---------- kamar & tampilan katalog ----------
        @ui.refreshable
        def rooms_view():
            with ui.row().classes('w-full gap-4'):
                for r in sv.rooms():
                    room_card(r, on_edit=lambda r=r: room_dialog(r))

        def room_dialog(r=None):
            new = r is None
            state = {'photo': None}
            with ui.dialog() as d, ui.card().classes('w-[480px] max-w-full gap-1'):
                ui.label('Tambah kamar' if new else f'Edit kamar {r["code"]}').classes('kf-title text-lg')
                code = ui.input('Kode kamar (mis. D1)', value='' if new else r['code']).classes('w-full')
                if not new:
                    code.props('readonly')
                typ = ui.input('Tipe kamar (mis. Deluxe)', value='Standard' if new else r['type_name']).classes('w-full')
                desc = ui.textarea('Deskripsi (tampil di katalog)', value='' if new else r['description']).classes('w-full')
                fac = ui.input('Fasilitas (pisahkan dengan koma)', value='' if new else r['facilities']).classes('w-full')
                with ui.row().classes('w-full no-wrap'):
                    floor = ui.number('Lantai', value=1 if new else r['floor'], min=1, precision=0).classes('flex-1')
                    size = ui.input('Ukuran', value='3x4 m' if new else r['size']).classes('flex-1')
                price = ui.number('Harga / bulan (Rp)', value=1000000 if new else r['price'], min=0, step=50000).classes('w-full')
                status = ui.select(['Tersedia', 'Dipesan', 'Terisi'], value='Tersedia' if new else r['status'],
                                   label='Status (SOLD bila bukan Tersedia)').classes('w-full')
                info = ui.label('Foto kamar: memakai ilustrasi bawaan' if new or not r['photo'] else 'Foto kamar: sudah ada (unggah untuk mengganti)').classes('kf-muted')

                async def on_up(e):
                    f = await ux.save_upload(e, images_only=True)
                    if f:
                        state['photo'] = f
                        info.set_text('Foto baru terunggah ✓')

                ui.upload(on_upload=on_up, auto_upload=True, max_file_size=5_000_000, label='Unggah foto kamar').props(
                    'accept=".jpg,.jpeg,.png,.webp" flat bordered').classes('w-full')

                def save():
                    if not (code.value or '').strip() or not (typ.value or '').strip():
                        ui.notify('Kode dan tipe kamar wajib diisi', type='warning')
                        return
                    fields = dict(type_name=typ.value.strip(), description=desc.value or '', facilities=fac.value or '',
                                  floor=int(floor.value or 1), size=size.value or '', price=int(price.value or 0),
                                  status=status.value)
                    if state['photo']:
                        fields['photo'] = state['photo']
                    if new:
                        try:
                            sv.add_room(code=code.value, **fields)
                        except Exception:
                            ui.notify('Kode kamar sudah dipakai', type='negative')
                            return
                    else:
                        sv.update_room(r['id'], **fields)
                    d.close()
                    ui.notify('Tersimpan', type='positive')
                    refresh_all()

                with ui.row().classes('justify-end w-full'):
                    ui.button('Batal', on_click=d.close).props('flat')
                    ui.button('Simpan', on_click=save)
            d.open()

        def profile_dialog():
            with ui.dialog() as d, ui.card().classes('w-[480px] max-w-full gap-1'):
                ui.label('Profil kost (tampil di halaman depan)').classes('kf-title text-lg')
                fields = {k: ui.input(label, value=sv.setting(k)).classes('w-full') for k, label in [
                    ('kost_name', 'Nama kost'), ('tagline', 'Deskripsi singkat'), ('address', 'Alamat'),
                    ('contact', 'Kontak'), ('bank_info', 'Rekening pembayaran (tampil saat booking)')]}

                def save():
                    for k, f in fields.items():
                        sv.set_setting(k, f.value or '')
                    d.close()
                    ui.notify('Profil kost tersimpan', type='positive')

                with ui.row().classes('justify-end w-full'):
                    ui.button('Batal', on_click=d.close).props('flat')
                    ui.button('Simpan', on_click=save)
            d.open()

        # ---------- buku kas ----------
        @ui.refreshable
        def ledger_view():
            cols = [
                {'name': 'date', 'label': 'Tanggal', 'field': 'date', 'align': 'left'},
                {'name': 'kind', 'label': 'Jenis', 'field': 'kind', 'align': 'left'},
                {'name': 'category', 'label': 'Kategori', 'field': 'category', 'align': 'left'},
                {'name': 'desc', 'label': 'Keterangan', 'field': 'desc', 'align': 'left'},
                {'name': 'amount', 'label': 'Jumlah', 'field': 'amount', 'align': 'right'},
            ]
            data = [{'id': r['id'], 'date': sv.tgl(r['date']), 'kind': r['kind'], 'category': r['category'],
                     'desc': r['description'], 'amount': ('+ ' if r['kind'] == 'Pemasukan' else '- ') + sv.rp(r['amount'])}
                    for r in sv.ledger_rows()]
            ui.table(columns=cols, rows=data, row_key='id').classes('w-full').props('flat bordered dense')

        def add_expense_dialog():
            with ui.dialog() as d, ui.card().classes('w-96 max-w-full'):
                ui.label('Catat pengeluaran').classes('kf-title text-lg')
                cat = ui.select(['Listrik', 'Air', 'Perbaikan', 'Kebersihan', 'Lainnya'], value='Listrik', label='Kategori').classes('w-full')
                desc = ui.input('Keterangan').classes('w-full')
                amt = ui.number('Jumlah (Rp)', value=0, min=0, step=10000).classes('w-full')
                on = ui.input('Tanggal', value=date.today().isoformat()).props('type=date').classes('w-full')

                def save():
                    if not ux.guard(sv.add_expense, cat.value, desc.value or cat.value, int(amt.value or 0), on.value):
                        return
                    d.close()
                    refresh_all()

                with ui.row().classes('justify-end w-full'):
                    ui.button('Batal', on_click=d.close).props('flat')
                    ui.button('Simpan', on_click=save)
            d.open()

        # ---------- kontrak penghuni ----------
        @ui.refreshable
        def contracts_view():
            rows = sv.active_contracts()
            if not rows:
                ui.label('Belum ada kontrak aktif.').classes('kf-muted')
            for c in rows:
                left = (date.fromisoformat(c['end_date']) - date.today()).days
                with ui.card().classes('kf-card p-4 w-full gap-1'):
                    ui.label(f'{c["full_name"]} · kamar {c["room_code"]}').classes('kf-title')
                    ui.label(f'{sv.rp(c["rent"])} / bulan · {sv.tgl(c["start_date"])} s.d. {sv.tgl(c["end_date"])} · '
                             f'sisa {left} hari · WA {c["phone"]}').classes('text-sm')
                    if left <= 30:
                        ui.label('Kontrak segera berakhir. Perpanjang atau biarkan berakhir otomatis.').classes('text-sm kf-atext')
                    with ui.row().classes('items-center gap-2 mt-1'):
                        months = ui.select({m: f'+{m} bulan' for m in sv.EXTEND_CHOICES}, value=6).props('dense outlined').classes('w-32')
                        ui.button('Perpanjang', icon='event_repeat', on_click=lambda c=c, m=months: extend(c, m.value)).props('unelevated color=primary no-caps')
                        ui.button('Akhiri kontrak', on_click=lambda c=c: ux.confirm_dialog(
                            f'Akhiri kontrak {c["full_name"]} (kamar {c["room_code"]}) sekarang? Kamar akan kembali tersedia.',
                            lambda _=None: (ux.guard(sv.end_contract, c['id']), refresh_all()), yes_label='Akhiri')).props('outline color=negative no-caps')

        def extend(c, months):
            if ux.guard(sv.extend_contract, c['id'], int(months)):
                ui.notify(f'Kontrak {c["full_name"]} diperpanjang {months} bulan', type='positive')
            refresh_all()

        # ---------- layout ----------
        def pay_panel():
            ui.button('Jalankan billing engine', icon='bolt', on_click=run_engine).props('unelevated color=primary no-caps').classes('self-start')
            ui.label('Sistem juga menjalankannya otomatis setiap jam.').classes('kf-muted')
            payments_view()

        def rooms_panel():
            ui.label('Tampilan ini sama dengan katalog yang dilihat calon penghuni. Kamar bukan Tersedia tampil abu-abu dengan label SOLD.').classes('kf-muted')
            with ui.row():
                ui.button('Tambah kamar', icon='add', on_click=lambda: room_dialog()).props('unelevated color=primary no-caps')
                ui.button('Edit profil kost', icon='storefront', on_click=profile_dialog).props('outline color=primary no-caps')
            rooms_view()

        def ledger_panel():
            with ui.row():
                ui.button('Catat pengeluaran', icon='add', on_click=add_expense_dialog).props('unelevated color=primary no-caps')
                ui.button('Unduh CSV', icon='download', on_click=lambda: ui.download.content(
                    sv.ledger_csv(), 'buku-kas.csv', 'text/csv')).props('outline color=primary no-caps')
            ledger_view()

        def side(select):
            p = sv.dashboard()['pending']
            ui.label('Perlu tindakan').classes('kf-muted')
            ui.label(f'{p["reservasi"] + p["pembayaran"] + p["tiket"]} item').classes('kf-title')
            for key, label, n in [('res', 'reservasi', p['reservasi']), ('pay', 'pembayaran', p['pembayaran']), ('tick', 'ajuan', p['tiket'])]:
                ui.button(f'{n} {label}', on_click=lambda key=key: select(key)).props('flat no-caps dense align=left').classes('w-full')

        shell.app_shell(
            u, [('home', 'Laporan', 'insights'), ('res', 'Reservasi', 'how_to_reg'), ('pay', 'Pembayaran', 'payments'),
                ('tick', 'Ajuan', 'build'), ('contracts', 'Kontrak', 'badge'), ('rooms', 'Kamar', 'meeting_room'),
                ('ledger', 'Buku kas', 'menu_book')],
            {'home': dashboard_view, 'res': reservations_view, 'pay': pay_panel, 'tick': tickets_view,
             'contracts': contracts_view, 'rooms': rooms_panel, 'ledger': ledger_panel}, side_card=side, on_theme=dashboard_view.refresh)
