from __future__ import annotations

from typing import Iterable

from app.tools.base import BaseTool


class ToolAlreadyRegisteredError(Exception):
    pass


class ToolNotFoundError(Exception):
    pass


class ToolRegistry:

    def __init__(
        self,
        tools: Iterable[BaseTool] | None = None,
    ) -> None:
        self._tools: dict[str, BaseTool] = {}

        if tools:
            for tool in tools:
                self.register(tool)

    def register(self, tool: BaseTool) -> None:
        name = tool.metadata.name

        if name in self._tools:
            raise ToolAlreadyRegisteredError(
                f"Tool '{name}' is already registered"
            )

        self._tools[name] = tool

    def unregister(self, name: str) -> None:
        if name not in self._tools:
            raise ToolNotFoundError(
                f"Tool '{name}' is not registered"
            )

        del self._tools[name]

    def get(self, name: str) -> BaseTool:
        try:
            return self._tools[name]
        except KeyError:
            raise ToolNotFoundError(
                f"Tool '{name}' is not registered"
            )

    def has(self, name: str) -> bool:
        return name in self._tools

    def list(self) -> list[BaseTool]:
        return list(self._tools.values())

    def descriptions(self) -> list[dict]:
        return [
            tool.describe()
            for tool in self._tools.values()
        ]

    def names(self) -> list[str]:
        return list(self._tools.keys())