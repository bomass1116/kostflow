"""Tema warna (bisa dipilih pengguna), CSS global, JS animasi, logo, dan ilustrasi."""
from nicegui import app, ui

DEFAULT_THEME, DEFAULT_MODE = 'homie', 'dark'

# Setiap tema: warna aksen + palet permukaan untuk mode gelap & terang.
THEMES = {
    'homie': dict(
        name='Homie', accent='#F2B705', ink='#2b2200', accent2='#6AB04C',
        dark=dict(bg='#1d1813', surface='#2a231c', surface2='#352c23', border='rgba(255,255,255,.09)',
                  text='#f4efe6', muted='#b8ad9c', atext='#F2B705'),
        light=dict(bg='#f5efe3', surface='#fffdf8', surface2='#f0e8d8', border='rgba(59,49,40,.13)',
                   text='#3B3128', muted='#7a6f60', atext='#8a6500')),
    'malam': dict(
        name='Malam', accent='#8CD62B', ink='#10170a', accent2='#4ade80',
        dark=dict(bg='#0b0b0b', surface='#151515', surface2='#1f1f1f', border='rgba(255,255,255,.09)',
                  text='#f2f2f2', muted='#a0a0a0', atext='#8CD62B'),
        light=dict(bg='#f2f4ee', surface='#ffffff', surface2='#e9ede1', border='rgba(0,0,0,.11)',
                   text='#1c2017', muted='#667060', atext='#4a7a0b')),
    'hutan': dict(
        name='Hutan', accent='#4CAF73', ink='#06210f', accent2='#A3D977',
        dark=dict(bg='#0f1a14', surface='#172a20', surface2='#1f3829', border='rgba(255,255,255,.09)',
                  text='#e8f3ec', muted='#9db8a8', atext='#6fd196'),
        light=dict(bg='#eef5ef', surface='#ffffff', surface2='#e0ede3', border='rgba(20,60,35,.13)',
                   text='#1a3326', muted='#5f7a6a', atext='#1f6b3f')),
    'samudra': dict(
        name='Samudra', accent='#3FA7F5', ink='#04192b', accent2='#5eead4',
        dark=dict(bg='#0c1520', surface='#14233a', surface2='#1b304d', border='rgba(255,255,255,.09)',
                  text='#e8f1fb', muted='#9fb3c8', atext='#6cbcf8'),
        light=dict(bg='#eef4fa', surface='#ffffff', surface2='#dfe9f4', border='rgba(20,50,90,.13)',
                   text='#17304d', muted='#5f7590', atext='#1b6aa8')),
    'sakura': dict(
        name='Sakura', accent='#F28AB2', ink='#2e0b1a', accent2='#fbbf77',
        dark=dict(bg='#1c1218', surface='#2a1b24', surface2='#36232f', border='rgba(255,255,255,.09)',
                  text='#f8ecf2', muted='#bfa6b2', atext='#f6a3c3'),
        light=dict(bg='#fbf1f5', surface='#ffffff', surface2='#f6e3ea', border='rgba(90,30,55,.12)',
                   text='#43212f', muted='#86606f', atext='#b0366a')),
}


def current() -> tuple[str, str]:
    t = app.storage.user.get('theme', DEFAULT_THEME)
    m = app.storage.user.get('mode', DEFAULT_MODE)
    return (t if t in THEMES else DEFAULT_THEME), (m if m in ('dark', 'light') else DEFAULT_MODE)


def palette() -> dict:
    """Warna tema aktif, dipakai grafik (ECharts) di sisi Python."""
    t, m = current()
    th = THEMES[t]
    return dict(accent=th['accent'], accent2=th['accent2'], **th[m])


def set_theme(theme: str | None = None, mode: str | None = None) -> None:
    t, m = current()
    t, m = theme or t, mode or m
    app.storage.user.update(theme=t, mode=m)
    ui.run_javascript(
        f"document.documentElement.dataset.theme='{t}';document.documentElement.dataset.mode='{m}';"
        f"if(window.Quasar)Quasar.Dark.set({'true' if m == 'dark' else 'false'});")


def _vars_css() -> str:
    out = []
    for key, th in THEMES.items():
        for mode in ('dark', 'light'):
            p = th[mode]
            out.append(
                f'html[data-theme="{key}"][data-mode="{mode}"],html[data-theme="{key}"][data-mode="{mode}"] body{{--bg:{p["bg"]};--surface:{p["surface"]};'
                f'--surface2:{p["surface2"]};--border:{p["border"]};--text:{p["text"]};--muted:{p["muted"]};'
                f'--atext:{p["atext"]};--accent:{th["accent"]};--ink:{th["ink"]};--accent2:{th["accent2"]};'
                f'--q-primary:{th["accent"]}!important;--q-secondary:{th["accent2"]}!important;--q-accent:{th["accent"]}!important;}}')
    return '\n'.join(out)


BASE_CSS = '''
html,body,.q-layout,.q-page-container{background:var(--bg)!important;color:var(--text);}
body{font-family:'Figtree',system-ui,sans-serif;}
.nicegui-content{padding:0;}
.kf-title{font-family:'Bricolage Grotesque','Figtree',sans-serif;font-weight:700;letter-spacing:-.01em;}
.kf-muted{color:var(--muted);font-size:.86rem;}
.kf-atext{color:var(--atext);}
a{color:var(--atext);}
/* tombol & komponen Quasar mengikuti tema (selector dinaikkan agar menang atas warna bawaan NiceGUI/Quasar) */
html body .bg-primary{background:var(--accent)!important;color:var(--ink)!important;}
html body .text-primary{color:var(--atext)!important;}
html body .bg-secondary{background:var(--accent2)!important;}
html body .q-btn--outline.text-primary{color:var(--atext)!important;}
html body .q-tab--active{color:var(--atext);}
html body .kf-top .q-btn.text-primary{color:var(--text)!important;}
html body .kf-nav.q-btn.text-primary{color:var(--muted)!important;}
html body .kf-nav.q-btn.text-primary:hover{color:var(--text)!important;}
html body .kf-nav-active.q-btn.text-primary{color:var(--text)!important;}
html body .kf-filter.q-btn.text-primary{color:var(--text)!important;}
html body .kf-filter-on.q-btn.text-primary{color:var(--ink)!important;}
html body .kf-side-card .q-btn.text-primary{color:var(--atext)!important;}
.q-tab--active,.q-tab--active .q-icon{color:var(--atext);}
.q-tabs__arrow,.q-tab{color:var(--muted);}
.q-field--outlined .q-field__control:before{border-color:var(--border);}
.q-field__label,.q-field__native,.q-field__input,.q-field__prefix,.q-field__suffix{color:var(--text);}
.q-field__label{opacity:.75;}
.q-card,.q-menu,.q-dialog .q-card{background:var(--surface);color:var(--text);}
.q-menu{background:var(--surface2);border:1px solid var(--border);}
.q-table__container,.q-table thead tr,.q-table tbody td,.q-table__bottom{background:transparent;color:var(--text);}
.q-table th{color:var(--muted);font-weight:600;}
.q-table--bordered,.q-table td,.q-table th{border-color:var(--border);}
.q-uploader{background:var(--surface2);color:var(--text);border-color:var(--border);}
.q-uploader__header{background:var(--accent);color:var(--ink);}
.q-uploader__subtitle,.q-uploader__title{color:var(--ink);}
/* tombol "+" pilih file: warnanya dulu sama dengan latar header (sama-sama aksen) sehingga tak terlihat */
html body .q-uploader__header .q-btn,html body .q-uploader__header .q-btn.text-primary,
html body .q-uploader__header .q-btn .q-icon{color:var(--ink)!important;}
.q-uploader__header .q-btn{background:rgba(0,0,0,.12);border-radius:10px;}
.q-uploader__header .q-btn .q-icon{font-size:1.6rem;}
.q-uploader__header .q-btn:hover{background:rgba(0,0,0,.22);}
.q-uploader__header{min-height:56px;}
.q-separator{background:var(--border);}
.q-item{color:var(--text);}
/* bilah atas */
.kf-top.q-header{background:color-mix(in srgb,var(--bg) 82%,transparent)!important;backdrop-filter:blur(12px);
  border-bottom:1px solid var(--border);color:var(--text);}
.kf-top .q-btn{color:var(--text);}
.kf-search{width:260px;max-width:34vw;}
.kf-search .q-field__control{border-radius:12px;background:var(--surface);}
/* sidebar */
.q-drawer{background:var(--surface)!important;border-right:1px solid var(--border);color:var(--text);}
.kf-nav.q-btn{width:100%;justify-content:flex-start;border-radius:12px;padding:10px 14px;color:var(--muted);
  transition:background .25s,transform .25s,color .25s;}
.kf-nav.q-btn .q-icon{font-size:1.25rem;margin-right:6px;}
.kf-nav.q-btn:hover{background:color-mix(in srgb,var(--accent) 12%,transparent);color:var(--text);transform:translateX(4px);}
.kf-nav-active.q-btn,.kf-nav-active.q-btn:hover{color:var(--text)!important;
  background:linear-gradient(90deg,color-mix(in srgb,var(--accent) 38%,transparent),color-mix(in srgb,var(--accent2) 14%,transparent));
  box-shadow:inset 0 0 0 1px color-mix(in srgb,var(--accent) 50%,transparent);}
.kf-nav-active.q-btn .q-icon{color:var(--atext);}
.kf-side-card{border:1px solid var(--border);border-radius:14px;padding:14px;background:var(--surface2);width:100%;}
/* logo */
.kf-logo{display:flex;align-items:center;gap:10px;text-decoration:none;color:var(--text);}
.kf-word{font-family:'Bricolage Grotesque',sans-serif;font-weight:700;letter-spacing:.22em;font-size:1.05rem;color:var(--text);}
.kf-word b{color:var(--atext);font-weight:700;}
/* kartu */
.kf-card{background:var(--surface);border:1px solid var(--border);border-radius:16px;box-shadow:none;color:var(--text);}
.kf-hover{transition:transform .3s cubic-bezier(.2,.8,.2,1),border-color .3s,box-shadow .3s;}
.kf-hover:hover{transform:translateY(-4px);border-color:color-mix(in srgb,var(--accent) 55%,var(--border));
  box-shadow:0 14px 30px -14px color-mix(in srgb,var(--accent) 45%,transparent);}
.kf-hero{position:relative;overflow:hidden;border:1px solid var(--border);border-radius:22px;padding:26px;
  background:radial-gradient(circle at 88% 10%,color-mix(in srgb,var(--accent) 22%,transparent),transparent 55%),var(--surface);}
.kf-hero-grid{display:grid;grid-template-columns:1.7fr 1fr;gap:18px;align-items:center;}
.kf-h1{font-size:2.3rem;line-height:1.1;}
.kf-sub{color:var(--muted);max-width:34rem;}
.kf-hero-art{min-height:200px;}
.kf-hero-art svg,.kf-scene{width:100%;height:auto;display:block;}
.kf-tiles{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;width:100%;}
.kf-tile{background:color-mix(in srgb,var(--bg) 45%,var(--surface2));border:1px solid var(--border);border-radius:14px;
  padding:14px;display:flex;flex-direction:column;gap:2px;transition:transform .3s,border-color .3s;}
.kf-tile:hover{transform:translateY(-3px);border-color:color-mix(in srgb,var(--accent) 50%,var(--border));}
.kf-ico{width:38px;height:38px;border-radius:50%;display:grid;place-items:center;
  background:color-mix(in srgb,var(--accent) 20%,transparent);color:var(--atext);margin-bottom:6px;}
.kf-stat{font-family:'Bricolage Grotesque',sans-serif;font-weight:700;font-size:1.5rem;line-height:1.15;overflow-wrap:anywhere;}
.kf-good{color:var(--atext);font-size:.82rem;font-weight:600;}
@media(max-width:900px){.kf-hero-grid{grid-template-columns:1fr;}.kf-h1{font-size:1.8rem;}.kf-search{display:none;}}
/* layar HP: kartu lebih rapat, angka tidak terpotong, ilustrasi dikecilkan */
@media(max-width:600px){
  .kf-hero{padding:18px;border-radius:18px;}
  .kf-h1{font-size:1.55rem;}
  .kf-tiles{gap:10px;}
  .kf-tile{padding:12px;}
  .kf-stat{font-size:1.25rem;white-space:nowrap;overflow-wrap:normal;}
  .kf-hero-art{min-height:0;max-width:260px;margin:0 auto;}
  .q-page-container .q-tab-panels{overflow:visible;}
}
/* kamar */
.kf-room{background:var(--surface);border:1px solid var(--border);border-radius:16px;overflow:hidden;box-shadow:none;color:var(--text);cursor:pointer;}
.kf-room-photo{position:relative;line-height:0;overflow:hidden;}
.kf-room-photo img{width:100%;aspect-ratio:8/5;object-fit:cover;display:block;transition:transform .6s cubic-bezier(.2,.8,.2,1);}
.kf-room:hover .kf-room-photo img{transform:scale(1.07);}
.kf-sold .kf-room-photo img{filter:grayscale(1);opacity:.5;}
.kf-sold:hover .kf-room-photo img{transform:none;}
.kf-sold-label{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-family:'Bricolage Grotesque',sans-serif;
  font-weight:700;font-size:2.2rem;letter-spacing:.25em;color:#fff;background:rgba(40,40,40,.5);line-height:1;}
.kf-sold .kf-room-body{opacity:.6;}
.kf-chip.q-badge{background:color-mix(in srgb,var(--accent) 14%,transparent)!important;color:var(--text)!important;}
.kf-filter.q-btn{border-radius:999px;padding:4px 16px;border:1px solid var(--border);color:var(--text);}
.kf-filter-on.q-btn{background:var(--accent)!important;color:var(--ink)!important;border-color:var(--accent);}
.kf-step{border-radius:16px;border:1px solid var(--border);background:var(--surface);padding:20px;}
/* halaman masuk */
.kf-login{display:grid;grid-template-columns:1.1fr 1fr;min-height:100vh;}
.kf-login-art{background:radial-gradient(circle at 70% 20%,color-mix(in srgb,var(--accent) 24%,transparent),transparent 60%),var(--surface);
  padding:36px;display:flex;flex-direction:column;justify-content:space-between;border-right:1px solid var(--border);}
@media(max-width:900px){.kf-login{grid-template-columns:1fr;}.kf-login-art{display:none;}}
/* animasi */
.kf-reveal{opacity:0;transform:translateY(20px);transition:opacity .7s ease,transform .7s cubic-bezier(.2,.8,.2,1);}
.kf-reveal.in{opacity:1;transform:none;}
@keyframes kf-drift{0%{transform:translateX(-14px)}50%{transform:translateX(14px)}100%{transform:translateX(-14px)}}
@keyframes kf-pulse{0%,100%{transform:scale(1)}50%{transform:scale(1.07)}}
@keyframes kf-sway{0%,100%{transform:rotate(-1.5deg)}50%{transform:rotate(1.5deg)}}
.kf-cloud{animation:kf-drift 14s ease-in-out infinite;}
.kf-sun{animation:kf-pulse 5s ease-in-out infinite;transform-origin:410px 80px;}
.kf-tree{animation:kf-sway 6s ease-in-out infinite;transform-origin:70px 300px;}
.q-tab-panel{padding:0;}
@media(prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important;}.kf-reveal{opacity:1;transform:none;}}
'''

JS = '''
(function(){
  function fmt(n,el){return (el.dataset.fmt==='rp'?'Rp\u00a0':'')+Math.round(n).toLocaleString('id-ID')+(el.dataset.fmt==='pct'?'%':'');}
  function count(el){
    if(el.dataset.done) return; el.dataset.done=1;
    var to=parseFloat(el.dataset.to)||0, t0=performance.now();
    (function step(t){var k=Math.min(1,(t-t0)/900),e=1-Math.pow(1-k,3);el.textContent=fmt(to*e,el);if(k<1)requestAnimationFrame(step);})(t0);
  }
  var io=('IntersectionObserver' in window)?new IntersectionObserver(function(es){
    es.forEach(function(e){if(e.isIntersecting){e.target.classList.add('in');io.unobserve(e.target);}});},{threshold:.08}):null;
  var pending=false;
  function scan(){
    pending=false;
    document.querySelectorAll('.kf-count:not([data-done])').forEach(count);
    document.querySelectorAll('.kf-reveal:not(.in)').forEach(function(el){if(io)io.observe(el);else el.classList.add('in');});
  }
  function schedule(){if(!pending){pending=true;requestAnimationFrame(scan);}}
  new MutationObserver(schedule).observe(document.documentElement,{childList:true,subtree:true});
  document.addEventListener('DOMContentLoaded',schedule);
  setTimeout(function(){document.querySelectorAll('.kf-reveal').forEach(function(el){el.classList.add('in');});},3000);
  document.addEventListener('mousemove',function(ev){
    var x=ev.clientX/innerWidth-.5,y=ev.clientY/innerHeight-.5;
    document.querySelectorAll('.kf-scene [data-depth]').forEach(function(el){
      var d=parseFloat(el.dataset.depth);el.style.transform='translate('+(x*d*-26)+'px,'+(y*d*-14)+'px)';});
  });
})();
'''


def apply() -> None:
    """Pasang tema ke halaman ini. Panggil di awal setiap halaman."""
    t, m = current()
    ui.dark_mode(m == 'dark')
    ui.add_head_html(f'''
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:wght@600;700&family=Figtree:wght@400;500;600&display=swap" rel="stylesheet">
    <script>document.documentElement.dataset.theme="{t}";document.documentElement.dataset.mode="{m}";</script>
    <style>@layer overrides{{{_vars_css()}\n{BASE_CSS}}}</style>
    <script>{JS}</script>''')


def logo_svg(size: int = 34) -> str:
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg" aria-label="Logo KostFlow">'
            '<path d="M5 24 24 7l19 17" stroke="var(--accent)" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>'
            '<path d="M11 25v15h26V25" stroke="var(--text)" stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round"/>'
            '<path d="M15 34c3-5 6-5 9 0s6 5 9 0" stroke="var(--accent2)" stroke-width="3.4" stroke-linecap="round"/></svg>')


def logo_html(size: int = 34, word: bool = True) -> str:
    w = '<span class="kf-word">KOST<b>FLOW</b></span>' if word else ''
    return f'<span class="kf-logo">{logo_svg(size)}{w}</span>'


def scene_svg() -> str:
    """Ilustrasi kost bernuansa taman (mengikuti warna tema). Lapisannya bergeser halus mengikuti mouse."""
    def house(x, wall, roof):
        return (f'<g transform="translate({x} 0)"><rect x="0" y="236" width="74" height="64" fill="{wall}"/>'
                f'<path d="M-8 240 37 200l45 40z" fill="{roof}"/><rect x="26" y="262" width="22" height="38" fill="#3B3128" opacity=".75"/>'
                '<rect x="8" y="250" width="14" height="14" fill="#dff1fb" opacity=".9"/><rect x="52" y="250" width="14" height="14" fill="#dff1fb" opacity=".9"/></g>')
    return f'''<svg class="kf-scene" viewBox="0 0 520 330" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Ilustrasi deretan rumah kost">
<g data-depth="0.3"><g class="kf-sun"><circle cx="410" cy="80" r="34" fill="var(--accent)"/>
<g stroke="var(--accent)" stroke-width="5" stroke-linecap="round"><path d="M410 28v-12M410 132v12M358 80h-12M474 80h12M373 43l-8-8M447 117l8 8M447 43l8-8M373 117l-8 8"/></g></g></g>
<g data-depth="0.6"><g class="kf-cloud" fill="#fff" opacity=".2"><ellipse cx="120" cy="70" rx="54" ry="16"/><ellipse cx="156" cy="58" rx="34" ry="14"/></g></g>
<g data-depth="0.9"><path d="M0 260c70-60 140-60 210-10s150 20 310-20V330H0z" fill="var(--accent2)" opacity=".5"/></g>
<g data-depth="1.3">{house(150, "#7fc4b5", "#D9613A")}{house(236, "#e9c7a0", "#4C9BD6")}{house(322, "#a7c4a0", "#E8B93A")}</g>
<g data-depth="1.7"><path d="M0 292c90-14 170 10 260 0s170-16 260 0V330H0z" fill="var(--accent2)"/>
<g class="kf-tree"><rect x="64" y="236" width="12" height="64" fill="#7a5c3b"/><circle cx="70" cy="224" r="36" fill="var(--accent2)"/><circle cx="46" cy="244" r="24" fill="var(--accent2)" opacity=".85"/></g>
<g fill="var(--accent)"><circle cx="450" cy="306" r="5"/><circle cx="476" cy="312" r="4"/><circle cx="426" cy="314" r="4"/></g></g></svg>'''
