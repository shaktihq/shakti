"""MkDocs build hooks.

- Registers a `tojson` Jinja filter (not available in vanilla Jinja2 —
  only Flask adds one) so theme overrides can safely embed page data
  into JSON-LD <script> blocks without hand-rolled escaping.
- Exposes the real installed package version as `config.extra.shakti_version`
  for the SoftwareApplication JSON-LD block, read from source so it can't
  drift out of sync with an actual release.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

# URLs (relative to site root) whose page front matter set `robots: noindex`
# — collected during the build so on_post_build can also drop them from
# sitemap.xml. The noindex meta tag is the authoritative signal either way;
# this just keeps the sitemap from listing pages we're telling crawlers to
# skip, which is the cleaner practice Google recommends.
_noindexed_urls: set[str] = set()


def _tojson_filter(value: Any) -> str:
    return json.dumps(value)


def on_env(env: Any, config: Any, files: Any) -> Any:
    env.filters["tojson"] = _tojson_filter
    return env


def on_config(config: Any) -> Any:
    about = Path(config["docs_dir"]).parent / "src" / "shakti" / "__about__.py"
    version = "unknown"
    if about.is_file():
        match = re.search(r'__version__\s*=\s*"([^"]+)"', about.read_text())
        if match:
            version = match.group(1)
    config["extra"]["shakti_version"] = version
    return config


def on_page_context(context: Any, page: Any, config: Any, nav: Any) -> Any:
    robots = (page.meta or {}).get("robots", "")
    if "noindex" in robots:
        _noindexed_urls.add(config["site_url"].rstrip("/") + "/" + page.url)
    return context


def on_post_build(config: Any) -> None:
    if not _noindexed_urls:
        return
    sitemap_path = Path(config["site_dir"]) / "sitemap.xml"
    if not sitemap_path.is_file():
        return
    text = sitemap_path.read_text(encoding="utf-8")
    for url in _noindexed_urls:
        text = re.sub(
            r"<url>\s*<loc>" + re.escape(url) + r"</loc>.*?</url>\s*",
            "",
            text,
            flags=re.S,
        )
    sitemap_path.write_text(text, encoding="utf-8")
