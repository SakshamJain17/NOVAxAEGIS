from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True, frozen=True)
class ToolResult:
    tool_name: str
    task_id: UUID
    task_version: int

    success: bool
    data: Any = None
    error: str | None = None

    started_at: datetime = field(default_factory=utc_now)
    completed_at: datetime = field(default_factory=utc_now)

    result_id: UUID = field(default_factory=uuid4)

    @property
    def duration_ms(self) -> float:
        return (
            self.completed_at - self.started_at
        ).total_seconds() * 1000

    def is_stale(self, current_task_version: int) -> bool:
        return self.task_version != current_task_version