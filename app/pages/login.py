"""Satu pintu masuk untuk semua peran: Masuk / Daftar."""
from nicegui import app, ui

from .. import services as sv
from .. import shell
from .. import theme as th
from .. import ui_common as ux
from ..db import check_password, q


def start_session(u) -> None:
    app.storage.user.update(uid=u['id'], role=u['role'], name=u['full_name'], username=u['username'])
    ui.navigate.to(ux.HOME[u['role']])


def register() -> None:
    @ui.page('/login')
    def login(tab: str = 'masuk'):
        ux.theme()
        u = ux.current_user()
        if u:
            ui.navigate.to(ux.HOME[u['role']])
            return

        def do_login():
            uname = (user.value or '').strip().lower()
            wait = sv.login_wait(uname)
            if wait:
                ui.notify(f'Terlalu banyak percobaan salah. Coba lagi dalam {wait // 60 + 1} menit.', type='warning')
                return
            row = q('SELECT * FROM users WHERE username=?', (uname,), one=True)
            if not row or not check_password(pw.value or '', row['password_hash']):
                sv.login_failed(uname)
                ui.notify('Username atau password salah', type='negative')
                return
            sv.login_ok(uname)
            start_session(row)

        def do_register():
            if (r_pw.value or '') != (r_pw2.value or ''):
                ui.notify('Konfirmasi password tidak sama', type='negative')
                return
            try:
                uid = sv.register_user(r_user.value or '', r_pw.value or '', r_name.value or '', r_phone.value or '')
            except ValueError as e:
                ui.notify(str(e), type='negative')
                return
            start_session(sv.get_user(uid))

        with ui.element('div').classes('kf-login'):
            with ui.element('div').classes('kf-login-art'):
                ui.html(f'<a href="/" class="kf-logo">{th.logo_html(44)}</a>')
                with ui.column().classes('gap-3'):
                    ui.label('Kelola kost dalam satu pintu.').classes('kf-title').style('font-size:2.4rem;line-height:1.1')
                    ui.label('Tagihan otomatis, pembayaran tercatat, keluhan tertangani, dan laporan selalu siap.').classes('kf-sub')
                    ui.html(th.scene_svg())
                ui.label(sv.setting('address')).classes('kf-muted')

            with ui.column().classes('items-center justify-center p-6 gap-3 w-full'):
                with ui.row().classes('w-full max-w-[400px] justify-end'):
                    shell.theme_menu()
                with ui.card().classes('kf-card p-6 gap-2 w-full max-w-[400px]'):
                    ui.label('Selamat datang').classes('kf-title text-2xl')
                    with ui.tabs().classes('w-full') as tabs:
                        t_in = ui.tab('Masuk')
                        t_up = ui.tab('Daftar')
                    with ui.tab_panels(tabs, value=t_up if tab == 'daftar' else t_in).classes('w-full bg-transparent'):
                        with ui.tab_panel(t_in).classes('p-0 flex flex-col gap-2 pt-3'):
                            user = ui.input('Username').props('outlined').classes('w-full')
                            pw = ui.input('Password', password=True, password_toggle_button=True).props('outlined').classes('w-full')
                            user.on('keydown.enter', do_login)
                            pw.on('keydown.enter', do_login)
                            ui.button('Masuk', on_click=do_login).props('unelevated color=primary no-caps size=lg').classes('w-full')
                            ui.label('Belum punya akun? Buka tab Daftar.').classes('kf-muted')
                            ui.separator()
                            ui.label('Akun demo').classes('kf-muted')
                            for label, un, p in [('Pemilik', 'pemilik', 'pemilik123'), ('Penghuni', 'penghuni', 'penghuni123')]:
                                def fill(un=un, p=p):
                                    user.set_value(un)
                                    pw.set_value(p)
                                    do_login()
                                ui.button(f'{label}  ({un} / {p})', on_click=fill).props('flat no-caps align=left').classes('w-full')
                        with ui.tab_panel(t_up).classes('p-0 flex flex-col gap-1 pt-3'):
                            r_name = ui.input('Nama lengkap').props('outlined dense').classes('w-full')
                            r_phone = ui.input('No. WhatsApp').props('outlined dense').classes('w-full')
                            r_user = ui.input('Username (huruf/angka, min. 4)').props('outlined dense').classes('w-full')
                            r_pw = ui.input('Password (min. 6)', password=True, password_toggle_button=True).props('outlined dense').classes('w-full')
                            r_pw2 = ui.input('Ulangi password', password=True).props('outlined dense').classes('w-full')
                            r_pw2.on('keydown.enter', do_register)
                            ui.button('Buat akun', on_click=do_register).props('unelevated color=primary no-caps size=lg').classes('w-full')
                            ui.label('Akun baru berstatus calon penghuni. Setelah reservasi disetujui, akun yang sama otomatis menjadi akun penghuni.').classes('kf-muted')
