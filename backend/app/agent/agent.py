from __future__ import annotations

import logging

from app.agent.models import AgentPlan, PlanActionType
from app.agent.planner import AgentPlanner
from app.runtime.action_gate import ActionGate
from app.runtime.event_bus import EventBus
from app.runtime.events import Event, EventType
from app.runtime.result_validator import ResultValidator, ValidationStatus
from app.runtime.tasks import TaskContext, TaskStatus


class AgentExecutionError(RuntimeError):
    pass


class ReplanLimitExceeded(AgentExecutionError):
    pass


class AegisAgent:
    """
    Bounded autonomous execution engine.

    The LLM never directly executes a tool.

    Every action passes through:

        PLAN
          ↓
        SAFETY
          ↓
        APPROVAL
          ↓
        EXECUTION
          ↓
        VALIDATION
          ↓
        ACCEPT / REPLAN / RECOVER
    """

    MAX_REPLANS = 3

    def __init__(
        self,
        planner: AgentPlanner,
        action_gate: ActionGate,
        result_validator: ResultValidator,
        event_bus: EventBus,
    ) -> None:
        self.planner = planner
        self.action_gate = action_gate
        self.result_validator = result_validator
        self.event_bus = event_bus

        self.logger = logging.getLogger("aegis.agent")

    async def run(self, task: TaskContext) -> AgentPlan:

        replan_count = 0

        while True:

            # -----------------------------------------------------
            # PLAN
            # -----------------------------------------------------

            task.status = TaskStatus.RUNNING
            task.touch()

            plan = await self.planner.create_plan(task)

            self._assert_current_version(
                task,
                plan.task_version,
            )

            await self.event_bus.publish(
                Event(
                    type=EventType.REPLAN_COMPLETED
                    if replan_count > 0
                    else EventType.PLAN_CREATED,
                    task_id=task.task_id,
                    task_version=task.version,
                    payload={
                        "replan_count": replan_count,
                        "actions": len(plan.actions),
                    },
                    source="aegis_agent",
                )
            )

            should_replan = False

            # -----------------------------------------------------
            # EXECUTE PLAN
            # -----------------------------------------------------

            for action in plan.actions:

                self._assert_current_version(
                    task,
                    plan.task_version,
                )

                if task.cancellation_requested():
                    task.status = TaskStatus.CANCELLED
                    task.touch()
                    return plan

                # ---------------------------------------------
                # Natural-language response
                # ---------------------------------------------

                if action.type == PlanActionType.RESPOND:
                    self._record_execution(
                        task,
                        {
                            "type": "respond",
                            "action_id": action.id,
                            "response": plan.final_response,
                            "task_version": task.version,
                        },
                    )
                    continue

                # ---------------------------------------------
                # Tool action
                # ---------------------------------------------

                if action.type != PlanActionType.TOOL:
                    raise AgentExecutionError(
                        f"Unsupported action type: {action.type}"
                    )

                if not action.tool_name:
                    raise AgentExecutionError(
                        "Tool action has no tool_name."
                    )

                result = await self.action_gate.execute(
                    task=task,
                    tool_name=action.tool_name,
                    arguments=action.arguments,
                    confidence=action.confidence,
                    rationale=action.rationale,
                )

                # ---------------------------------------------
                # VALIDATE
                # ---------------------------------------------

                validation = await self.result_validator.validate(
                    task=task,
                    result=result,
                )

                # ---------------------------------------------
                # STALE RESULT
                # ---------------------------------------------

                if validation.status == ValidationStatus.STALE:

                    replan_count += 1

                    if replan_count > self.MAX_REPLANS:
                        raise ReplanLimitExceeded(
                            "AEGIS exceeded its maximum reconciliation "
                            "limit."
                        )

                    task.status = TaskStatus.RECONCILING
                    task.touch()

                    await self.event_bus.publish(
                        Event(
                            type=EventType.REPLAN_STARTED,
                            task_id=task.task_id,
                            task_version=task.version,
                            payload={
                                "reason": "stale_result",
                                "tool": result.tool_name,
                                "result_version": result.task_version,
                                "current_version": task.version,
                                "replan_count": replan_count,
                            },
                            source="aegis_agent",
                        )
                    )

                    should_replan = True
                    break

                # ---------------------------------------------
                # INVALID / FAILED RESULT
                # ---------------------------------------------

                if not validation.usable:

                    await self.event_bus.publish(
                        Event(
                            type=EventType.TASK_FAILED,
                            task_id=task.task_id,
                            task_version=task.version,
                            payload={
                                "tool": result.tool_name,
                                "reason": validation.reason,
                                "validation_status": validation.status,
                            },
                            source="aegis_agent",
                        )
                    )

                    task.status = TaskStatus.FAILED
                    task.touch()

                    raise AgentExecutionError(
                        validation.reason
                        or "Tool result failed validation."
                    )

                # ---------------------------------------------
                # STORE VERIFIED RESULT
                # ---------------------------------------------

                self._record_result(
                    task,
                    result,
                )

            # -----------------------------------------------------
            # REPLAN
            # -----------------------------------------------------

            if should_replan:
                continue

            # -----------------------------------------------------
            # COMPLETE
            # -----------------------------------------------------

            task.status = TaskStatus.COMPLETED
            task.touch()

            return plan

    @staticmethod
    def _assert_current_version(
        task: TaskContext,
        expected_version: int,
    ) -> None:

        if task.version != expected_version:
            raise AgentExecutionError(
                "Agent execution became stale."
            )

    @staticmethod
    def _record_result(
        task: TaskContext,
        result,
    ) -> None:

        history = task.metadata.setdefault(
            "previous_results",
            [],
        )

        history.append(
            {
                "tool": result.tool_name,
                "task_id": str(result.task_id),
                "task_version": result.task_version,
                "success": result.success,
                "data": result.data,
            }
        )

        # Prevent unlimited context growth.
        if len(history) > 50:
            del history[:-50]

        task.touch()

    @staticmethod
    def _record_execution(
        task: TaskContext,
        entry: dict,
    ) -> None:

        history = task.metadata.setdefault(
            "execution_history",
            [],
        )

        history.append(entry)

        if len(history) > 100:
            del history[:-100]

        task.touch()