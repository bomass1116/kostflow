"""Tema, header, dan helper UI yang dipakai semua halaman."""
import uuid

from nicegui import app, ui

from . import services as sv
from . import theme as th
from .db import store_file

theme = th.apply  # alias: ux.theme() dipanggil di awal tiap halaman

STATUS_COLOR = {
    'Tersedia': 'positive', 'Dipesan': 'warning', 'Terisi': 'grey-7',
    'Lunas': 'positive', 'Belum Dibayar': 'warning', 'Menunggu Verifikasi': 'info', 'Ditolak': 'negative',
    'Menunggu': 'warning', 'Disetujui': 'positive',
    'Baru': 'info', 'Diterima': 'primary', 'Diproses': 'warning', 'Selesai': 'positive',
    'Dikonfirmasi': 'positive', 'Dibatalkan': 'grey-7', 'Dibuka Ulang': 'negative',
    'Menunggu Persetujuan Biaya': 'orange', 'Menunggu Pembayaran': 'orange',
}


def badge(text: str):
    return ui.badge(text, color=STATUS_COLOR.get(text, 'grey')).props('outline' if text in ('Terisi', 'Dibatalkan') else '')


HOME = {'owner': '/owner', 'tenant': '/tenant', 'applicant': '/applicant'}
ROLE_LABEL = {'owner': 'Pemilik Kost', 'tenant': 'Penghuni', 'applicant': 'Calon Penghuni'}


def current_user():
    """Ambil pengguna login dari database (peran selalu terbaru)."""
    uid = app.storage.user.get('uid')
    u = sv.get_user(uid) if uid else None
    if u:
        app.storage.user.update(role=u['role'], name=u['full_name'])
    return u


def require_role(role: str) -> bool:
    """True bila pengguna login dengan peran yang benar; kalau tidak, diarahkan ke halaman yang sesuai."""
    u = current_user()
    if not u:
        ui.navigate.to('/login')
        return False
    if u['role'] != role:
        ui.navigate.to(HOME[u['role']])
        return False
    return True


def logout() -> None:
    app.storage.user.pop('uid', None)
    app.storage.user.pop('role', None)
    ui.navigate.to('/login')


def tile(icon: str, label: str, value, fmt: str = 'num', hint: str = '') -> None:
    """Kartu statistik berikon. Angka menghitung naik saat muncul (animasi di JS)."""
    with ui.element('div').classes('kf-tile'):
        with ui.element('div').classes('kf-ico'):
            ui.icon(icon).classes('text-lg')
        ui.label(label).classes('kf-muted')
        if fmt == 'text':
            ui.label(str(value)).classes('kf-stat')
        else:
            shown = sv.rp(value) if fmt == 'rp' else f'{int(value):,}'.replace(',', '.') + ('%' if fmt == 'pct' else '')
            ui.html(f'<span class="kf-stat kf-count" data-to="{int(value)}" data-fmt="{fmt}">{shown}</span>')
        if hint:
            ui.label(hint).classes('kf-good' if hint.startswith('✓') else 'kf-muted')


def hero(greeting: str, title: str, subtitle: str, tiles: list[dict]) -> None:
    """Kartu sambutan besar di bagian atas dashboard (gaya referensi)."""
    with ui.element('div').classes('kf-hero w-full kf-reveal'):
        with ui.element('div').classes('kf-hero-grid'):
            with ui.column().classes('gap-2'):
                ui.label(greeting).classes('kf-muted')
                ui.label(title).classes('kf-title kf-h1')
                ui.label(subtitle).classes('kf-sub')
                with ui.element('div').classes('kf-tiles mt-2'):
                    for t in tiles:
                        tile(**t)
            ui.html(th.scene_svg()).classes('kf-hero-art')


IMAGE_EXT = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}
MAX_UPLOAD = 5_000_000


def _looks_like(ext: str, data: bytes) -> bool:
    """Cek tanda ('magic bytes') awal file agar isi sesuai ekstensinya."""
    if ext in ('.jpg', '.jpeg'):
        return data[:3] == b'\xff\xd8\xff'
    if ext == '.png':
        return data[:8] == b'\x89PNG\r\n\x1a\n'
    if ext == '.gif':
        return data[:4] == b'GIF8'
    if ext == '.webp':
        return data[:4] == b'RIFF' and data[8:12] == b'WEBP'
    if ext == '.pdf':
        return data[:5] == b'%PDF-'
    return False


async def save_upload(e, images_only: bool = False) -> str | None:
    """Simpan file hasil ui.upload (ke Supabase / data/uploads) dan kembalikan nama file.

    Hanya JPG/PNG/WEBP/GIF (dan PDF bila images_only=False), maks 5 MB, isi harus cocok dengan ekstensi.
    Bila ditolak, tampil pesan dan mengembalikan None (pemanggil wajib mengecek).
    """
    if hasattr(e, 'file'):
        name, data = e.file.name, await e.file.read()
    else:  # NiceGUI 2.x
        name, data = e.name, e.content.read()
    ext = ('.' + name.rsplit('.', 1)[-1].lower()) if '.' in name else ''
    allowed = IMAGE_EXT if images_only else IMAGE_EXT | {'.pdf'}
    if ext not in allowed:
        ui.notify('Format tidak didukung. Gunakan ' + ('JPG, PNG, WEBP.' if images_only else 'JPG, PNG, WEBP, atau PDF.'), type='negative')
        return None
    if len(data) > MAX_UPLOAD:
        ui.notify('Ukuran file maksimal 5 MB.', type='negative')
        return None
    if not _looks_like(ext, data):
        ui.notify('Isi file tidak sesuai formatnya. Unggah foto atau PDF yang asli.', type='negative')
        return None
    fname = uuid.uuid4().hex[:12] + ext
    store_file(fname, data)
    return fname


def guard(fn, *args) -> bool:
    """Jalankan aksi bisnis; bila ditolak aturan (ValueError) tampilkan pesan, bukan error diam-diam."""
    try:
        fn(*args)
        return True
    except ValueError as e:
        ui.notify(str(e), type='warning')
        return False


def password_dialog(uid: int) -> None:
    with ui.dialog() as d, ui.card().classes('w-96 max-w-full gap-2'):
        ui.label('Ganti password').classes('kf-title text-lg')
        old = ui.input('Password lama', password=True, password_toggle_button=True).props('outlined dense').classes('w-full')
        new = ui.input('Password baru (min. 6)', password=True, password_toggle_button=True).props('outlined dense').classes('w-full')
        new2 = ui.input('Ulangi password baru', password=True).props('outlined dense').classes('w-full')

        def save():
            if (new.value or '') != (new2.value or ''):
                ui.notify('Konfirmasi password tidak sama', type='negative')
                return
            if guard(sv.change_password, uid, old.value or '', new.value or ''):
                d.close()
                ui.notify('Password berhasil diganti', type='positive')

        with ui.row().classes('justify-end w-full'):
            ui.button('Batal', on_click=d.close).props('flat no-caps')
            ui.button('Simpan', on_click=save).props('unelevated color=primary no-caps')
    d.open()


def file_link(fname: str | None, label: str = 'Lihat file') -> None:
    if not fname:
        return
    ui.link(label, f'/uploads/{fname}', new_tab=True).classes('text-sm')


def confirm_dialog(message: str, on_yes, *, input_label: str | None = None, yes_label: str = 'Ya'):
    """Dialog konfirmasi; bila input_label diisi, minta teks (mis. alasan penolakan)."""
    with ui.dialog() as d, ui.card().classes('w-96 max-w-full'):
        ui.label(message).classes('text-base')
        field = ui.input(input_label).classes('w-full') if input_label else None

        def go():
            if field is not None and not (field.value or '').strip():
                ui.notify(f'{input_label} wajib diisi', type='warning')
                return
            d.close()
            on_yes(field.value.strip() if field is not None else None)

        with ui.row().classes('justify-end w-full'):
            ui.button('Batal', on_click=d.close).props('flat')
            ui.button(yes_label, on_click=go)
    d.open()
