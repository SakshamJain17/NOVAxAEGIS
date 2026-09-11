from __future__ import annotations

from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PlanActionType(str, Enum):
    RESPOND = "respond"
    TOOL = "tool"


class PlanAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=100)
    type: PlanActionType

    tool_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
    )

    arguments: dict[str, Any] = Field(default_factory=dict)

    rationale: str = Field(
        default="",
        max_length=2_000,
    )

    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
    )


class AgentPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: UUID
    task_version: int = Field(ge=1)

    objective: str = Field(
        min_length=1,
        max_length=10_000,
    )

    actions: list[PlanAction] = Field(
        min_length=1,
        max_length=20,
    )

    final_response: str | None = Field(
        default=None,
        max_length=20_000,
    )

    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
    )