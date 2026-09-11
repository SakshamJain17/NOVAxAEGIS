from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.runtime.event_bus import EventBus
from app.runtime.events import Event, EventType
from app.runtime.tasks import TaskContext, TaskStatus
from app.safety.approvals import (
    ApprovalManager,
)
from app.safety.engine import SafetyEngine
from app.safety.models import (
    ActionProposal,
    Decision,
)
from app.tools.base import ToolExecutionResult
from app.tools.executor import ToolExecutor


@dataclass(slots=True, frozen=True)
class ActionDecision:
    """
    Result of the control-plane decision.

    Separating the decision from raw tool execution gives
    the UI, audit layer and agent runtime a common contract.
    """

    decision: Decision

    request_id: UUID | None = None

    reason: str | None = None


class ActionGate:

    def __init__(
        self,
        safety: SafetyEngine,
        executor: ToolExecutor,
        approvals: ApprovalManager,
        event_bus: EventBus,
    ) -> None:

        self.safety = safety
        self.executor = executor
        self.approvals = approvals
        self.event_bus = event_bus

    async def execute(
        self,
        task: TaskContext,
        tool_name: str,
        arguments: dict,
        confidence: float,
        rationale: str = "",
    ) -> ToolExecutionResult:

        # --------------------------------------------------
        # VERSION SNAPSHOT
        # --------------------------------------------------

        task_version = task.version

        proposal = ActionProposal(
            task_id=task.task_id,
            task_version=task_version,
            tool_name=tool_name,
            arguments=arguments,
            confidence=confidence,
            rationale=rationale,
        )

        # --------------------------------------------------
        # SAFETY EVALUATION
        # --------------------------------------------------

        assessment = await self.safety.evaluate(
            proposal
        )

        # --------------------------------------------------
        # BLOCK
        # --------------------------------------------------

        if assessment.decision == Decision.BLOCK:

            return ToolExecutionResult(
                tool_name=tool_name,
                task_id=task.task_id,
                task_version=task_version,
                success=False,
                error=(
                    "AEGIS safety policy blocked "
                    "this action."
                ),
            )

        # --------------------------------------------------
        # HUMAN APPROVAL
        # --------------------------------------------------

        if (
            assessment.decision
            == Decision.APPROVAL_REQUIRED
        ):

            task.status = (
                TaskStatus.WAITING_APPROVAL
            )
            task.touch()

            # Create approval asynchronously.

            approval_task = (
                __import__("asyncio")
                .create_task(
                    self.approvals.request(
                        task_id=task.task_id,
                        task_version=task_version,
                        tool_name=tool_name,
                        arguments=arguments,
                    )
                )
            )

            # Give the ApprovalManager a scheduling
            # opportunity so the request exists before
            # the event reaches the UI.

            await __import__("asyncio").sleep(0)

            pending = await self.approvals.pending(
                task_id=task.task_id
            )

            matching = [
                request
                for request in pending
                if (
                    request.task_version
                    == task_version
                    and request.tool_name
                    == tool_name
                    and request._future is not None
                )
            ]

            if not matching:
                approval_task.cancel()

                return ToolExecutionResult(
                    tool_name=tool_name,
                    task_id=task.task_id,
                    task_version=task_version,
                    success=False,
                    error=(
                        "Failed to create approval request."
                    ),
                )

            request = matching[-1]

            await self.event_bus.publish(
                Event(
                    type=EventType.AWAITING_APPROVAL,
                    task_id=task.task_id,
                    task_version=task_version,
                    payload={
                        "request_id": str(
                            request.request_id
                        ),
                        "tool": tool_name,
                        "arguments": arguments,
                        "risk": (
                            assessment.level.value
                        ),
                        "risk_score": (
                            assessment.score
                        ),
                        "reasons": (
                            assessment.reasons
                        ),
                    },
                    source="action_gate",
                )
            )

            approved = await approval_task

            # --------------------------------------------------
            # VERSION CHECK AFTER APPROVAL
            # --------------------------------------------------

            if task.version != task_version:

                return ToolExecutionResult(
                    tool_name=tool_name,
                    task_id=task.task_id,
                    task_version=task_version,
                    success=False,
                    stale=True,
                    error=(
                        "Approval became stale because "
                        "the task changed."
                    ),
                )

            if not approved:

                return ToolExecutionResult(
                    tool_name=tool_name,
                    task_id=task.task_id,
                    task_version=task_version,
                    success=False,
                    error=(
                        "User denied the action."
                    ),
                )

        # --------------------------------------------------
        # CANCELLATION CHECK
        # --------------------------------------------------

        if task.cancellation_requested():

            return ToolExecutionResult(
                tool_name=tool_name,
                task_id=task.task_id,
                task_version=task_version,
                success=False,
                cancelled=True,
                error="Task cancelled.",
            )

        # --------------------------------------------------
        # FINAL VERSION CHECK
        # --------------------------------------------------

        if task.version != task_version:

            return ToolExecutionResult(
                tool_name=tool_name,
                task_id=task.task_id,
                task_version=task_version,
                success=False,
                stale=True,
                error=(
                    "Action became stale before execution."
                ),
            )

        task.status = TaskStatus.RUNNING
        task.touch()

        # --------------------------------------------------
        # EXECUTE
        # --------------------------------------------------

        return await self.executor.execute(
            tool_name=tool_name,
            arguments=arguments,
            task=task,
        )