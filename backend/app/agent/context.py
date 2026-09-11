from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.runtime.tasks import TaskContext
from app.tools.registry import ToolRegistry


@dataclass(slots=True, frozen=True)
class AgentContext:
    """
    Immutable context snapshot supplied to the reasoning layer.

    The LLM receives a snapshot rather than a mutable TaskContext.
    This prevents reasoning against a task state that may have changed
    while the model was generating a plan.
    """

    system_instruction: str

    task_id: str
    task_version: int

    user_instruction: str
    constraints: dict[str, Any]

    available_tools: list[dict[str, Any]]

    metadata: dict[str, Any] = field(default_factory=dict)

    execution_history: list[dict[str, Any]] = field(
        default_factory=list
    )

    previous_results: list[dict[str, Any]] = field(
        default_factory=list
    )


class ContextBuilder:
    """
    Builds an immutable reasoning context from the current task.

    This is deliberately separate from the LLM client so that:
    - the LLM remains provider-agnostic
    - task state is controlled by AEGIS
    - future memory/retrieval can be injected here
    - stale context can be detected using task versions
    """

    SYSTEM_INSTRUCTION = """
You are AEGIS — Adaptive Execution & Guidance Intelligence System.

You are a bounded-autonomy AI agent.

Your responsibilities:
1. Understand the user's current objective.
2. Create the smallest safe plan necessary to accomplish it.
3. Propose tool actions when tools are genuinely required.
4. Never execute tools yourself.
5. Never invent tool names.
6. Never invent tool results.
7. Never claim an action succeeded unless execution confirms it.
8. Respect the current task version.
9. Treat previous tool results as potentially stale unless AEGIS
   confirms they belong to the current task version.
10. Explicitly represent uncertainty through lower confidence.
11. Prefer asking for clarification over making unsafe assumptions.
12. Keep plans minimal and deterministic where possible.

AEGIS's execution architecture is:

USER
  ↓
REASON
  ↓
PLAN
  ↓
SAFETY POLICY
  ↓
HUMAN APPROVAL when required
  ↓
TOOL EXECUTION
  ↓
RESULT VALIDATION
  ↓
RESPONSE / REPLAN

The language model proposes actions.
The AEGIS control plane decides whether those actions execute.
""".strip()

    def __init__(self, tool_registry: ToolRegistry) -> None:
        self.tool_registry = tool_registry

    def build(self, task: TaskContext) -> AgentContext:
        return AgentContext(
            system_instruction=self.SYSTEM_INSTRUCTION,
            task_id=str(task.task_id),
            task_version=task.version,
            user_instruction=task.instruction,
            constraints=dict(task.constraints),
            available_tools=self.tool_registry.descriptions(),
            metadata=dict(task.metadata),
            execution_history=self._execution_history(task),
            previous_results=self._previous_results(task),
        )

    @staticmethod
    def _execution_history(task: TaskContext) -> list[dict[str, Any]]:
        history = task.metadata.get("execution_history", [])

        if not isinstance(history, list):
            return []

        return [
            dict(entry)
            for entry in history
            if isinstance(entry, dict)
        ]

    @staticmethod
    def _previous_results(task: TaskContext) -> list[dict[str, Any]]:
        results = task.metadata.get("previous_results", [])

        if not isinstance(results, list):
            return []

        return [
            dict(result)
            for result in results
            if isinstance(result, dict)
        ]