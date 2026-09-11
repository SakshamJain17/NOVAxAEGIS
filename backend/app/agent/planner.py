from __future__ import annotations

from app.agent.context import ContextBuilder
from app.agent.llm import LLMClient
from app.agent.models import AgentPlan
from app.runtime.events import Event, EventType
from app.runtime.event_bus import EventBus
from app.runtime.tasks import TaskContext


class AgentPlanner:

    def __init__(
        self,
        llm: LLMClient,
        context_builder: ContextBuilder,
        event_bus: EventBus,
    ) -> None:

        self.llm = llm
        self.context_builder = context_builder
        self.event_bus = event_bus

    async def create_plan(
        self,
        task: TaskContext,
    ) -> AgentPlan:

        context = self.context_builder.build(
            task
        )

        await self.event_bus.publish(
    Event(
        type=EventType.PLAN_CREATED,
        task_id=task.task_id,
        task_version=task.version,
        payload={
            "phase": "planning_started",
            "instruction": task.instruction,
        },
        source="agent_planner",
    )
)

        plan = await self.llm.plan(
            context
        )

        # Never accept a plan belonging to an
        # obsolete task.

        if plan.task_version != task.version:
            raise RuntimeError(
                "Planner produced a stale plan."
            )

        await self.event_bus.publish(
            Event(
                type=EventType.PLAN_CREATED,
                task_id=task.task_id,
                task_version=task.version,
                payload={
                    "objective": plan.objective,
                    "actions": [
                        action.model_dump()
                        for action in plan.actions
                    ],
                    "confidence": plan.confidence,
                },
                source="agent_planner",
            )
        )

        return plan