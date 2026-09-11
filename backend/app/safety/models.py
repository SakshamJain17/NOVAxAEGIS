from __future__ import annotations

from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Decision(str, Enum):
    ALLOW = "allow"
    APPROVAL_REQUIRED = "approval_required"
    BLOCK = "block"


class ActionProposal(BaseModel):
    task_id: UUID
    task_version: int

    tool_name: str

    arguments: dict[str, Any] = Field(
        default_factory=dict
    )

    rationale: str = ""

    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
    )


class RiskAssessment(BaseModel):
    level: RiskLevel
    decision: Decision

    score: float = Field(
        ge=0.0,
        le=1.0,
    )

    reasons: list[str] = Field(
        default_factory=list
    )

    requires_human_confirmation: bool = False

    reversible: bool = True
    user_authorized: bool = False