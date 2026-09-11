from app.runtime.event_bus import EventBus
from app.tools.builtin import SafeCalculator
from app.tools.executor import ToolExecutor
from app.tools.registry import ToolRegistry


def create_tool_runtime(
    event_bus: EventBus,
) -> tuple[ToolRegistry, ToolExecutor]:

    registry = ToolRegistry(
        tools=[
            SafeCalculator(),
        ]
    )

    executor = ToolExecutor(
        registry=registry,
        event_bus=event_bus,
    )

    return registry, executor