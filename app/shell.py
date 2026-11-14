"""Kerangka aplikasi: sidebar, bilah atas (cari, tema, notifikasi, avatar), dan header publik."""
from nicegui import ui

from . import services as sv
from . import theme as th
from . import ui_common as ux


def theme_menu(on_change=None) -> None:
    """Tombol palet: pilih tema warna + mode terang/gelap."""
    def choose(key=None, mode=None):
        th.set_theme(key, mode)
        refresh_menu.refresh()
        if on_change:
            on_change()

    with ui.button(icon='palette').props('flat round').tooltip('Ganti tema'):
        with ui.menu().props('auto-close=false'):
            @ui.refreshable
            def refresh_menu():
                cur, mode = th.current()
                with ui.column().classes('p-3 gap-2 w-[230px]'):
                    ui.label('Tema warna').classes('kf-title')
                    for key, t in th.THEMES.items():
                        with ui.row().classes('items-center gap-3 cursor-pointer w-full rounded-lg p-1 no-wrap').style(
                                'background:color-mix(in srgb,var(--accent) 16%,transparent)' if key == cur else '').on(
                                'click', lambda key=key: choose(key=key)):
                            ui.html(f'<span style="display:inline-flex"><span style="width:20px;height:20px;border-radius:50%;background:{t["accent"]}"></span>'
                                    f'<span style="width:20px;height:20px;border-radius:50%;background:{t["accent2"]};margin-left:-7px"></span></span>')
                            ui.label(t['name']).classes('text-sm')
                            if key == cur:
                                ui.icon('check').classes('ml-auto kf-atext')
                    ui.separator()
                    with ui.row().classes('items-center justify-between w-full no-wrap'):
                        ui.label('Mode gelap').classes('text-sm')
                        ui.switch(value=mode == 'dark', on_change=lambda e: choose(mode='dark' if e.value else 'light'))
            refresh_menu()


def notif_button(uid: int) -> None:
    with ui.button(icon='notifications').props('flat round') as bell:
        badge_el = ui.badge().props('floating color=secondary text-color=dark')

    def update_badge():
        n = sv.unread_count(uid)
        badge_el.set_text(str(n))
        badge_el.set_visibility(n > 0)

    def open_notifs():
        with ui.dialog() as d, ui.card().classes('w-96 max-w-full'):
            ui.label('Notifikasi').classes('kf-title text-lg')
            rows = sv.notifications(uid)
            if not rows:
                ui.label('Belum ada notifikasi.').classes('kf-muted')
            for n in rows:
                with ui.column().classes('gap-0 w-full pb-1').style('border-bottom:1px solid var(--border)'):
                    ui.label(n['message']).classes('text-sm')
                    ui.label(n['created_at']).classes('kf-muted')
            ui.button('Tutup', on_click=d.close).props('flat')
        sv.mark_read(uid)
        update_badge()
        d.open()

    update_badge()
    bell.on_click(open_notifs)
    ui.timer(15, update_badge)


def public_header() -> None:
    """Header halaman publik: logo, tautan, tema, masuk/daftar."""
    u = ux.current_user()
    with ui.header().classes('kf-top items-center justify-between px-4 py-2'):
        ui.html(f'<a href="/" class="kf-logo">{th.logo_html(34)}</a>')
        with ui.row().classes('items-center gap-1'):
            ui.button('Kamar', on_click=lambda: ui.run_javascript("document.getElementById('kamar').scrollIntoView({behavior:'smooth'})")).props('flat no-caps').classes('gt-xs')
            ui.button('Cara memesan', on_click=lambda: ui.run_javascript("document.getElementById('cara').scrollIntoView({behavior:'smooth'})")).props('flat no-caps').classes('gt-xs')
            theme_menu()
            if u:
                ui.button(f'Dashboard {ux.ROLE_LABEL[u["role"]]}', on_click=lambda: ui.navigate.to(ux.HOME[u['role']])).props('unelevated color=primary no-caps')
            else:
                ui.button('Masuk', on_click=lambda: ui.navigate.to('/login')).props('flat no-caps')
                ui.button('Daftar', on_click=lambda: ui.navigate.to('/login?tab=daftar')).props('unelevated color=primary no-caps')


def app_shell(user, nav: list[tuple[str, str, str]], builders: dict, side_card=None, on_theme=None):
    """Sidebar + top bar + panel konten.

    nav      : [(kunci, label, ikon)]
    builders : {kunci: fungsi yang menggambar isi panel}
    Mengembalikan fungsi select(kunci) untuk berpindah panel dari kode lain.
    """
    labels = {k: l for k, l, _ in nav}
    buttons: dict = {}
    state = {'key': nav[0][0]}

    def select(key: str) -> None:
        state['key'] = key
        panels.set_value(key)
        crumb.set_text(labels[key])
        for k, b in buttons.items():
            b.classes(add='kf-nav-active' if k == key else '', remove='' if k == key else 'kf-nav-active')

    # ---- sidebar ----
    # value=None -> "show-if-above": terbuka otomatis di laptop/desktop, tertutup (overlay) di HP.
    drawer = ui.left_drawer(bordered=False).props('width=264 breakpoint=900 show-if-above')

    async def on_nav(key: str) -> None:
        select(key)
        # Di layar HP, tutup menu setelah memilih agar isi halaman langsung terlihat.
        if await ui.run_javascript('window.innerWidth') < 900:
            drawer.hide()

    with drawer:
        with ui.column().classes('w-full h-full gap-1 no-wrap'):
            ui.html(f'<a href="/" class="kf-logo" style="padding:6px 8px 18px">{th.logo_html(36)}</a>')
            for key, label, icon in nav:
                buttons[key] = ui.button(label, icon=icon, on_click=lambda key=key: on_nav(key)).props(
                    'flat no-caps align=left').classes('kf-nav')
            ui.space()
            if side_card:
                with ui.element('div').classes('kf-side-card'):
                    side_card(on_nav)

    # ---- bilah atas ----
    with ui.header().classes('kf-top items-center justify-between px-3 py-1'):
        with ui.row().classes('items-center gap-2'):
            ui.button(icon='menu', on_click=drawer.toggle).props('flat round')
            crumb = ui.label(nav[0][1]).classes('kf-title text-lg')
        with ui.row().classes('items-center gap-1'):
            search = ui.input(placeholder='Cari menu…').props('dense outlined rounded').classes('kf-search')
            with search.add_slot('prepend'):
                ui.icon('search')

            def go_search():
                term = (search.value or '').strip().lower()
                if not term:
                    return
                for k, l, _ in nav:
                    if term in l.lower() or term in k.lower():
                        select(k)
                        search.set_value('')
                        return
                ui.notify('Menu tidak ditemukan', type='warning')

            search.on('keydown.enter', go_search)
            theme_menu(on_theme)
            notif_button(user['id'])
            with ui.button(icon='account_circle').props('flat round'):
                with ui.menu():
                    with ui.column().classes('p-3 gap-0'):
                        ui.label(user['full_name']).classes('font-semibold')
                        ui.label(ux.ROLE_LABEL[user['role']]).classes('kf-muted')
                    ui.separator()
                    ui.menu_item('Beranda katalog', on_click=lambda: ui.navigate.to('/'))
                    ui.menu_item('Ganti password', on_click=lambda: ux.password_dialog(user['id']))
                    ui.menu_item('Keluar', on_click=ux.logout)

    # ---- konten ----
    with ui.column().classes('w-full max-w-6xl mx-auto p-4 gap-4'):
        panels = ui.tab_panels(value=nav[0][0]).props('animated transition-prev=fade transition-next=fade').classes('w-full bg-transparent')
        with panels:
            for key, _, _ in nav:
                with ui.tab_panel(key).classes('p-0 flex flex-col gap-4'):
                    builders[key]()
    select(nav[0][0])
    return select
