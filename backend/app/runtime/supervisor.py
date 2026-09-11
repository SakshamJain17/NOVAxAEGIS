from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from uuid import UUID

from app.runtime.event_bus import EventBus
from app.runtime.events import Event, EventType
from app.runtime.tasks import TaskContext, TaskStatus


@dataclass(slots=True)
class ActiveTask:
    context: TaskContext
    execution_task: asyncio.Task | None = None


class TaskSupervisor:
    """
    Owns active AEGIS tasks and their lifecycle.

    The supervisor is intentionally independent of the LLM.
    """
    def get_task(self, task_id: str) -> TaskContext | None:
        """
        Return an active task by ID.

        The caller receives the live TaskContext so that orchestration
        operations can update task state atomically.
        """
        return self._tasks.get(task_id)
    def __init__(self, event_bus: EventBus) -> None:
        self.event_bus = event_bus

        self._tasks: dict[UUID, ActiveTask] = {}

        self._logger = logging.getLogger(
            "aegis.task_supervisor"
        )

    async def create_task(
        self,
        instruction: str,
        constraints: dict | None = None,
    ) -> TaskContext:
        context = TaskContext(
            instruction=instruction,
            constraints=constraints or {},
        )

        self._tasks[context.task_id] = ActiveTask(
            context=context
        )

        await self.event_bus.publish(
            Event(
                type=EventType.TASK_CREATED,
                task_id=context.task_id,
                task_version=context.version,
                payload={
                    "instruction": instruction,
                    "constraints": context.constraints,
                },
                source="task_supervisor",
            )
        )

        return context

    def get_task(
        self,
        task_id: UUID,
    ) -> TaskContext | None:
        active = self._tasks.get(task_id)
        return active.context if active else None

    async def interrupt_task(
        self,
        task_id: UUID,
        new_instruction: str | None = None,
        constraints: dict | None = None,
    ) -> TaskContext:
        active = self._tasks.get(task_id)

        if active is None:
            raise KeyError(f"Unknown task: {task_id}")

        context = active.context

        old_version = context.version

        if active.execution_task and not active.execution_task.done():
            active.execution_task.cancel()

            try:
                await active.execution_task
            except asyncio.CancelledError:
                pass

        context.status = TaskStatus.INTERRUPTED
        context.touch()

        await self.event_bus.publish(
            Event(
                type=EventType.TASK_INTERRUPTED,
                task_id=task_id,
                task_version=old_version,
                payload={
                    "reason": "user_interrupt",
                    "old_version": old_version,
                },
                source="task_supervisor",
            )
        )

        if new_instruction is not None:
            new_version = context.update_instruction(
                instruction=new_instruction,
                constraints=constraints,
            )
        else:
            new_version = context.invalidate()
            context.status = TaskStatus.RECONCILING

        await self.event_bus.publish(
            Event(
                type=EventType.TASK_RECONCILING,
                task_id=task_id,
                task_version=new_version,
                payload={
                    "previous_version": old_version,
                    "new_version": new_version,
                    "instruction": context.instruction,
                    "constraints": context.constraints,
                },
                source="task_supervisor",
            )
        )

        return context

    async def cancel_task(
        self,
        task_id: UUID,
    ) -> None:
        active = self._tasks.get(task_id)

        if active is None:
            raise KeyError(f"Unknown task: {task_id}")

        if active.execution_task and not active.execution_task.done():
            active.execution_task.cancel()

            try:
                await active.execution_task
            except asyncio.CancelledError:
                pass

        active.context.cancel()

        await self.event_bus.publish(
            Event(
                type=EventType.TASK_CANCELLED,
                task_id=task_id,
                task_version=active.context.version,
                source="task_supervisor",
            )
        )

    def attach_execution(
        self,
        task_id: UUID,
        execution_task: asyncio.Task,
    ) -> None:
        active = self._tasks.get(task_id)

        if active is None:
            raise KeyError(f"Unknown task: {task_id}")

        active.execution_task = execution_task

    def active_tasks(self) -> list[TaskContext]:
        return [
            active.context
            for active in self._tasks.values()
        ]

    def remove_task(
        self,
        task_id: UUID,
    ) -> None:
        self._tasks.pop(task_id, None)