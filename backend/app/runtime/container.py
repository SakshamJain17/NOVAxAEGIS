"""
AEGIS Runtime Container

Central dependency graph for the AEGIS backend.

The container wires together:
    EventBus
    TaskSupervisor
    Tool Runtime
    Risk Engine
    Safety Policy
    Safety Engine
    Approval Manager
    Action Gate
    Result Validator
    Context Builder
    LLM Client
    Agent Planner
    AEGIS Agent
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.runtime.event_bus import EventBus
from app.runtime.supervisor import TaskSupervisor
from app.runtime.result_validator import ResultValidator
from app.runtime.action_gate import ActionGate

from app.tools.runtime import create_tool_runtime

from app.safety.engine import SafetyEngine
from app.safety.risk import RiskEngine
from app.safety.policy import SafetyPolicy
from app.safety.approvals import ApprovalManager

from app.agent.context import ContextBuilder
from app.agent.llm import LLMClient
from app.agent.planner import AgentPlanner
from app.agent.agent import AegisAgent


# ==============================================================
# RUNTIME CONTAINER
# ==============================================================


@dataclass
class AegisRuntime:
    """
    Complete dependency container for the AEGIS runtime.
    """

    # Core
    event_bus: EventBus
    supervisor: TaskSupervisor

    # Tools
    tool_registry: Any
    tool_executor: Any

    # Safety
    risk_engine: RiskEngine
    policy: SafetyPolicy
    safety_engine: SafetyEngine
    approval_manager: ApprovalManager
    action_gate: ActionGate

    # Validation
    result_validator: ResultValidator

    # Agent
    context_builder: ContextBuilder
    llm: LLMClient
    planner: AgentPlanner
    agent: AegisAgent

    # Metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    async def shutdown(self) -> None:
        """
        Gracefully shut down runtime components.
        """

        # ------------------------------------------------------
        # Tool executor
        # ------------------------------------------------------

        shutdown = getattr(self.tool_executor, "shutdown", None)

        if shutdown is not None:
            result = shutdown()

            if hasattr(result, "__await__"):
                await result

        # ------------------------------------------------------
        # Supervisor
        # ------------------------------------------------------

        shutdown = getattr(self.supervisor, "shutdown", None)

        if shutdown is not None:
            result = shutdown()

            if hasattr(result, "__await__"):
                await result

        # ------------------------------------------------------
        # Approval manager
        # ------------------------------------------------------

        clear = getattr(self.approval_manager, "clear", None)

        if clear is not None:
            result = clear()

            if hasattr(result, "__await__"):
                await result

        # ------------------------------------------------------
        # Event bus
        # ------------------------------------------------------

        clear = getattr(self.event_bus, "clear", None)

        if clear is not None:
            result = clear()

            if hasattr(result, "__await__"):
                await result


# ==============================================================
# TOOL RUNTIME EXTRACTION
# ==============================================================


def _extract_tool_runtime(tool_runtime: Any) -> tuple[Any, Any]:
    """
    Extract the registry and executor from create_tool_runtime().

    Supports:
        runtime.registry / runtime.executor
        (registry, executor)
        {"registry": ..., "executor": ...}
    """

    # Object-style runtime
    if hasattr(tool_runtime, "registry") and hasattr(
        tool_runtime,
        "executor",
    ):
        return (
            tool_runtime.registry,
            tool_runtime.executor,
        )

    # Tuple-style runtime
    if isinstance(tool_runtime, tuple) and len(tool_runtime) >= 2:
        return (
            tool_runtime[0],
            tool_runtime[1],
        )

    # Dictionary-style runtime
    if isinstance(tool_runtime, dict):
        registry = tool_runtime.get("registry")
        executor = tool_runtime.get("executor")

        if registry is not None and executor is not None:
            return registry, executor

    raise TypeError(
        "Unsupported create_tool_runtime() return value. "
        "Expected an object with registry/executor, "
        "a (registry, executor) tuple, or a dictionary containing "
        "'registry' and 'executor'."
    )


# ==============================================================
# RUNTIME FACTORY
# ==============================================================


def create_runtime() -> AegisRuntime:
    """
    Construct the complete AEGIS runtime.

    Dependency order:

        EventBus
            ↓
        TaskSupervisor
            ↓
        Tool Runtime
            ↓
        Risk Engine
            ↓
        Safety Policy
            ↓
        Safety Engine
            ↓
        Approval Manager
            ↓
        Action Gate
            ↓
        Result Validator
            ↓
        Context Builder
            ↓
        LLM Client
            ↓
        Agent Planner
            ↓
        AegisAgent
    """

    # ==========================================================
    # 1. EVENT BUS
    # ==========================================================

    event_bus = EventBus()

    # ==========================================================
    # 2. TASK SUPERVISOR
    # ==========================================================

    supervisor = TaskSupervisor(
        event_bus=event_bus,
    )

    # ==========================================================
    # 3. TOOL RUNTIME
    # ==========================================================

    # The existing implementation accepts event_bus.
    # It does NOT accept supervisor.

    tool_runtime = create_tool_runtime(
        event_bus=event_bus,
    )

    tool_registry, tool_executor = _extract_tool_runtime(
        tool_runtime
    )

    # ==========================================================
    # 4. RISK ENGINE
    # ==========================================================

    # Confirmed interface:
    #
    #     RiskEngine(registry)
    #

    risk_engine = RiskEngine(
        registry=tool_registry,
    )

    # ==========================================================
    # 5. SAFETY POLICY
    # ==========================================================

    policy = SafetyPolicy()

    # ==========================================================
    # 6. SAFETY ENGINE
    # ==========================================================

    # Confirmed required dependencies:
    #
    #     risk_engine
    #     policy
    #

    safety_engine = SafetyEngine(
        risk_engine=risk_engine,
        policy=policy,
        event_bus=event_bus,
    )

    # ==========================================================
    # 7. APPROVAL MANAGER
    # ==========================================================

    # Confirmed interface:
    #
    #     ApprovalManager()
    #

    approval_manager = ApprovalManager()

    # ==========================================================
    # 8. ACTION GATE
    # ==========================================================

    # Confirmed interface:
    #
    #     ActionGate(
    #         safety,
    #         executor,
    #         approvals,
    #         event_bus
    #     )
    #

    action_gate = ActionGate(
        safety=safety_engine,
        executor=tool_executor,
        approvals=approval_manager,
        event_bus=event_bus,
    )

    # ==========================================================
    # 9. RESULT VALIDATOR
    # ==========================================================

    # Confirmed interface:
    #
    #     ResultValidator(event_bus)
    #

    result_validator = ResultValidator(
        event_bus=event_bus,
    )

    # ==========================================================
    # 10. CONTEXT BUILDER
    # ==========================================================

    # Confirmed interface:
    #
    #     ContextBuilder(tool_registry)
    #

    context_builder = ContextBuilder(
        tool_registry=tool_registry,
    )

    # ==========================================================
    # 11. LLM CLIENT
    # ==========================================================

    # Confirmed interface:
    #
    #     LLMClient(
    #         base_url="http://127.0.0.1:11434",
    #         timeout=120.0
    #     )
    #
    # Defaults intentionally preserve the local Ollama setup.

    llm = LLMClient(
        base_url="http://127.0.0.1:11434",
        timeout=120.0,
    )

    # ==========================================================
    # 12. AGENT PLANNER
    # ==========================================================

    # Confirmed interface:
    #
    #     AgentPlanner(
    #         llm,
    #         context_builder,
    #         event_bus
    #     )
    #

    planner = AgentPlanner(
        llm=llm,
        context_builder=context_builder,
        event_bus=event_bus,
    )

    # ==========================================================
    # 13. AEGIS AGENT
    # ==========================================================

    # Confirmed interface:
    #
    #     AegisAgent(
    #         planner,
    #         action_gate,
    #         result_validator,
    #         event_bus
    #     )
    #

    agent = AegisAgent(
        planner=planner,
        action_gate=action_gate,
        result_validator=result_validator,
        event_bus=event_bus,
    )

    # ==========================================================
    # 14. RETURN COMPLETE RUNTIME
    # ==========================================================

    return AegisRuntime(
        # Core
        event_bus=event_bus,
        supervisor=supervisor,

        # Tools
        tool_registry=tool_registry,
        tool_executor=tool_executor,

        # Safety
        risk_engine=risk_engine,
        policy=policy,
        safety_engine=safety_engine,
        approval_manager=approval_manager,
        action_gate=action_gate,

        # Validation
        result_validator=result_validator,

        # Agent
        context_builder=context_builder,
        llm=llm,
        planner=planner,
        agent=agent,

        # Metadata
        metadata={
            "service": "AEGIS",
            "version": "0.1.0",
            "architecture": "control-plane-agent",
            "llm": "Ollama",
            "llm_base_url": "http://127.0.0.1:11434",
            "safety_enabled": True,
            "tool_execution_enabled": True,
            "task_versioning_enabled": True,
            "recovery_enabled": True,
        },
    )