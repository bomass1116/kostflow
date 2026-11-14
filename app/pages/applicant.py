"""Dashboard calon penghuni: pilih kamar, ajukan reservasi + bukti pembayaran, pantau status."""
from datetime import date

from nicegui import app, ui

from .. import services as sv
from .. import shell
from .. import ui_common as ux
from ..ui_rooms import room_card


def register() -> None:
    @ui.page('/applicant')
    def applicant_page():
        ux.theme()
        if not ux.require_role('applicant'):
            return
        u = ux.current_user()
        uid = u['id']

        @ui.refreshable
        def catalog_view():
            rooms = sv.rooms()
            free = [r for r in rooms if r['status'] == 'Tersedia']
            ux.hero(f'Halo, {u["full_name"].split()[0]}', 'Temukan kamar Anda',
                    'Pilih kamar, unggah KTP dan bukti deposit, lalu tunggu persetujuan pemilik.',
                    [dict(icon='meeting_room', label='Kamar tersedia', value=len(free), hint=f'dari {len(rooms)} kamar')]
                    + ([dict(icon='payments', label='Mulai dari', value=min(r['price'] for r in free), fmt='rp', hint='/ bulan')] if free else []))
            with ui.row().classes('w-full gap-4'):
                for r in rooms:
                    room_card(r, on_book=booking_dialog)

        @ui.refreshable
        def my_reservations():
            rows = sv.reservations_of(uid)
            if not rows:
                ui.label('Belum ada reservasi. Pilih kamar di tab Pilih kamar.').classes('kf-muted')
            for r in rows:
                with ui.card().classes('kf-card p-4 w-full gap-1'):
                    with ui.row().classes('items-center justify-between w-full'):
                        ui.label(f'{r["code"]} · {r["type_name"]} kamar {r["room_code"]}').classes('kf-title')
                        ux.badge(r['status'])
                    ui.label(f'Mulai {sv.tgl(r["start_date"])} · {r["months"]} bulan · deposit {sv.rp(r["deposit"])} · diajukan {r["created_at"]}').classes('text-sm')
                    if r['status'] == 'Menunggu':
                        ui.label('Pemilik sedang meninjau dokumen identitas dan bukti pembayaran Anda.').classes('kf-muted')
                    elif r['status'] == 'Ditolak':
                        ui.label(f'Ditolak. Alasan: {r["reject_reason"]}').classes('text-negative text-sm')

        def booking_dialog(room):
            state = {'id': None, 'proof': None}
            with ui.dialog() as d, ui.card().classes('w-[460px] max-w-full gap-2'):
                ui.label(f'Pesan {room["type_name"]} · kamar {room["code"]}').classes('kf-title text-lg')
                ui.label(f'{sv.rp(room["price"])} / bulan').classes('kf-muted')
                start = ui.input('Tanggal mulai sewa', value=date.today().isoformat()).props('type=date').classes('w-full')
                months = ui.select({3: '3 bulan', 6: '6 bulan', 12: '12 bulan'}, value=6, label='Lama sewa').classes('w-full')
                ui.label('1. Dokumen identitas (KTP/KTM)').classes('font-semibold mt-1')
                info1 = ui.label('Belum ada file').classes('kf-muted')

                async def up_id(e):
                    f = await ux.save_upload(e)
                    if f:
                        state['id'] = f
                        info1.set_text('Terunggah ✓')

                ui.upload(on_upload=up_id, auto_upload=True, max_file_size=5_000_000, label='Pilih file').props(
                    'accept=".jpg,.jpeg,.png,.pdf" flat bordered').classes('w-full')
                ui.label(f'2. Bayar deposit {sv.rp(room["price"])} (dihitung sebagai sewa bulan pertama)').classes('font-semibold mt-1')
                ui.label(f'Transfer ke: {sv.setting("bank_info")}').classes('text-sm')
                info2 = ui.label('Belum ada bukti transfer').classes('kf-muted')

                async def up_proof(e):
                    f = await ux.save_upload(e)
                    if f:
                        state['proof'] = f
                        info2.set_text('Terunggah ✓')

                ui.upload(on_upload=up_proof, auto_upload=True, max_file_size=5_000_000, label='Unggah bukti transfer').props(
                    'accept=".jpg,.jpeg,.png,.pdf" flat bordered').classes('w-full')

                def submit():
                    if not state['id'] or not state['proof']:
                        ui.notify('Unggah dokumen identitas dan bukti transfer dulu', type='warning')
                        return
                    try:
                        code = sv.create_reservation(uid, room['id'], state['id'], state['proof'], start.value, months.value)
                    except ValueError as e:
                        ui.notify(str(e), type='negative')
                        return
                    d.close()
                    catalog_view.refresh()
                    my_reservations.refresh()
                    ref['select']('mine')
                    ui.notify(f'Reservasi {code} terkirim. Tunggu persetujuan pemilik.', type='positive')

                with ui.row().classes('justify-end w-full'):
                    ui.button('Batal', on_click=d.close).props('flat')
                    ui.button('Kirim reservasi', on_click=submit)
            d.open()

        def side(select):
            n = len([r for r in sv.reservations_of(uid) if r['status'] == 'Menunggu'])
            ui.label('Status reservasi').classes('kf-muted')
            ui.label(f'{n} menunggu ditinjau' if n else 'Belum ada yang menunggu').classes('kf-title')
            ui.button('Lihat reservasi', on_click=lambda: select('mine')).props('flat no-caps dense')

        ref = {}
        ref['select'] = shell.app_shell(
            u, [('pick', 'Pilih kamar', 'meeting_room'), ('mine', 'Reservasi saya', 'assignment')],
            {'pick': catalog_view, 'mine': my_reservations}, side_card=side)

        pending = app.storage.user.pop('pending_room', None)
        if pending:
            room = sv.get_room(pending)
            if room and room['status'] == 'Tersedia':
                booking_dialog(room)
