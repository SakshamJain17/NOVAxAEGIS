from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.agent.agent import AegisAgent
from app.runtime.event_bus import EventBus
from app.runtime.events import Event, EventType
from app.runtime.supervisor import TaskSupervisor
from app.runtime.tasks import TaskContext, TaskSnapshot, TaskStatus


logger = logging.getLogger("AEGIS")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class TaskExecution:
    """
    Runtime execution handle.

    The TaskContext is the source of truth for task state.
    This object only tracks the asyncio execution associated with it.
    """

    task_id: str
    task_version: int
    started_at: datetime
    asyncio_task: asyncio.Task[Any]

    @property
    def done(self) -> bool:
        return self.asyncio_task.done()


class TaskService:
    """
    Application orchestration layer for AEGIS.

    Responsibilities:

    - create tasks
    - execute tasks
    - prevent duplicate execution
    - interrupt tasks
    - cancel tasks
    - expose task state
    - maintain execution handles
    - bridge HTTP/WebSocket APIs to the agent runtime
    """

    def __init__(
        self,
        *,
        event_bus: EventBus,
        supervisor: TaskSupervisor,
        agent: AegisAgent,
    ) -> None:

        self.event_bus = event_bus
        self.supervisor = supervisor
        self.agent = agent

        self._executions: dict[str, TaskExecution] = {}

        self._lock = asyncio.Lock()

    # ==================================================================
    # CREATE
    # ==================================================================

    async def create(
        self,
        instruction: str,
        *,
        constraints: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TaskSnapshot:

        instruction = instruction.strip()

        if not instruction:
            raise ValueError(
                "Task instruction cannot be empty."
            )

        task = await self.supervisor.create_task(
            instruction=instruction,
            constraints=constraints or [],
            metadata=metadata or {},
        )

        snapshot = task.snapshot()

        logger.info(
            "Task created | task=%s version=%s",
            snapshot.task_id,
            snapshot.version,
        )

        return snapshot

    # ==================================================================
    # RUN
    # ==================================================================

    async def run(
        self,
        task_id: str,
    ) -> TaskSnapshot:

        async with self._lock:

            task = self.supervisor.get_task(task_id)

            if task is None:
                raise KeyError(
                    f"Task '{task_id}' was not found."
                )

            existing = self._executions.get(task_id)

            if existing and not existing.done:
                raise RuntimeError(
                    f"Task '{task_id}' is already executing."
                )

            if existing:
                self._executions.pop(
                    task_id,
                    None,
                )

            if task.status in {
                TaskStatus.COMPLETED,
                TaskStatus.CANCELLED,
                TaskStatus.FAILED,
            }:
                raise RuntimeError(
                    f"Task '{task_id}' cannot be executed "
                    f"from state '{task.status.value}'."
                )

            task.status = TaskStatus.THINKING
            task.touch()

            execution_task = asyncio.create_task(
                self._execute(task),
                name=f"aegis-task-{task_id}",
            )

            self._executions[task_id] = TaskExecution(
                task_id=task_id,
                task_version=task.version,
                started_at=utc_now(),
                asyncio_task=execution_task,
            )

            return task.snapshot()

    # ==================================================================
    # INTERNAL EXECUTION
    # ==================================================================

    async def _execute(
        self,
        task: TaskContext,
    ) -> None:

        task_id = task.task_id
        version = task.version

        try:

            await self.event_bus.publish(
                Event(
                    type=EventType.TASK_STARTED,
                    task_id=task_id,
                    task_version=version,
                    payload={
                        "instruction": task.instruction,
                    },
                    source="task_service",
                )
            )

            await self.agent.run(task)

        except asyncio.CancelledError:

            logger.info(
                "Task execution cancelled | task=%s version=%s",
                task_id,
                version,
            )

            raise

        except Exception as exc:

            logger.exception(
                "Task execution failed | task=%s version=%s",
                task_id,
                version,
            )

            task.status = TaskStatus.FAILED
            task.touch()

            await self.event_bus.publish(
                Event(
                    type=EventType.TASK_FAILED,
                    task_id=task_id,
                    task_version=task.version,
                    payload={
                        "error": str(exc),
                    },
                    source="task_service",
                )
            )

        finally:

            async with self._lock:

                current = self._executions.get(
                    task_id
                )

                if (
                    current is not None
                    and current.asyncio_task.done()
                ):
                    self._executions.pop(
                        task_id,
                        None,
                    )

    # ==================================================================
    # INTERRUPT
    # ==================================================================

    async def interrupt(
        self,
        task_id: str,
        *,
        new_instruction: str | None = None,
        constraints: list[str] | None = None,
    ) -> TaskSnapshot:

        task = self.supervisor.get_task(task_id)

        if task is None:
            raise KeyError(
                f"Task '{task_id}' was not found."
            )

        old_version = task.version

        # --------------------------------------------------------------
        # Update instruction first.
        #
        # This increments the task version and therefore invalidates
        # all tool results belonging to the old execution.
        # --------------------------------------------------------------

        if new_instruction:

            task.update_instruction(
                new_instruction.strip()
            )

        if constraints is not None:
            task.constraints = list(constraints)

        # --------------------------------------------------------------
        # Tell supervisor to cancel active execution.
        # --------------------------------------------------------------

        await self.supervisor.interrupt_task(
            task_id
        )

        execution = self._executions.get(
            task_id
        )

        if (
            execution is not None
            and not execution.done
        ):
            execution.asyncio_task.cancel()

        logger.info(
            "Task interrupted | task=%s old_version=%s new_version=%s",
            task_id,
            old_version,
            task.version,
        )

        return task.snapshot()

    # ==================================================================
    # CANCEL
    # ==================================================================

    async def cancel(
        self,
        task_id: str,
    ) -> TaskSnapshot:

        task = self.supervisor.get_task(task_id)

        if task is None:
            raise KeyError(
                f"Task '{task_id}' was not found."
            )

        execution = self._executions.get(
            task_id
        )

        if (
            execution is not None
            and not execution.done
        ):
            execution.asyncio_task.cancel()

        await self.supervisor.cancel_task(
            task_id
        )

        return task.snapshot()

    # ==================================================================
    # GET
    # ==================================================================

    async def get(
        self,
        task_id: str,
    ) -> TaskSnapshot:

        task = self.supervisor.get_task(task_id)

        if task is None:
            raise KeyError(
                f"Task '{task_id}' was not found."
            )

        return task.snapshot()

    # ==================================================================
    # LIST
    # ==================================================================

    async def list(
        self,
    ) -> list[TaskSnapshot]:

        tasks = self.supervisor.active_tasks()

        return [
            task.snapshot()
            for task in tasks
        ]

    # ==================================================================
    # ACTIVE EXECUTIONS
    # ==================================================================

    async def active_executions(
        self,
    ) -> list[dict[str, Any]]:

        async with self._lock:

            return [
                {
                    "task_id": execution.task_id,
                    "task_version": execution.task_version,
                    "started_at": execution.started_at,
                    "done": execution.done,
                }
                for execution in self._executions.values()
            ]

    # ==================================================================
    # SHUTDOWN
    # ==================================================================

    async def shutdown(self) -> None:

        async with self._lock:

            executions = list(
                self._executions.values()
            )

        for execution in executions:

            if not execution.done:

                execution.asyncio_task.cancel()

        if executions:

            await asyncio.gather(
                *[
                    execution.asyncio_task
                    for execution in executions
                ],
                return_exceptions=True,
            )

        async with self._lock:
            self._executions.clear()