"""Value formatting, CSV export, activity log."""

from __future__ import annotations

import csv
import io
from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


def fmt(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "✓" if value else "✗"
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M")
    s = str(value)
    return s[:60] + "…" if len(s) > 60 else s


def to_csv(headers: list[str], rows: list[list[Any]]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(headers)
    for row in rows:
        w.writerow([fmt(v) for v in row])
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
