from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from app.runtime.event_bus import EventBus
from app.runtime.events import Event, EventType
from app.runtime.results import ToolResult
from app.runtime.tasks import TaskContext
from app.tools.base import (
    BaseTool,
    ToolContext,
    ToolExecutionResult,
)
from app.tools.registry import ToolRegistry


class ToolExecutionError(Exception):
    pass


class ToolExecutor:

    def __init__(
        self,
        registry: ToolRegistry,
        event_bus: EventBus,
    ) -> None:
        self.registry = registry
        self.event_bus = event_bus

        self.logger = logging.getLogger(
            "aegis.tool_executor"
        )

    async def execute(
        self,
        tool_name: str,
        arguments: dict,
        task: TaskContext,
    ) -> ToolExecutionResult:

        tool = self.registry.get(tool_name)

        task_version = task.version

        await self.event_bus.publish(
            Event(
                type=EventType.TOOL_REQUESTED,
                task_id=task.task_id,
                task_version=task_version,
                payload={
                    "tool": tool_name,
                    "arguments": arguments,
                },
                source="tool_executor",
            )
        )

        if task.cancellation_requested():
            return ToolExecutionResult(
                tool_name=tool_name,
                task_id=task.task_id,
                task_version=task_version,
                success=False,
                cancelled=True,
                error="Task was cancelled before execution",
            )

        await self.event_bus.publish(
            Event(
                type=EventType.TOOL_STARTED,
                task_id=task.task_id,
                task_version=task_version,
                payload={
                    "tool": tool_name,
                },
                source="tool_executor",
            )
        )

        context = ToolContext(
            task_id=task.task_id,
            task_version=task_version,
            cancellation_requested=task._cancel_event,
        )

        started_at = datetime.now(timezone.utc)

        try:
            result = await asyncio.wait_for(
                tool.execute(
                    arguments,
                    context,
                ),
                timeout=tool.metadata.timeout_seconds,
            )

        except asyncio.CancelledError:

            await self.event_bus.publish(
                Event(
                    type=EventType.TOOL_CANCELLED,
                    task_id=task.task_id,
                    task_version=task_version,
                    payload={
                        "tool": tool_name,
                    },
                    source="tool_executor",
                )
            )

            raise

        except asyncio.TimeoutError:

            await self.event_bus.publish(
                Event(
                    type=EventType.TOOL_FAILED,
                    task_id=task.task_id,
                    task_version=task_version,
                    payload={
                        "tool": tool_name,
                        "error": "timeout",
                    },
                    source="tool_executor",
                )
            )

            return ToolExecutionResult(
                tool_name=tool_name,
                task_id=task.task_id,
                task_version=task_version,
                success=False,
                error="Tool execution timed out",
            )

        except Exception as exc:

            self.logger.exception(
                "Tool execution failed: %s",
                tool_name,
            )

            await self.event_bus.publish(
                Event(
                    type=EventType.TOOL_FAILED,
                    task_id=task.task_id,
                    task_version=task_version,
                    payload={
                        "tool": tool_name,
                        "error": str(exc),
                    },
                    source="tool_executor",
                )
            )

            return ToolExecutionResult(
                tool_name=tool_name,
                task_id=task.task_id,
                task_version=task_version,
                success=False,
                error=str(exc),
            )

        completed_at = datetime.now(timezone.utc)

        # Critical AEGIS check:
        # Did the user change the task while this tool
        # was executing?

        if task.version != task_version:

            await self.event_bus.publish(
                Event(
                    type=EventType.TOOL_RESULT_STALE,
                    task_id=task.task_id,
                    task_version=task_version,
                    payload={
                        "tool": tool_name,
                        "result_version": task_version,
                        "current_version": task.version,
                    },
                    source="tool_executor",
                )
            )

            result.stale = True

            return result

        await self.event_bus.publish(
            Event(
                type=EventType.TOOL_COMPLETED,
                task_id=task.task_id,
                task_version=task_version,
                payload={
                    "tool": tool_name,
                    "success": result.success,
                    "duration_ms": (
                        completed_at - started_at
                    ).total_seconds() * 1000,
                },
                source="tool_executor",
            )
        )

        return result