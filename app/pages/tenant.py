from nicegui import app, ui

from datetime import date

from .. import services as sv
from .. import shell
from .. import ui_common as ux


def register() -> None:
    @ui.page('/tenant')
    def tenant_page():
        ux.theme()
        if not ux.require_role('tenant'):
            return
        uid = app.storage.user['uid']
        c = sv.tenant_contract(uid)
        u = ux.current_user()

        @ui.refreshable
        def invoices_view():
            rows = [i for i in sv.invoices_of(uid) if i['status'] != 'Lunas']
            c = sv.tenant_contract(uid)
            open_t = len([t for t in sv.tickets_of(uid) if t['status'] not in ('Dikonfirmasi', 'Dibatalkan', 'Ditolak')])
            left = (date.fromisoformat(c['end_date']) - date.today()).days if c else 0
            tiles = [dict(icon='payments', label='Sewa per bulan', value=c['rent'] if c else 0, fmt='rp',
                          hint=f'Kamar {c["room_code"]}' if c else ''),
                     dict(icon='receipt_long', label='Tagihan aktif', value=len(rows),
                          hint='✓ Semua lunas' if not rows else f'{sv.rp(sum(i["amount"] for i in rows))} belum lunas'),
                     dict(icon='event', label='Sisa kontrak', value=max(left, 0), hint=f'hari · berakhir {sv.tgl(c["end_date"])}' if c else ''),
                     dict(icon='build', label='Ajuan berjalan', value=open_t)]
            ux.hero(f'Halo, {u["full_name"].split()[0]}', 'Beranda Penghuni',
                    'Pantau tagihan, bayar tepat waktu, dan sampaikan keluhan atau permintaan Anda.', tiles)
            ui.label('Tagihan yang perlu dibayar').classes('kf-title text-lg')
            if not rows:
                ui.label('Tidak ada tagihan aktif. Semua sudah lunas.').classes('kf-muted')
            for i in rows:
                with ui.card().classes('kf-card kf-reveal p-4 w-full gap-1'):
                    with ui.row().classes('items-center justify-between w-full'):
                        ui.label(i['description']).classes('kf-title text-lg')
                        ux.badge(i['status'])
                    ui.label(f'{sv.rp(i["amount"])} · jatuh tempo {sv.tgl(i["due_date"])} · {i["type"]}').classes('text-sm')
                    if i['status'] == 'Ditolak':
                        ui.label(f'Bukti ditolak: {i["reject_reason"]}. Unggah ulang bukti yang benar.').classes('text-negative text-sm')
                    if i['status'] == 'Menunggu Verifikasi':
                        ui.label('Bukti sudah dikirim, menunggu verifikasi pemilik.').classes('kf-muted')
                    else:
                        async def on_up(e, inv=i):
                            fname = await ux.save_upload(e)
                            if not fname:
                                return
                            if ux.guard(sv.submit_proof, inv['id'], fname):
                                ui.notify('Bukti pembayaran terkirim', type='positive')
                            refresh_all()

                        ui.upload(on_upload=on_up, auto_upload=True, max_file_size=5_000_000,
                                  label='Unggah bukti transfer').props('accept=".jpg,.jpeg,.png,.pdf" flat bordered').classes('w-full max-w-sm')

        @ui.refreshable
        def history_view():
            rows = [i for i in sv.invoices_of(uid) if i['status'] == 'Lunas']
            if not rows:
                ui.label('Belum ada pembayaran lunas.').classes('kf-muted')
            for i in rows:
                with ui.card().classes('kf-card p-3 w-full'):
                    with ui.row().classes('items-center justify-between w-full'):
                        with ui.column().classes('gap-0'):
                            ui.label(i['description']).classes('font-semibold')
                            ui.label(f'Lunas {sv.tgl(i["paid_at"])} · {sv.rp(i["amount"])}').classes('kf-muted')
                        ui.button('Kuitansi', icon='receipt_long', on_click=lambda i=i: receipt(i)).props('flat no-caps')

        def receipt(i):
            with ui.dialog() as d, ui.card().classes('w-96 max-w-full gap-1'):
                ui.label('Kuitansi Pembayaran').classes('kf-title text-xl')
                ui.label(f'No. {i["number"]}').classes('kf-muted')
                ui.separator()
                for k, v in [('Penghuni', app.storage.user['name']), ('Untuk', i['description']),
                             ('Jumlah', sv.rp(i['amount'])), ('Tanggal lunas', sv.tgl(i['paid_at'])),
                             ('Status', 'LUNAS')]:
                    with ui.row().classes('justify-between w-full'):
                        ui.label(k).classes('kf-muted')
                        ui.label(v).classes('font-semibold')
                ui.button('Tutup', on_click=d.close).props('flat')
            d.open()

        @ui.refreshable
        def tickets_view():
            rows = sv.tickets_of(uid)
            if not rows:
                ui.label('Belum ada ajuan. Buat ajuan untuk melapor keluhan atau meminta layanan.').classes('kf-muted')
            for t in rows:
                with ui.card().classes('kf-card p-4 w-full gap-1'):
                    with ui.row().classes('items-center justify-between w-full'):
                        ui.label(f'{t["number"]} · {t["category"]}').classes('kf-title')
                        ux.badge(t['status'])
                    ui.label(f'{t["type"]} · dibuat {t["created_at"]}' + (f' · prioritas {t["priority"]}' if t['priority'] else '')).classes('kf-muted')
                    ui.label(t['description']).classes('text-sm')
                    ux.file_link(t['photo'], 'Lihat foto')
                    if t['schedule_note']:
                        ui.label(f'Catatan jadwal: {t["schedule_note"]}').classes('text-sm')
                    if t['status'] == 'Ditolak':
                        ui.label(f'Alasan penolakan: {t["reject_reason"]}').classes('text-negative text-sm')
                    if t['rating']:
                        ui.label(f'Rating Anda: {"★" * t["rating"]}').classes('text-sm')
                    ticket_actions(t)

        def ticket_actions(t):
            if t['status'] == 'Menunggu Persetujuan Biaya':
                ui.label(f'Pemilik menawarkan biaya {sv.rp(t["cost"])}. Setujui?').classes('font-semibold')
                with ui.row():
                    ui.button('Setujui', on_click=lambda: act(sv.respond_quote, t['id'], True))
                    ui.button('Tolak', on_click=lambda: act(sv.respond_quote, t['id'], False)).props('outline color=negative')
            elif t['status'] == 'Menunggu Pembayaran':
                ui.label('Tagihan layanan tambahan sudah terbit. Bayar lewat tab Tagihan.').classes('text-sm')
            elif t['status'] == 'Selesai':
                rating = ui.slider(min=1, max=5, step=1, value=5).props('label-always markers').classes('max-w-xs')
                with ui.row():
                    ui.button('Konfirmasi selesai', on_click=lambda: act(sv.confirm_ticket, t['id'], int(rating.value)))
                    ui.button('Belum beres, buka ulang', on_click=lambda: act(sv.reopen_ticket, t['id'])).props('outline color=negative')

        def act(fn, *args):
            ux.guard(fn, *args)
            refresh_all()

        def refresh_all():
            invoices_view.refresh()
            history_view.refresh()
            tickets_view.refresh()

        def new_ticket():
            state = {'photo': None}
            with ui.dialog() as d, ui.card().classes('w-[440px] max-w-full gap-2'):
                ui.label('Buat ajuan').classes('kf-title text-lg')
                ttype = ui.toggle(['Keluhan', 'Permintaan'], value='Keluhan')
                cat = ui.select(sv.TICKET_CATEGORIES['Keluhan'], value=sv.TICKET_CATEGORIES['Keluhan'][0], label='Kategori').classes('w-full')

                def on_type(e):
                    opts = sv.TICKET_CATEGORIES[ttype.value]
                    cat.set_options(opts, value=opts[0])

                ttype.on_value_change(on_type)
                desc = ui.textarea('Deskripsi').classes('w-full')
                info = ui.label('Foto (opsional)').classes('kf-muted')

                async def on_up(e):
                    f = await ux.save_upload(e, images_only=True)
                    if f:
                        state['photo'] = f
                        info.set_text('Foto terunggah ✓')

                ui.upload(on_upload=on_up, auto_upload=True, max_file_size=5_000_000, label='Unggah foto').props('accept=".jpg,.jpeg,.png,.webp" flat bordered').classes('w-full')

                def submit():
                    if not (desc.value or '').strip():
                        ui.notify('Deskripsi wajib diisi', type='warning')
                        return
                    try:
                        n = sv.create_ticket(uid, ttype.value, cat.value, desc.value.strip(), state['photo'])
                    except ValueError as err:
                        ui.notify(str(err), type='warning')
                        return
                    d.close()
                    ui.notify(f'Ajuan {n} dibuat', type='positive')
                    refresh_all()

                with ui.row().classes('justify-end w-full'):
                    ui.button('Batal', on_click=d.close).props('flat')
                    ui.button('Kirim ajuan', on_click=submit)
            d.open()

        def tickets_panel():
            ui.button('Buat ajuan baru', icon='add', on_click=new_ticket).props('unelevated color=primary no-caps').classes('self-start')
            tickets_view()

        def side(select):
            c2 = sv.tenant_contract(uid)
            ui.label('Kontrak Anda').classes('kf-muted')
            if c2:
                total = (date.fromisoformat(c2['end_date']) - date.fromisoformat(c2['start_date'])).days or 1
                used = (date.today() - date.fromisoformat(c2['start_date'])).days
                ui.label(f'Kamar {c2["room_code"]}').classes('kf-title')
                ui.linear_progress(value=max(0, min(1, used / total)), show_value=False).props('rounded color=primary')
                ui.label(f'Berakhir {sv.tgl(c2["end_date"])}').classes('kf-muted')

        shell.app_shell(
            u, [('home', 'Beranda & tagihan', 'home'), ('tickets', 'Ajuan', 'build'), ('history', 'Riwayat & kuitansi', 'receipt_long')],
            {'home': invoices_view, 'tickets': tickets_panel, 'history': history_view}, side_card=side)
