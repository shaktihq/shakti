"""Professional Admin UI — dark/light mode, no @apply (CDN compatible)."""

from __future__ import annotations
from typing import Any

ICONS = {
    "dashboard": '<svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="7" rx="1" stroke-width="2"/><rect x="14" y="3" width="7" height="7" rx="1" stroke-width="2"/><rect x="3" y="14" width="7" height="7" rx="1" stroke-width="2"/><rect x="14" y="14" width="7" height="7" rx="1" stroke-width="2"/></svg>',
    "table":     '<svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h18M3 6h18M3 14h18M3 18h18"/></svg>',
    "plus":      '<svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/></svg>',
    "edit":      '<svg class="w-3.5 h-3.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/></svg>',
    "trash":     '<svg class="w-3.5 h-3.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>',
    "download":  '<svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/></svg>',
    "search":    '<svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>',
    "logout":    '<svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"/></svg>',
    "sun":       '<svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364-6.364l-.707.707M6.343 17.657l-.707.707m12.728 0l-.707-.707M6.343 6.343l-.707-.707M12 8a4 4 0 100 8 4 4 0 000-8z"/></svg>',
    "moon":      '<svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"/></svg>',
    "check":     '<svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>',
    "x":         '<svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>',
    "activity":  '<svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"/></svg>',
    "chevron":   '<svg class="w-3 h-3 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/></svg>',
}

_HEAD = """
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<script src="https://cdn.tailwindcss.com"></script>
<script defer src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js"></script>
<script>
tailwind.config = {
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        brand: {
          50:  '#eef2ff',
          100: '#e0e7ff',
          200: '#c7d2fe',
          400: '#818cf8',
          500: '#6366f1',
          600: '#4f46e5',
          700: '#4338ca',
        }
      }
    }
  }
}
</script>
<style>
  * { box-sizing: border-box; }
  body { font-family: 'Inter', ui-sans-serif, system-ui, sans-serif; }
  [x-cloak] { display: none !important; }
</style>
<script>
  (function(){
    var t = localStorage.getItem('pf_theme') || 'dark';
    if(t === 'dark') document.documentElement.classList.add('dark');
  })();
</script>
"""

def _toggle_js():
    return "darkMode: localStorage.getItem('pf_theme') !== 'light', toggleTheme(){ this.darkMode=!this.darkMode; localStorage.setItem('pf_theme', this.darkMode ? 'dark' : 'light'); if(this.darkMode){ document.documentElement.classList.add('dark'); } else { document.documentElement.classList.remove('dark'); } }"


def _sidebar(models_slugs, current="", title="Shakti Admin", prefix="/admin"):
    dash_active = current == "__dashboard__"
    da = "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium bg-brand-600 text-white"
    di = "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-white transition-colors cursor-pointer"

    nav_links = f"""
    <a href="{prefix}/" class="{'da' if dash_active else 'di'}".replace('da', '{da}').replace('di', '{di}')>
        {ICONS['dashboard']}
        <span>Dashboard</span>
    </a>""".replace(
        "'da' if dash_active else 'di'".replace("'", '"'),
        da if dash_active else di
    ).replace(
        "\"da\" if dash_active else \"di\"",
        da if dash_active else di
    )

    # Build dashboard link cleanly
    dash_cls = da if dash_active else di
    nav_links = f'<a href="{prefix}/" class="{dash_cls}">{ICONS["dashboard"]}<span>Dashboard</span></a>'

    for name, slug in models_slugs:
        active = current == slug
        cls = da if active else di
        nav_links += f'<a href="{prefix}/{slug}" class="{cls}">{ICONS["table"]}<span>{name}</span></a>'

    return f"""
<aside style="width:224px;position:fixed;top:0;left:0;bottom:0;z-index:40;display:flex;flex-direction:column;"
       class="bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-800">

  <div class="flex items-center gap-3 px-4 border-b border-gray-200 dark:border-gray-800" style="height:56px;flex-shrink:0;">
    <div class="flex items-center justify-center rounded-lg bg-brand-600 text-white text-xs font-bold" style="width:28px;height:28px;">PF</div>
    <span class="text-sm font-semibold text-gray-900 dark:text-white truncate">{title}</span>
  </div>

  <nav class="flex-1 overflow-y-auto p-3" style="display:flex;flex-direction:column;gap:2px;">
    {nav_links}
    <div class="pt-3 pb-1 px-2">
      <p class="text-xs font-semibold uppercase tracking-widest text-gray-400 dark:text-gray-600">Models</p>
    </div>
  </nav>

  <div class="p-3 border-t border-gray-200 dark:border-gray-800">
    <form method="POST" action="{prefix}/logout">
      <button type="submit" class="{di} w-full text-left">
        {ICONS['logout']}
        <span>Sign out</span>
      </button>
    </form>
  </div>
</aside>"""


def base(title, content, models_slugs, current="", admin_title="Shakti Admin", prefix="/admin"):
    sidebar = _sidebar(models_slugs, current, admin_title, prefix)
    breadcrumb = f'<span class="mx-2 text-gray-300 dark:text-gray-600">/</span><span class="text-sm font-medium text-gray-900 dark:text-white">{title}</span>' if title != "Dashboard" else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<title>{title} — {admin_title}</title>
{_HEAD}
</head>
<body x-data="{{ {_toggle_js()} }}" class="bg-gray-50 dark:bg-gray-950 text-gray-900 dark:text-gray-100 min-h-screen">
{sidebar}

<div style="margin-left:224px;min-height:100vh;display:flex;flex-direction:column;">

  <!-- Topbar -->
  <header class="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 sticky top-0 z-30"
          style="height:56px;display:flex;align-items:center;justify-content:space-between;padding:0 24px;">
    <div class="flex items-center text-sm text-gray-500 dark:text-gray-400">
      <a href="{prefix}/" class="hover:text-gray-900 dark:hover:text-white transition-colors">Admin</a>
      {breadcrumb}
    </div>
    <button @click="toggleTheme()"
            class="flex items-center justify-center rounded-lg text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
            style="width:36px;height:36px;">
      <span x-show="darkMode">{ICONS['sun']}</span>
      <span x-show="!darkMode" x-cloak>{ICONS['moon']}</span>
    </button>
  </header>

  <main class="flex-1 p-6">
    {content}
  </main>

  <footer class="border-t border-gray-200 dark:border-gray-800 px-6 py-3">
    <p class="text-xs text-gray-400 dark:text-gray-600">Shakti Admin &middot; Built with Shakti Framework</p>
  </footer>
</div>
</body>
</html>"""


def login_page(error="", title="Shakti Admin"):
    err_html = f"""
    <div class="flex items-center gap-2 p-3 rounded-lg text-sm bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 mb-4">
      {ICONS['x']}<span>{error}</span>
    </div>""" if error else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<title>Sign In — {title}</title>
{_HEAD}
</head>
<body x-data="{{ {_toggle_js()} }}" class="bg-gray-950 min-h-screen flex items-center justify-center p-4">

  <button @click="toggleTheme()"
          class="fixed top-4 right-4 flex items-center justify-center rounded-lg text-gray-400 hover:bg-gray-800 transition-colors"
          style="width:36px;height:36px;">
    <span x-show="darkMode">{ICONS['sun']}</span>
    <span x-show="!darkMode" x-cloak>{ICONS['moon']}</span>
  </button>

  <div style="width:100%;max-width:380px;">
    <div class="text-center mb-8">
      <div class="flex items-center justify-center rounded-2xl bg-brand-600 text-white text-xl font-bold mx-auto mb-5 shadow-lg"
           style="width:56px;height:56px;">PF</div>
      <h1 class="text-2xl font-bold text-white">{title}</h1>
      <p class="text-sm text-gray-400 mt-1">Sign in to your admin panel</p>
    </div>

    <div class="bg-gray-900 rounded-2xl border border-gray-800 p-7 shadow-2xl">
      {err_html}
      <form method="POST" action="/admin/login" style="display:flex;flex-direction:column;gap:18px;">
        <div>
          <label class="block text-xs font-semibold text-gray-400 uppercase tracking-widest mb-2">Email address</label>
          <input name="email" type="email" required autofocus placeholder="admin@example.com"
            class="w-full px-4 py-2.5 text-sm rounded-xl border border-gray-700 bg-gray-800 text-white placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent transition-colors">
        </div>
        <div>
          <label class="block text-xs font-semibold text-gray-400 uppercase tracking-widest mb-2">Password</label>
          <input name="password" type="password" required placeholder="&bull;&bull;&bull;&bull;&bull;&bull;&bull;&bull;"
            class="w-full px-4 py-2.5 text-sm rounded-xl border border-gray-700 bg-gray-800 text-white placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent transition-colors">
        </div>
        <button type="submit"
          class="w-full py-3 rounded-xl text-sm font-semibold text-white bg-brand-600 hover:bg-brand-500 transition-colors shadow-lg"
          style="margin-top:4px;">
          Sign in
        </button>
      </form>
    </div>
    <p class="text-center text-xs text-gray-600 mt-5">Admin access only &middot; Requires <code class="font-mono bg-gray-800 px-1 py-0.5 rounded text-gray-400">role: admin</code></p>
  </div>
</body>
</html>"""


def dashboard(stats, activity, models_slugs, title, prefix="/admin"):
    colors = [
        ("text-indigo-500 dark:text-indigo-400", "bg-indigo-50 dark:bg-indigo-900/20 border-indigo-200 dark:border-indigo-800"),
        ("text-violet-500 dark:text-violet-400", "bg-violet-50 dark:bg-violet-900/20 border-violet-200 dark:border-violet-800"),
        ("text-emerald-500 dark:text-emerald-400", "bg-emerald-50 dark:bg-emerald-900/20 border-emerald-200 dark:border-emerald-800"),
        ("text-amber-500 dark:text-amber-400",  "bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800"),
        ("text-rose-500 dark:text-rose-400",    "bg-rose-50 dark:bg-rose-900/20 border-rose-200 dark:border-rose-800"),
        ("text-sky-500 dark:text-sky-400",      "bg-sky-50 dark:bg-sky-900/20 border-sky-200 dark:border-sky-800"),
    ]

    cards = ""
    for i, s in enumerate(stats):
        tc, bg = colors[i % len(colors)]
        cards += f"""
        <a href="{prefix}/{s['slug']}"
           class="block bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl p-6 hover:border-brand-400 dark:hover:border-brand-600 hover:shadow-lg transition-all">
          <div class="flex items-start justify-between gap-4">
            <div>
              <p class="text-xs font-semibold uppercase tracking-widest text-gray-400 dark:text-gray-500">{s['name']}</p>
              <p class="text-4xl font-bold {tc} mt-2">{s['count']}</p>
              <p class="text-xs text-gray-400 dark:text-gray-600 mt-1">total records</p>
            </div>
            <div class="flex items-center justify-center rounded-xl border {bg} shrink-0" style="width:40px;height:40px;">
              <span class="{tc}">{ICONS['table']}</span>
            </div>
          </div>
        </a>"""

    if not cards:
        cards = '<div class="col-span-4 py-16 text-center text-gray-500 dark:text-gray-600 text-sm">No models registered yet</div>'

    act_badges = {
        "created": "bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400",
        "updated": "bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400",
        "deleted": "bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400",
        "login":   "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400",
    }

    act_rows = ""
    for a in activity:
        badge = act_badges.get(a.action, "bg-gray-100 dark:bg-gray-800 text-gray-500")
        initial = a.username[0].upper() if a.username else "?"
        detail = a.detail[:50] + "…" if len(a.detail) > 50 else a.detail
        act_rows += f"""
        <tr class="border-t border-gray-100 dark:border-gray-800">
          <td class="px-5 py-3 text-xs text-gray-400 dark:text-gray-500 font-mono">{a.timestamp.strftime('%H:%M:%S')}</td>
          <td class="px-5 py-3">
            <div class="flex items-center gap-2">
              <span class="flex items-center justify-center rounded-full bg-brand-100 dark:bg-brand-900/40 text-brand-600 dark:text-brand-400 text-xs font-bold shrink-0"
                    style="width:26px;height:26px;">{initial}</span>
              <span class="text-sm text-gray-700 dark:text-gray-300 font-medium">{a.username}</span>
            </div>
          </td>
          <td class="px-5 py-3">
            <span class="inline-block px-2 py-0.5 rounded-md text-xs font-semibold {badge}">{a.action.title()}</span>
          </td>
          <td class="px-5 py-3 text-sm text-gray-500 dark:text-gray-400">{a.model}</td>
          <td class="px-5 py-3 text-xs text-gray-400 dark:text-gray-600 font-mono">{detail}</td>
        </tr>"""

    if not act_rows:
        act_rows = f'<tr><td colspan="5" class="py-16 text-center text-sm text-gray-400 dark:text-gray-600">No activity recorded yet</td></tr>'

    content = f"""
    <div class="mb-7">
      <h1 class="text-2xl font-bold text-gray-900 dark:text-white">Dashboard</h1>
      <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">Welcome back. Here&apos;s what&apos;s happening.</p>
    </div>

    <div class="grid gap-4 mb-8" style="grid-template-columns:repeat(auto-fill,minmax(220px,1fr));">
      {cards}
    </div>

    <div class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl overflow-hidden">
      <div class="flex items-center justify-between px-5 py-4 border-b border-gray-100 dark:border-gray-800">
        <div class="flex items-center gap-2">
          <span class="text-gray-400 dark:text-gray-500">{ICONS['activity']}</span>
          <h2 class="text-sm font-semibold text-gray-900 dark:text-white">Recent Activity</h2>
        </div>
        <span class="text-xs text-gray-400 dark:text-gray-600">Last {len(activity)} actions</span>
      </div>
      <div style="overflow-x:auto;">
        <table style="width:100%;border-collapse:collapse;">
          <thead>
            <tr class="bg-gray-50 dark:bg-gray-800/60">
              <th class="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500">Time</th>
              <th class="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500">User</th>
              <th class="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500">Action</th>
              <th class="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500">Model</th>
              <th class="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500">Detail</th>
            </tr>
          </thead>
          <tbody>{act_rows}</tbody>
        </table>
      </div>
    </div>"""

    return base("Dashboard", content, models_slugs, "__dashboard__", title, prefix)


def model_list(model_admin, rows, total, page, per_page, search, models_slugs, flash="", admin_title="Shakti Admin", prefix="/admin"):
    from shakti.admin.helpers import fmt

    th_cls = "px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500 whitespace-nowrap"
    headers_html = "".join(f'<th class="{th_cls}">{f.replace("_"," ").title()}</th>' for f in model_admin.list_fields)

    rows_html = ""
    for obj in rows:
        cells = ""
        for i, f in enumerate(model_admin.list_fields):
            val = getattr(obj, f, None)
            if isinstance(val, bool):
                if val:
                    badge = '<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400">Yes</span>'
                else:
                    badge = '<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400">No</span>'
                cells += f'<td class="px-4 py-3">{badge}</td>'
            elif i == 0:
                cells += f'<td class="px-4 py-3 text-sm font-mono text-gray-400 dark:text-gray-500">{fmt(val)}</td>'
            elif i == 1:
                cells += f'<td class="px-4 py-3 text-sm font-semibold text-gray-900 dark:text-white">{fmt(val)}</td>'
            else:
                cells += f'<td class="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">{fmt(val)}</td>'

        rows_html += f"""
        <tr class="border-t border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors group">
          {cells}
          <td class="px-4 py-3 text-right" style="white-space:nowrap;">
            <span class="inline-flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
              <a href="{prefix}/{model_admin.slug}/{obj.id}"
                 class="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium rounded-lg bg-brand-50 dark:bg-brand-900/20 text-brand-600 dark:text-brand-400 hover:bg-brand-100 dark:hover:bg-brand-900/40 transition-colors">
                {ICONS['edit']} Edit
              </a>
              <form method="POST" action="{prefix}/{model_admin.slug}/{obj.id}/delete" style="display:inline;"
                    onsubmit="return confirm('Delete this {model_admin.name}? This cannot be undone.')">
                <button type="submit"
                        class="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium rounded-lg bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 hover:bg-red-100 dark:hover:bg-red-900/40 transition-colors">
                  {ICONS['trash']} Delete
                </button>
              </form>
            </span>
          </td>
        </tr>"""

    if not rows_html:
        rows_html = f'<tr><td colspan="{len(model_admin.list_fields)+1}" class="py-16 text-center text-sm text-gray-400 dark:text-gray-600">{"No results for &quot;" + search + "&quot;" if search else "No records yet"}</td></tr>'

    total_pages = max(1, (total + per_page - 1) // per_page)
    page_start = (page - 1) * per_page + 1 if total > 0 else 0
    page_end = min(page * per_page, total)

    btn_cls = "px-3 py-1.5 text-xs font-medium rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
    prev_btn = f'<a href="?page={page-1}&search={search}" class="{btn_cls}">&#8592; Prev</a>' if page > 1 else ""
    next_btn = f'<a href="?page={page+1}&search={search}" class="{btn_cls}">Next &#8594;</a>' if page < total_pages else ""

    flash_html = f"""
    <div x-data="{{show:true}}" x-show="show" x-init="setTimeout(()=>show=false,4000)" class="flex items-center gap-3 px-4 py-3 mb-5 rounded-xl border border-emerald-200 dark:border-emerald-800 bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-400 text-sm">
      {ICONS['check']}<span>{flash.replace('+', ' ')}</span>
      <button @click="show=false" class="ml-auto text-emerald-500 hover:text-emerald-700">{ICONS['x']}</button>
    </div>""" if flash else ""

    content = f"""
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
      <div>
        <h1 class="text-2xl font-bold text-gray-900 dark:text-white">{model_admin.name}</h1>
        <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">{total} total record{"s" if total != 1 else ""}</p>
      </div>
      <div class="flex items-center gap-3">
        <a href="{prefix}/{model_admin.slug}/export"
           class="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
          {ICONS['download']} Export CSV
        </a>
        <a href="{prefix}/{model_admin.slug}/new"
           class="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold rounded-lg bg-brand-600 hover:bg-brand-500 text-white transition-colors shadow-sm">
          {ICONS['plus']} New {model_admin.name}
        </a>
      </div>
    </div>

    {flash_html}

    <div class="mb-4">
      <form method="GET" style="position:relative;display:inline-block;width:320px;max-width:100%;">
        <span style="position:absolute;left:12px;top:50%;transform:translateY(-50%);" class="text-gray-400 dark:text-gray-500 pointer-events-none">{ICONS['search']}</span>
        <input name="search" value="{search}"
               placeholder="Search {', '.join(model_admin.search_fields) if model_admin.search_fields else model_admin.name}…"
               class="w-full pl-10 pr-4 py-2.5 text-sm rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-brand-500 transition-colors shadow-sm">
      </form>
    </div>

    <div class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl overflow-hidden shadow-sm">
      <div style="overflow-x:auto;">
        <table style="width:100%;border-collapse:collapse;">
          <thead>
            <tr class="bg-gray-50 dark:bg-gray-800/60">{headers_html}<th class="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500">Actions</th></tr>
          </thead>
          <tbody>{rows_html}</tbody>
        </table>
      </div>
      <div class="flex items-center justify-between px-5 py-3 border-t border-gray-100 dark:border-gray-800 bg-gray-50/50 dark:bg-gray-800/30">
        <p class="text-xs text-gray-500 dark:text-gray-400">
          Showing <span class="font-semibold text-gray-700 dark:text-gray-300">{page_start}–{page_end}</span> of <span class="font-semibold text-gray-700 dark:text-gray-300">{total}</span>
        </p>
        <div class="flex items-center gap-2">
          {prev_btn}
          <span class="px-3 py-1.5 text-xs font-semibold rounded-lg bg-brand-50 dark:bg-brand-900/30 text-brand-600 dark:text-brand-400">{page}/{total_pages}</span>
          {next_btn}
        </div>
      </div>
    </div>"""

    return base(model_admin.name, content, models_slugs, model_admin.slug, admin_title, prefix)


def model_form(model_admin, obj, models_slugs, errors=None, admin_title="Shakti Admin", prefix="/admin"):
    is_edit = obj is not None
    action = f"{prefix}/{model_admin.slug}/{obj.id}" if is_edit else f"{prefix}/{model_admin.slug}/new"
    title = f"Edit {model_admin.name}" if is_edit else f"New {model_admin.name}"

    input_cls_normal   = "w-full px-4 py-2.5 text-sm rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent transition-colors"
    input_cls_disabled = "w-full px-4 py-2.5 text-sm rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-100 dark:bg-gray-800/50 text-gray-400 dark:text-gray-500 cursor-not-allowed"

    fields_html = ""
    for f in model_admin.get_fields():
        val = getattr(obj, f["name"], "") if obj else ""
        if val is None:
            val = ""
        ro = f["readonly"]
        cls = input_cls_disabled if ro else input_cls_normal
        da = "disabled" if ro else ""

        if ro:
            badge = '<span class="ml-2 px-1.5 py-0.5 text-xs rounded bg-gray-100 dark:bg-gray-800 text-gray-400 font-normal normal-case tracking-normal">read-only</span>'
        elif f["nullable"]:
            badge = '<span class="ml-2 text-xs text-gray-400 dark:text-gray-600 font-normal normal-case tracking-normal">optional</span>'
        else:
            badge = ""

        if f["type"] == "textarea":
            inp = f'<textarea name="{f["name"]}" rows="4" {da} class="{cls}" style="resize:vertical;">{val}</textarea>'
        elif f["type"] == "checkbox":
            chk = "checked" if val else ""
            inp = f"""<label class="flex items-center gap-3 cursor-pointer">
              <input type="checkbox" name="{f['name']}" value="true" {chk} {da}
                     class="w-4 h-4 rounded border-gray-300 dark:border-gray-600 accent-indigo-600">
              <span class="text-sm text-gray-600 dark:text-gray-400">Enabled</span>
            </label>"""
        elif f["type"] in ("number", "decimal"):
            step = ' step="0.01"' if f["type"] == "decimal" else ""
            inp = f'<input type="number"{step} name="{f["name"]}" value="{val}" {da} class="{cls}">'
        elif f["type"] == "datetime":
            dt_val = val.strftime("%Y-%m-%dT%H:%M") if hasattr(val, "strftime") else ""
            inp = f'<input type="datetime-local" name="{f["name"]}" value="{dt_val}" {da} class="{cls}">'
        else:
            inp = f'<input type="text" name="{f["name"]}" value="{val}" {da} class="{cls}">'

        lbl = f["name"].replace("_", " ").title()
        fields_html += f"""
        <div>
          <label class="flex items-center text-xs font-semibold uppercase tracking-widest text-gray-500 dark:text-gray-400 mb-2">
            {lbl}{badge}
          </label>
          {inp}
        </div>"""

    err_html = ""
    if errors:
        items = "".join(f'<li class="flex items-center gap-2">{ICONS["x"]}{e}</li>' for e in errors)
        err_html = f'<ul class="p-4 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 text-sm space-y-1">{items}</ul>'

    delete_btn = ""
    if is_edit:
        delete_btn = f"""
        <form method="POST" action="{prefix}/{model_admin.slug}/{obj.id}/delete" style="margin-left:auto;"
              onsubmit="return confirm('Delete this record? This cannot be undone.')">
          <button type="submit" class="inline-flex items-center gap-2 text-sm text-red-500 hover:text-red-700 dark:hover:text-red-400 transition-colors">
            {ICONS['trash']} Delete
          </button>
        </form>"""

    content = f"""
    <div class="flex items-center gap-2 mb-6 text-sm text-gray-500 dark:text-gray-400">
      <a href="{prefix}/{model_admin.slug}" class="hover:text-gray-900 dark:hover:text-white transition-colors">{model_admin.name}</a>
      <span class="text-gray-300 dark:text-gray-700">/</span>
      <span class="text-gray-900 dark:text-white font-semibold">{"Edit #" + str(obj.id) if is_edit else "New"}</span>
    </div>

    <div style="max-width:560px;">
      <div class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl overflow-hidden shadow-sm">
        <div class="px-6 py-4 border-b border-gray-100 dark:border-gray-800 bg-gray-50/50 dark:bg-gray-800/30">
          <h1 class="text-base font-semibold text-gray-900 dark:text-white">{title}</h1>
          <p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{"Update the fields below and save your changes." if is_edit else "Fill in the details to create a new record."}</p>
        </div>
        <form method="POST" action="{action}" class="p-6" style="display:flex;flex-direction:column;gap:18px;">
          {err_html}
          {fields_html}
          <div class="flex items-center gap-3 pt-2 border-t border-gray-100 dark:border-gray-800">
            <button type="submit"
                    class="inline-flex items-center gap-2 px-5 py-2.5 text-sm font-semibold rounded-xl bg-brand-600 hover:bg-brand-500 text-white transition-colors shadow-sm">
              {ICONS['check']} {"Save Changes" if is_edit else "Create " + model_admin.name}
            </button>
            <a href="{prefix}/{model_admin.slug}"
               class="inline-flex items-center gap-2 px-5 py-2.5 text-sm font-medium rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
              Cancel
            </a>
            {delete_btn}
          </div>
        </form>
      </div>
    </div>"""

    return base(title, content, models_slugs, model_admin.slug, admin_title, prefix)
