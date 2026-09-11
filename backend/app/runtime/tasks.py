from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TaskStatus(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    INTERRUPTED = "interrupted"
    RECONCILING = "reconciling"
    RECOVERING = "recovering"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(slots=True)
class TaskSnapshot:
    task_id: UUID
    version: int
    status: TaskStatus

    instruction: str
    constraints: dict[str, Any]

    created_at: datetime
    updated_at: datetime

    parent_version: int | None = None


@dataclass
class TaskContext:
    
    """
    Mutable runtime state for one logical user task.

    A task's version changes whenever the user's intent changes
    materially enough to invalidate previous work.
    """

    instruction: str
    constraints: dict[str, Any] = field(default_factory=dict)

    task_id: UUID = field(default_factory=uuid4)

    version: int = 1
    status: TaskStatus = TaskStatus.CREATED

    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    parent_version: int | None = None

    metadata: dict[str, Any] = field(default_factory=dict)

    _cancel_event: asyncio.Event = field(
        default_factory=asyncio.Event,
        repr=False,
    )

    def touch(self) -> None:
        self.updated_at = utc_now()

    def snapshot(self) -> TaskSnapshot:
        return TaskSnapshot(
            task_id=self.task_id,
            version=self.version,
            status=self.status,
            instruction=self.instruction,
            constraints=dict(self.constraints),
            created_at=self.created_at,
            updated_at=self.updated_at,
            parent_version=self.parent_version,
        )

    def is_current_version(self, version: int) -> bool:
        return self.version == version

    def invalidate(self) -> int:
        """
        Increment task version.

        Any tool result, plan, or response associated with the
        previous version becomes potentially stale.
        """

        previous_version = self.version

        self.parent_version = previous_version
        self.version += 1
        self.touch()

        return self.version

    def update_instruction(
        self,
        instruction: str,
        constraints: dict[str, Any] | None = None,
    ) -> int:
        self.invalidate()

        self.instruction = instruction

        if constraints is not None:
            self.constraints = dict(constraints)

        self.status = TaskStatus.RECONCILING
        self.touch()

        return self.version

    def cancel(self) -> None:
        self._cancel_event.set()
        self.status = TaskStatus.CANCELLED
        self.touch()

    def reset_cancellation(self) -> None:
        self._cancel_event = asyncio.Event()

    def cancellation_requested(self) -> bool:
        return self._cancel_event.is_set()
        def append_metadata_list(
        self,
        key: str,
        value: dict[str, Any],
        *,
        max_items: int = 50,
    ) -> None:
            collection = self.metadata.setdefault(key, [])

        if not isinstance(collection, list):
            collection = []
            self.metadata[key] = collection

        collection.append(dict(value))

        if len(collection) > max_items:
            del collection[:-max_items]

        self.touch()

    def get_metadata_list(
        self,
        key: str,
    ) -> list[dict[str, Any]]:
        value = self.metadata.get(key, [])

        if not isinstance(value, list):
            return []

        return [
            dict(item)
            for item in value
            if isinstance(item, dict)
        ]