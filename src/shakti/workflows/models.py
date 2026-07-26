"""Job model and status definitions."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable


class JobStatus(str, Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"
    RETRYING  = "retrying"
    CANCELLED = "cancelled"


@dataclass
class Job:
    id: str
    name: str
    func: Callable
    kwargs: dict[str, Any]
    status: JobStatus = JobStatus.PENDING
    result: Any = None
    error: str | None = None
    retries: int = 0
    max_retries: int = 3
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None
    finished_at: datetime | None = None
    scheduled_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "retries": self.retries,
            "max_retries": self.max_retries,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "scheduled_at": self.scheduled_at.isoformat() if self.scheduled_at else None,
            "duration_ms": (
                int((self.finished_at - self.started_at).total_seconds() * 1000)
                if self.started_at and self.finished_at else None
            ),
        }


@dataclass
class ScheduledJob:
    name: str
    func: Callable
    interval_seconds: float
    kwargs: dict[str, Any] = field(default_factory=dict)
    last_run: datetime | None = None
    run_count: int = 0
    enabled: bool = True
