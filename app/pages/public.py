"""Halaman publik '/' : katalog kamar ala hotel dengan filter interaktif. Bisa dilihat tanpa akun."""
from nicegui import app, ui

from .. import services as sv
from .. import shell
from .. import theme as th
from .. import ui_common as ux
from ..ui_rooms import room_card


def book(room) -> None:
    u = ux.current_user()
    if u and u['role'] != 'applicant':
        ui.notify('Pemesanan kamar hanya untuk akun calon penghuni.', type='info')
        return
    app.storage.user['pending_room'] = room['id']
    if u:
        ui.navigate.to('/applicant')
    else:
        ui.notify('Daftar atau masuk dulu untuk memesan kamar', type='info')
        ui.navigate.to('/login?tab=daftar')


def register() -> None:
    @ui.page('/')
    def index():
        ux.theme()
        shell.public_header()
        rooms = sv.rooms()
        free = [r for r in rooms if r['status'] == 'Tersedia']
        types = ['Semua'] + sorted({r['type_name'] for r in rooms if r['type_name']})
        flt = {'type': 'Semua', 'free': False}

        # ---- hero ----
        with ui.element('div').classes('w-full').style('padding:28px 20px 8px'):
            with ui.element('div').classes('kf-hero max-w-6xl mx-auto'):
                with ui.element('div').classes('kf-hero-grid'):
                    with ui.column().classes('gap-3'):
                        ui.label(sv.setting('address')).classes('kf-muted')
                        ui.label(sv.setting('kost_name')).classes('kf-title').style('font-size:3rem;line-height:1.05')
                        ui.label(sv.setting('tagline')).classes('kf-sub')
                        with ui.row().classes('gap-2'):
                            ui.button('Lihat kamar', icon='meeting_room', on_click=lambda: ui.run_javascript(
                                "document.getElementById('kamar').scrollIntoView({behavior:'smooth'})")).props('unelevated color=primary no-caps')
                            ui.button('Daftar sekarang', on_click=lambda: ui.navigate.to('/login?tab=daftar')).props('outline color=primary no-caps')
                        with ui.element('div').classes('kf-tiles mt-2'):
                            ux.tile('meeting_room', 'Kamar tersedia', len(free), hint=f'dari {len(rooms)} kamar')
                            if free:
                                ux.tile('payments', 'Mulai dari', min(r['price'] for r in free), 'rp', '/ bulan')
                    ui.html(th.scene_svg()).classes('kf-hero-art')

        # ---- katalog ----
        with ui.column().classes('w-full max-w-6xl mx-auto px-5 pt-6 gap-3'):
            ui.html('<div id="kamar"></div>')
            ui.label('Pilihan kamar').classes('kf-title text-2xl kf-reveal')
            ui.label('Lihat dulu tanpa akun. Klik foto kamar untuk detail. Akun hanya dibutuhkan saat memesan.').classes('kf-muted')

            @ui.refreshable
            def filters():
                with ui.row().classes('gap-2 items-center'):
                    for t in types:
                        ui.button(t, on_click=lambda t=t: (flt.update(type=t), filters.refresh(), grid.refresh())).props(
                            'flat no-caps').classes('kf-filter' + (' kf-filter-on' if flt['type'] == t else ''))
                    ui.switch('Hanya yang tersedia', value=flt['free'],
                              on_change=lambda e: (flt.update(free=e.value), grid.refresh()))

            @ui.refreshable
            def grid():
                shown = [r for r in rooms if (flt['type'] == 'Semua' or r['type_name'] == flt['type'])
                         and (not flt['free'] or r['status'] == 'Tersedia')]
                if not shown:
                    ui.label('Tidak ada kamar yang cocok dengan filter ini.').classes('kf-muted')
                with ui.row().classes('w-full gap-4'):
                    for r in shown:
                        room_card(r, on_book=book)

            filters()
            grid()

        # ---- cara memesan ----
        with ui.column().classes('w-full max-w-6xl mx-auto px-5 pt-10 gap-3'):
            ui.html('<div id="cara"></div>')
            ui.label('Cara memesan').classes('kf-title text-2xl kf-reveal')
            with ui.row().classes('w-full gap-4'):
                for i, (icon, title, text) in enumerate([
                        ('person_add', 'Buat akun', 'Daftar dengan nama dan nomor WhatsApp. Gratis dan cepat.'),
                        ('upload_file', 'Ajukan reservasi', 'Pilih kamar, unggah KTP/KTM, lalu transfer deposit sebagai sewa bulan pertama.'),
                        ('verified', 'Disetujui pemilik', 'Setelah diverifikasi, akun Anda otomatis menjadi akun penghuni dan tagihan bulanan terbit sendiri.')], 1):
                    with ui.element('div').classes('kf-step kf-reveal kf-hover flex-1 min-w-[240px]'):
                        with ui.element('div').classes('kf-ico'):
                            ui.icon(icon)
                        ui.label(f'{i}. {title}').classes('kf-title text-lg')
                        ui.label(text).classes('kf-muted')

        with ui.row().classes('w-full justify-center py-10'):
            ui.html(th.logo_html(26)).classes('opacity-70')
            ui.label(f'· {sv.setting("contact")}').classes('kf-muted')
