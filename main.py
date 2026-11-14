"""KostFlow - titik masuk aplikasi. Jalankan: python main.py"""
import asyncio
import logging
import os
import re
import secrets

from fastapi import Response
from nicegui import app, ui

from app import services
from app.db import BASE_DIR, DATA_DIR, init_db, load_file, q
from app.pages import applicant, login, owner, public, tenant

init_db()
app.add_static_files('/static', str(BASE_DIR / 'app' / 'static'))

_SAFE_NAME = re.compile(r'^[a-f0-9]{12}\.[a-z]{3,4}$')


_MIME = {'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'png': 'image/png', 'gif': 'image/gif',
         'webp': 'image/webp', 'pdf': 'application/pdf'}


@app.get('/uploads/{fname}')
def serve_upload(fname: str):
    """File upload TIDAK publik: foto kamar terbuka untuk umum, dokumen hanya untuk pemilik kost / pengunggahnya."""
    if not _SAFE_NAME.match(fname):
        return Response(status_code=404)
    uid = app.storage.user.get('uid')
    user = services.get_user(uid) if uid else None
    if not services.can_view_file(user, fname):
        return Response(status_code=403)
    data = load_file(fname)
    if data is None:
        return Response(status_code=404)
    return Response(content=data, media_type=_MIME.get(fname.rsplit('.', 1)[-1], 'application/octet-stream'),
                    headers={'X-Content-Type-Options': 'nosniff', 'Cache-Control': 'private, max-age=300'})


@app.get('/healthz')
def healthz():
    """Dipanggil layanan ping (UptimeRobot / cron-job.org) tiap beberapa menit: menjaga Render tidak tidur
    dan Supabase tidak di-pause. Menyentuh database dengan query ringan."""
    try:
        q('SELECT 1 AS ok', one=True)
    except Exception:
        return Response('database error', status_code=503, media_type='text/plain')
    return Response('ok', media_type='text/plain')


def storage_secret() -> str:
    """Pakai STORAGE_SECRET dari env; bila tidak ada, buat rahasia acak sekali dan simpan di data/.secret."""
    env = os.environ.get('STORAGE_SECRET')
    if env:
        return env
    path = DATA_DIR / '.secret'
    if not path.exists():
        path.write_text(secrets.token_urlsafe(32))
        try:
            path.chmod(0o600)
        except OSError:
            pass
    return path.read_text().strip()

public.register()
login.register()
applicant.register()
tenant.register()
owner.register()


async def billing_scheduler():
    """Scheduler: cek jatuh tempo kontrak & terbitkan tagihan tiap jam."""
    while True:
        try:
            services.run_billing_engine()
        except Exception:  # satu kegagalan tidak boleh mematikan scheduler selamanya
            logging.exception('billing engine gagal, dicoba lagi jam berikutnya')
        await asyncio.sleep(3600)


app.on_startup(lambda: asyncio.create_task(billing_scheduler()))

ui.run(
    title='KostFlow',
    host='0.0.0.0',
    port=int(os.environ.get('PORT', 8080)),
    storage_secret=storage_secret(),
    reload=False,
    show=False,
    favicon=str(BASE_DIR / 'app' / 'static' / 'logo.svg'),
)
