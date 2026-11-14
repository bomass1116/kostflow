"""Kartu kamar bergaya hotel. Kamar yang sudah laku tampil abu-abu dengan label SOLD."""
from nicegui import ui

from . import services as sv
from . import ui_common as ux


def photo_url(r) -> str:
    if r['photo']:
        return f'/uploads/{r["photo"]}'
    key = (r['type_name'] or 'standard').lower()
    return f'/static/{key if key in ("standard", "deluxe", "premium") else "standard"}.svg'


def room_detail(r, on_book=None) -> None:
    """Dialog besar berisi detail kamar (dibuka saat foto kamar diklik)."""
    sold = r['status'] != 'Tersedia'
    with ui.dialog() as d, ui.card().classes('p-0 w-[560px] max-w-[95vw] overflow-hidden gap-0'):
        with ui.element('div').classes('kf-room-photo w-full' + (' kf-sold' if sold else '')):
            ui.html(f'<img src="{photo_url(r)}" alt="Kamar {r["code"]}">')
            if sold:
                ui.html('<div class="kf-sold-label">SOLD</div>')
        with ui.column().classes('p-5 gap-2 w-full'):
            ui.label(f'{r["type_name"]} · Kamar {r["code"]}').classes('kf-title text-2xl')
            ui.label(f'Lantai {r["floor"]} · {r["size"]}').classes('kf-muted')
            ui.label(r['description'] or '')
            with ui.row().classes('gap-1'):
                for f in [x.strip() for x in (r['facilities'] or '').split(',') if x.strip()]:
                    ui.badge(f).classes('kf-chip')
            ui.label(f'{sv.rp(r["price"])} / bulan').classes('kf-title text-xl kf-atext')
            with ui.row().classes('justify-end w-full'):
                ui.button('Tutup', on_click=d.close).props('flat no-caps')
                if on_book:
                    ui.button('Sold' if sold else 'Pesan kamar ini', on_click=lambda: (d.close(), on_book(r))).props(
                        'unelevated color=primary no-caps' + (' disable' if sold else ''))
    d.open()


def room_card(r, on_book=None, on_edit=None) -> None:
    sold = r['status'] != 'Tersedia'
    with ui.card().classes('kf-room kf-hover kf-reveal p-0 w-full sm:w-[320px] gap-0' + (' kf-sold' if sold else '')):
        with ui.element('div').classes('kf-room-photo w-full').on('click', lambda r=r: room_detail(r, on_book)):
            ui.html(f'<img src="{photo_url(r)}" alt="Kamar {r["code"]} tipe {r["type_name"]}">')
            if sold:
                ui.html('<div class="kf-sold-label">SOLD</div>')
        with ui.column().classes('kf-room-body p-4 gap-1 w-full'):
            ui.label(r['type_name'] or 'Standard').classes('kf-title text-xl')
            ui.label(f'Kamar {r["code"]} · Lantai {r["floor"]} · {r["size"]}').classes('kf-muted')
            ui.label(r['description'] or '').classes('text-sm')
            with ui.row().classes('gap-1 mt-1'):
                for f in [x.strip() for x in (r['facilities'] or '').split(',') if x.strip()]:
                    ui.badge(f).classes('kf-chip')
            ui.label(f'{sv.rp(r["price"])} / bulan').classes('kf-title text-lg mt-1' + ('' if sold else ' kf-atext'))
            if on_book:
                ui.button('Sold' if sold else 'Pesan kamar ini', on_click=(lambda r=r: on_book(r))).props(
                    'unelevated color=primary no-caps' + (' disable' if sold else '')).classes('mt-1')
            if on_edit:
                ux.badge(r['status'])
                ui.button('Edit tampilan', icon='edit', on_click=lambda r=r: on_edit(r)).props('flat no-caps')
