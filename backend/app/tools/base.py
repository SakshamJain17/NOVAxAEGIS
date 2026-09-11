from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import UUID


class ToolRisk(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ToolCategory(str, Enum):
    INFORMATION = "information"
    COMPUTATION = "computation"
    FILESYSTEM = "filesystem"
    BROWSER = "browser"
    SYSTEM = "system"
    COMMUNICATION = "communication"


@dataclass(frozen=True, slots=True)
class ToolMetadata:
    name: str
    description: str
    category: ToolCategory
    risk: ToolRisk

    requires_approval: bool = False
    supports_cancellation: bool = True

    timeout_seconds: float = 30.0

    allowed_environments: tuple[str, ...] = (
        "development",
        "production",
    )


@dataclass(slots=True)
class ToolContext:
    task_id: UUID
    task_version: int

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    cancellation_requested: Any = None

    def is_cancelled(self) -> bool:
        if self.cancellation_requested is None:
            return False

        return bool(
            self.cancellation_requested.is_set()
        )


@dataclass(slots=True)
class ToolExecutionResult:
    tool_name: str
    task_id: UUID
    task_version: int

    success: bool

    data: Any = None
    error: str | None = None

    stale: bool = False
    cancelled: bool = False


class BaseTool(ABC):

    metadata: ToolMetadata

    @abstractmethod
    async def execute(
        self,
        arguments: dict[str, Any],
        context: ToolContext,
    ) -> ToolExecutionResult:
        """
        Execute the tool.

        Implementations MUST:
        - respect cancellation
        - never bypass safety checks
        - return structured results
        - never raise user-facing errors directly
        """
        raise NotImplementedError

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.metadata.name,
            "description": self.metadata.description,
            "category": self.metadata.category.value,
            "risk": self.metadata.risk.value,
            "requires_approval": (
                self.metadata.requires_approval
            ),
            "supports_cancellation": (
                self.metadata.supports_cancellation
            ),
        }