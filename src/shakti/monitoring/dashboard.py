"""Monitoring dashboard HTML."""

from __future__ import annotations

from typing import Any


def _status_badge(status: str) -> str:
    colors = {
        "healthy":   "bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400",
        "degraded":  "bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400",
        "unhealthy": "bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400",
    }
    c = colors.get(status, "bg-gray-100 text-gray-600")
    return f'<span class="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-semibold {c}">{status.title()}</span>'


def _method_badge(method: str) -> str:
    colors = {
        "GET":    "bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400",
        "POST":   "bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400",
        "PUT":    "bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400",
        "PATCH":  "bg-violet-100 dark:bg-violet-900/30 text-violet-700 dark:text-violet-400",
        "DELETE": "bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400",
    }
    c = colors.get(method, "bg-gray-100 text-gray-600")
    return f'<span class="inline-block px-2 py-0.5 rounded text-xs font-bold {c}">{method}</span>'


def _status_color(code: int) -> str:
    if code < 300:
        return "text-emerald-600 dark:text-emerald-400"
    if code < 400:
        return "text-blue-600 dark:text-blue-400"
    if code < 500:
        return "text-amber-600 dark:text-amber-400"
    return "text-red-600 dark:text-red-400"


def render_dashboard(
    metrics: dict[str, Any],
    system: dict[str, Any],
    health: list[dict[str, Any]],
    endpoints: list[dict[str, Any]],
    recent: list[dict[str, Any]],
    overall_status: str,
    title: str = "Shakti Monitor",
) -> str:
    # Health checks
    health_rows = ""
    for h in health:
        health_rows += f"""
        <tr class="border-t border-gray-100 dark:border-gray-800">
          <td class="px-5 py-3 text-sm font-medium text-gray-900 dark:text-white">{h['name']}</td>
          <td class="px-5 py-3">{_status_badge(h['status'])}</td>
          <td class="px-5 py-3 text-sm text-gray-500 dark:text-gray-400">{h.get('message','')}</td>
          <td class="px-5 py-3 text-xs text-gray-400 font-mono">{h.get('duration_ms',0):.1f}ms</td>
        </tr>"""
    if not health_rows:
        health_rows = '<tr><td colspan="4" class="py-8 text-center text-sm text-gray-400">No health checks registered</td></tr>'

    # Endpoint rows
    ep_rows = ""
    for ep in endpoints:
        err_pct = (ep["errors"] / ep["count"] * 100) if ep["count"] else 0
        ep_rows += f"""
        <tr class="border-t border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/40">
          <td class="px-4 py-3">{_method_badge(ep['method'])}</td>
          <td class="px-4 py-3 text-sm font-mono text-gray-700 dark:text-gray-300">{ep['path']}</td>
          <td class="px-4 py-3 text-sm text-gray-600 dark:text-gray-400 text-right">{ep['count']}</td>
          <td class="px-4 py-3 text-sm text-right font-mono text-gray-600 dark:text-gray-400">{ep['avg_ms']}ms</td>
          <td class="px-4 py-3 text-sm text-right font-mono text-gray-600 dark:text-gray-400">{ep['max_ms']}ms</td>
          <td class="px-4 py-3 text-sm text-right {'text-red-500' if err_pct > 5 else 'text-gray-400 dark:text-gray-600'}">{err_pct:.1f}%</td>
        </tr>"""
    if not ep_rows:
        ep_rows = '<tr><td colspan="6" class="py-8 text-center text-sm text-gray-400">No requests recorded yet</td></tr>'

    # Recent requests
    recent_rows = ""
    for r in recent:
        recent_rows += f"""
        <tr class="border-t border-gray-100 dark:border-gray-800">
          <td class="px-4 py-2.5 text-xs font-mono text-gray-400">{r['time']}</td>
          <td class="px-4 py-2.5">{_method_badge(r['method'])}</td>
          <td class="px-4 py-2.5 text-sm font-mono text-gray-600 dark:text-gray-400">{r['path']}</td>
          <td class="px-4 py-2.5 text-sm font-bold {_status_color(r['status'])}">{r['status']}</td>
          <td class="px-4 py-2.5 text-xs font-mono text-gray-400">{r['duration_ms']}ms</td>
        </tr>"""
    if not recent_rows:
        recent_rows = '<tr><td colspan="5" class="py-8 text-center text-sm text-gray-400">No requests yet</td></tr>'

    # System gauges
    cpu = system.get("cpu_pct", 0)
    mem = system.get("memory_pct", 0)
    disk = system.get("disk_pct", 0)

    def gauge_color(pct):
        if pct < 60: return "bg-emerald-500"
        if pct < 80: return "bg-amber-500"
        return "bg-red-500"

    rt = metrics.get("response_time_ms", {})

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="10">
<title>{title}</title>
<script src="https://cdn.tailwindcss.com"></script>
<script>
tailwind.config = {{
  darkMode: 'class',
  theme: {{ extend: {{ colors: {{ brand: {{ 500:'#6366f1',600:'#4f46e5' }} }} }} }}
}}
</script>
<script>
(function(){{
  var t = localStorage.getItem('pf_theme') || 'dark';
  if(t==='dark') document.documentElement.classList.add('dark');
}})();
</script>
<style>body{{font-family:'Inter',ui-sans-serif,system-ui,sans-serif}}</style>
</head>
<body class="bg-gray-50 dark:bg-gray-950 text-gray-900 dark:text-gray-100 min-h-screen">

<!-- Header -->
<header class="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 sticky top-0 z-20"
        style="height:56px;display:flex;align-items:center;justify-content:space-between;padding:0 24px;">
  <div class="flex items-center gap-3">
    <div class="flex items-center justify-center rounded-lg bg-brand-600 text-white text-xs font-bold" style="width:28px;height:28px;">PF</div>
    <span class="font-semibold text-gray-900 dark:text-white">{title}</span>
    <span class="text-xs text-gray-400">· auto-refreshes every 10s</span>
  </div>
  <div class="flex items-center gap-3">
    {_status_badge(overall_status)}
    <button onclick="location.reload()" class="px-3 py-1.5 text-xs font-medium rounded-lg border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">Refresh</button>
    <button onclick="var d=document.documentElement;var dark=d.classList.toggle('dark');localStorage.setItem('pf_theme',dark?'dark':'light')"
            class="px-3 py-1.5 text-xs font-medium rounded-lg border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
      Toggle Theme
    </button>
  </div>
</header>

<div class="p-6 space-y-6">

  <!-- Top stats -->
  <div class="grid gap-4" style="grid-template-columns:repeat(auto-fill,minmax(180px,1fr));">
    <div class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-5">
      <p class="text-xs font-semibold uppercase tracking-widest text-gray-400">Uptime</p>
      <p class="text-2xl font-bold text-brand-600 dark:text-brand-400 mt-1">{metrics.get('uptime_human','—')}</p>
    </div>
    <div class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-5">
      <p class="text-xs font-semibold uppercase tracking-widest text-gray-400">Total Requests</p>
      <p class="text-2xl font-bold text-gray-900 dark:text-white mt-1">{metrics.get('total_requests',0)}</p>
    </div>
    <div class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-5">
      <p class="text-xs font-semibold uppercase tracking-widest text-gray-400">Avg Response</p>
      <p class="text-2xl font-bold text-emerald-600 dark:text-emerald-400 mt-1">{rt.get('avg',0)}ms</p>
    </div>
    <div class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-5">
      <p class="text-xs font-semibold uppercase tracking-widest text-gray-400">P95 Response</p>
      <p class="text-2xl font-bold text-amber-600 dark:text-amber-400 mt-1">{rt.get('p95',0)}ms</p>
    </div>
    <div class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-5">
      <p class="text-xs font-semibold uppercase tracking-widest text-gray-400">Error Rate</p>
      <p class="text-2xl font-bold {'text-red-600 dark:text-red-400' if metrics.get('error_rate_pct',0) > 1 else 'text-gray-900 dark:text-white'} mt-1">{metrics.get('error_rate_pct',0)}%</p>
    </div>
    <div class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-5">
      <p class="text-xs font-semibold uppercase tracking-widest text-gray-400">Active</p>
      <p class="text-2xl font-bold text-gray-900 dark:text-white mt-1">{metrics.get('active_requests',0)}</p>
    </div>
  </div>

  <!-- System + Health -->
  <div class="grid gap-6" style="grid-template-columns:1fr 1fr;">

    <!-- System Resources -->
    <div class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl overflow-hidden">
      <div class="px-5 py-4 border-b border-gray-100 dark:border-gray-800">
        <h2 class="text-sm font-semibold text-gray-900 dark:text-white">System Resources</h2>
      </div>
      <div class="p-5 space-y-4">
        <div>
          <div class="flex justify-between mb-1.5">
            <span class="text-xs font-medium text-gray-600 dark:text-gray-400">CPU</span>
            <span class="text-xs font-bold text-gray-900 dark:text-white">{cpu:.1f}%</span>
          </div>
          <div class="h-2 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
            <div class="h-full {gauge_color(cpu)} rounded-full transition-all" style="width:{min(cpu,100):.1f}%"></div>
          </div>
        </div>
        <div>
          <div class="flex justify-between mb-1.5">
            <span class="text-xs font-medium text-gray-600 dark:text-gray-400">Memory — {system.get('memory_used_mb',0):.0f}MB / {system.get('memory_total_mb',0):.0f}MB</span>
            <span class="text-xs font-bold text-gray-900 dark:text-white">{mem:.1f}%</span>
          </div>
          <div class="h-2 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
            <div class="h-full {gauge_color(mem)} rounded-full transition-all" style="width:{min(mem,100):.1f}%"></div>
          </div>
        </div>
        <div>
          <div class="flex justify-between mb-1.5">
            <span class="text-xs font-medium text-gray-600 dark:text-gray-400">Disk — {system.get('disk_used_gb',0):.1f}GB / {system.get('disk_total_gb',0):.1f}GB</span>
            <span class="text-xs font-bold text-gray-900 dark:text-white">{disk:.1f}%</span>
          </div>
          <div class="h-2 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
            <div class="h-full {gauge_color(disk)} rounded-full transition-all" style="width:{min(disk,100):.1f}%"></div>
          </div>
        </div>
        <div class="pt-2 border-t border-gray-100 dark:border-gray-800 grid grid-cols-2 gap-3">
          <div>
            <p class="text-xs text-gray-400">Python</p>
            <p class="text-xs font-semibold text-gray-700 dark:text-gray-300 mt-0.5">{system.get('python_version','—')}</p>
          </div>
          <div>
            <p class="text-xs text-gray-400">Platform</p>
            <p class="text-xs font-semibold text-gray-700 dark:text-gray-300 mt-0.5">{system.get('platform','—')}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Health Checks -->
    <div class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl overflow-hidden">
      <div class="px-5 py-4 border-b border-gray-100 dark:border-gray-800">
        <h2 class="text-sm font-semibold text-gray-900 dark:text-white">Health Checks</h2>
      </div>
      <div style="overflow-x:auto;">
        <table style="width:100%;border-collapse:collapse;">
          <thead>
            <tr class="bg-gray-50 dark:bg-gray-800/60">
              <th class="px-5 py-2.5 text-left text-xs font-semibold uppercase tracking-wider text-gray-400">Check</th>
              <th class="px-5 py-2.5 text-left text-xs font-semibold uppercase tracking-wider text-gray-400">Status</th>
              <th class="px-5 py-2.5 text-left text-xs font-semibold uppercase tracking-wider text-gray-400">Message</th>
              <th class="px-5 py-2.5 text-left text-xs font-semibold uppercase tracking-wider text-gray-400">Time</th>
            </tr>
          </thead>
          <tbody>{health_rows}</tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- Endpoints -->
  <div class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl overflow-hidden">
    <div class="px-5 py-4 border-b border-gray-100 dark:border-gray-800">
      <h2 class="text-sm font-semibold text-gray-900 dark:text-white">Endpoints</h2>
    </div>
    <div style="overflow-x:auto;">
      <table style="width:100%;border-collapse:collapse;">
        <thead>
          <tr class="bg-gray-50 dark:bg-gray-800/60">
            <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-400">Method</th>
            <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-400">Path</th>
            <th class="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-400">Requests</th>
            <th class="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-400">Avg</th>
            <th class="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-400">Max</th>
            <th class="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-400">Error%</th>
          </tr>
        </thead>
        <tbody>{ep_rows}</tbody>
      </table>
    </div>
  </div>

  <!-- Recent Requests -->
  <div class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl overflow-hidden">
    <div class="px-5 py-4 border-b border-gray-100 dark:border-gray-800">
      <h2 class="text-sm font-semibold text-gray-900 dark:text-white">Recent Requests</h2>
    </div>
    <div style="overflow-x:auto;">
      <table style="width:100%;border-collapse:collapse;">
        <thead>
          <tr class="bg-gray-50 dark:bg-gray-800/60">
            <th class="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wider text-gray-400">Time</th>
            <th class="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wider text-gray-400">Method</th>
            <th class="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wider text-gray-400">Path</th>
            <th class="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wider text-gray-400">Status</th>
            <th class="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wider text-gray-400">Duration</th>
          </tr>
        </thead>
        <tbody>{recent_rows}</tbody>
      </table>
    </div>
  </div>

</div>

<footer class="px-6 py-3 border-t border-gray-200 dark:border-gray-800 text-xs text-gray-400 dark:text-gray-600">
  Shakti Monitor · Built with Shakti Framework
</footer>
</body>
</html>"""
