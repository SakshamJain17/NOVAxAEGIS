from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class EventType(str, Enum):
    # Input
    USER_INPUT = "user.input"
    USER_INTERRUPT = "user.interrupt"
    USER_APPROVAL = "user.approval"
    USER_CANCELLATION = "user.cancellation"

    # Agent lifecycle
    TASK_CREATED = "task.created"
    TASK_STARTED = "task.started"
    STATE_CHANGED = "agent.state_changed"

    # Planning
    INTENT_DETECTED = "agent.intent_detected"
    PLAN_CREATED = "agent.plan_created"
    PLAN_INVALIDATED = "agent.plan_invalidated"

    # Safety
    RISK_ASSESSED = "safety.risk_assessed"
    APPROVAL_REQUIRED = "safety.approval_required"
    ACTION_BLOCKED = "safety.action_blocked"
    AWAITING_APPROVAL = "safety.awaiting_approval"

    # Tools
    TOOL_REQUESTED = "tool.requested"
    TOOL_STARTED = "tool.started"
    TOOL_COMPLETED = "tool.completed"
    TOOL_FAILED = "tool.failed"
    TOOL_CANCELLED = "tool.cancelled"
    TOOL_RESULT_STALE = "tool.result_stale"

    # Recovery
    TASK_INTERRUPTED = "task.interrupted"
    TASK_RECONCILING = "task.reconciling"
    RECOVERY_STARTED = "recovery.started"
    RECOVERY_COMPLETED = "recovery.completed"
    TASK_FAILED = "task.failed"
    TASK_CANCELLED = "task.cancelled"

    # Voice
    SPEECH_STARTED = "voice.speech_started"
    SPEECH_CHUNK = "voice.speech_chunk"
    SPEECH_INTERRUPTED = "voice.speech_interrupted"
    SPEECH_COMPLETED = "voice.speech_completed"

    # Observability
    AUDIT = "system.audit"
    RESULT_VALIDATION_STARTED = "result.validation_started"
    RESULT_ACCEPTED = "result.accepted"
    RESULT_REJECTED = "result.rejected"

    REPLAN_STARTED = "agent.replan_started"
    REPLAN_COMPLETED = "agent.replan_completed"

@dataclass(slots=True, frozen=True)
class Event:
    type: EventType
    task_id: UUID | None = None
    task_version: int | None = None

    payload: dict[str, Any] = field(default_factory=dict)

    event_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=utc_now)

    correlation_id: UUID = field(default_factory=uuid4)

    source: str = "aegis"