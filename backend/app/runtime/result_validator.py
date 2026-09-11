from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from app.runtime.event_bus import EventBus
from app.runtime.events import Event, EventType
from app.runtime.results import ToolResult
from app.runtime.tasks import TaskContext


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ValidationStatus(str, Enum):
    ACCEPTED = "accepted"
    STALE = "stale"
    INVALID = "invalid"
    FAILED = "failed"


@dataclass(slots=True, frozen=True)
class ValidationResult:
    """
    Immutable result produced by the AEGIS validation layer.

    A tool result is never trusted simply because the tool returned
    successfully. It must still belong to the current task version,
    correspond to the current task, and contain usable data.
    """

    status: ValidationStatus
    task_id: str
    task_version: int
    result_id: str
    valid: bool
    reason: str
    data: Any = None
    validated_at: datetime = field(default_factory=utc_now)

    @property
    def accepted(self) -> bool:
        return self.status == ValidationStatus.ACCEPTED

    @property
    def stale(self) -> bool:
        return self.status == ValidationStatus.STALE


class ResultValidator:
    """
    Trust boundary between tool execution and agent reasoning.

    Validation order:

        task identity
            ↓
        version freshness
            ↓
        cancellation state
            ↓
        tool success
            ↓
        payload validity
            ↓
        ACCEPT / REJECT
    """

    def __init__(self, event_bus: EventBus) -> None:
        self.event_bus = event_bus

    async def validate(
        self,
        task: TaskContext,
        result: ToolResult,
    ) -> ValidationResult:

        await self.event_bus.publish(
            Event(
                type=EventType.RESULT_VALIDATION_STARTED,
                task_id=task.task_id,
                task_version=task.version,
                payload={
                    "result_id": result.result_id,
                },
                source="result_validator",
            )
        )

        # --------------------------------------------------------------
        # TASK IDENTITY
        # --------------------------------------------------------------

        if result.task_id != task.task_id:
            return await self._reject(
                task=task,
                result=result,
                status=ValidationStatus.INVALID,
                reason=(
                    "Tool result belongs to a different task."
                ),
            )

        # --------------------------------------------------------------
        # VERSION / STALENESS
        # --------------------------------------------------------------

        if result.version != task.version:
            return await self._reject(
                task=task,
                result=result,
                status=ValidationStatus.STALE,
                reason=(
                    "Tool result belongs to an outdated task version."
                ),
            )

        if result.is_stale:
            return await self._reject(
                task=task,
                result=result,
                status=ValidationStatus.STALE,
                reason="Tool explicitly marked its result as stale.",
            )

        # --------------------------------------------------------------
        # CANCELLATION
        # --------------------------------------------------------------

        if task.cancellation_requested:
            return await self._reject(
                task=task,
                result=result,
                status=ValidationStatus.STALE,
                reason=(
                    "Task cancellation was requested before "
                    "result validation completed."
                ),
            )

        # --------------------------------------------------------------
        # TOOL FAILURE
        # --------------------------------------------------------------

        if not result.success:
            return await self._reject(
                task=task,
                result=result,
                status=ValidationStatus.FAILED,
                reason=result.error or "Tool execution failed.",
            )

        # --------------------------------------------------------------
        # PAYLOAD VALIDITY
        # --------------------------------------------------------------

        if result.data is None:
            return await self._reject(
                task=task,
                result=result,
                status=ValidationStatus.INVALID,
                reason="Tool returned no usable data.",
            )

        # --------------------------------------------------------------
        # ACCEPT
        # --------------------------------------------------------------

        validation = ValidationResult(
            status=ValidationStatus.ACCEPTED,
            task_id=task.task_id,
            task_version=task.version,
            result_id=result.result_id,
            valid=True,
            reason="Result passed AEGIS validation.",
            data=result.data,
        )

        await self.event_bus.publish(
            Event(
                type=EventType.RESULT_ACCEPTED,
                task_id=task.task_id,
                task_version=task.version,
                payload={
                    "result_id": result.result_id,
                    "reason": validation.reason,
                },
                source="result_validator",
            )
        )

        return validation

    async def _reject(
        self,
        *,
        task: TaskContext,
        result: ToolResult,
        status: ValidationStatus,
        reason: str,
    ) -> ValidationResult:

        validation = ValidationResult(
            status=status,
            task_id=task.task_id,
            task_version=task.version,
            result_id=result.result_id,
            valid=False,
            reason=reason,
            data=result.data,
        )

        event_type = (
            EventType.TOOL_RESULT_STALE
            if status == ValidationStatus.STALE
            else EventType.RESULT_REJECTED
        )

        await self.event_bus.publish(
            Event(
                type=event_type,
                task_id=task.task_id,
                task_version=task.version,
                payload={
                    "result_id": result.result_id,
                    "status": status.value,
                    "reason": reason,
                },
                source="result_validator",
            )
        )

        return validation