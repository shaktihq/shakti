"""Value formatting, CSV export, activity log."""

from __future__ import annotations

import csv
import html
import io
from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


def esc(value: Any) -> str:
    """HTML-escape a value for safe interpolation into admin UI templates.

    The admin UI builds pages by string interpolation, not a templating
    engine with autoescaping — anything sourced from the database or a
    request (field values, search queries, flash messages, activity log
    entries) must be passed through this before landing in HTML, or a
    value any regular app user can set becomes stored/reflected XSS
    against the admin's authenticated session.
    """
    return html.escape(str(value), quote=True)


def fmt(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "✓" if value else "✗"
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M")
    s = str(value)
    return s[:60] + "…" if len(s) > 60 else s


_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _sanitize_csv_cell(value: str) -> str:
    """Neutralize spreadsheet formula injection (CWE-1236).

    Excel/Sheets/LibreOffice treat a cell starting with =, +, -, @, tab, or
    CR as a formula. Exported data often includes values end users typed
    into the app (not the admin), so prefix such cells with a single quote
    — the standard mitigation — to force them to render as plain text.
    """
    if value.startswith(_FORMULA_PREFIXES):
        return "'" + value
    return value


def to_csv(headers: list[str], rows: list[list[Any]]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(headers)
    for row in rows:
        w.writerow([_sanitize_csv_cell(fmt(v)) for v in row])
    return buf.getvalue()


@dataclass
class ActivityEntry:
    timestamp: datetime
    username: str
    action: str   # created | updated | deleted
    model: str
    record_id: int | None
    detail: str


class ActivityLog:
    def __init__(self, maxlen: int = 200) -> None:
        self._log: deque[ActivityEntry] = deque(maxlen=maxlen)

    def record(
        self,
        username: str,
        action: str,
        model: str,
        record_id: int | None = None,
        detail: str = "",
    ) -> None:
        self._log.appendleft(
            ActivityEntry(
                timestamp=datetime.now(UTC),
                username=username,
                action=action,
                model=model,
                record_id=record_id,
                detail=detail,
            )
        )

    def recent(self, n: int = 20) -> list[ActivityEntry]:
        return list(self._log)[:n]


# Global activity log instance shared across admin instances
activity_log = ActivityLog()
