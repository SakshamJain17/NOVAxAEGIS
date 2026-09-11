from __future__ import annotations

import ast
import operator

from app.tools.base import (
    BaseTool,
    ToolCategory,
    ToolExecutionResult,
    ToolMetadata,
    ToolRisk,
    ToolContext,
)


class SafeCalculator(BaseTool):

    metadata = ToolMetadata(
        name="calculator",
        description=(
            "Safely evaluate basic mathematical expressions."
        ),
        category=ToolCategory.COMPUTATION,
        risk=ToolRisk.LOW,
        requires_approval=False,
        timeout_seconds=5,
    )

    _operators = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.Mod: operator.mod,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    def _evaluate(self, node: ast.AST) -> float:

        if isinstance(node, ast.Constant):

            if not isinstance(
                node.value,
                (int, float),
            ):
                raise ValueError(
                    "Only numeric constants are allowed"
                )

            return node.value

        if isinstance(node, ast.UnaryOp):

            operator_fn = self._operators.get(
                type(node.op)
            )

            if operator_fn is None:
                raise ValueError(
                    "Unsupported unary operator"
                )

            return operator_fn(
                self._evaluate(node.operand)
            )

        if isinstance(node, ast.BinOp):

            operator_fn = self._operators.get(
                type(node.op)
            )

            if operator_fn is None:
                raise ValueError(
                    "Unsupported operator"
                )

            return operator_fn(
                self._evaluate(node.left),
                self._evaluate(node.right),
            )

        raise ValueError(
            f"Unsupported expression: "
            f"{type(node).__name__}"
        )

    async def execute(
        self,
        arguments: dict,
        context: ToolContext,
    ) -> ToolExecutionResult:

        expression = arguments.get("expression")

        if not isinstance(expression, str):
            return ToolExecutionResult(
                tool_name=self.metadata.name,
                task_id=context.task_id,
                task_version=context.task_version,
                success=False,
                error="expression must be a string",
            )

        if context.is_cancelled():
            return ToolExecutionResult(
                tool_name=self.metadata.name,
                task_id=context.task_id,
                task_version=context.task_version,
                success=False,
                cancelled=True,
                error="Execution cancelled",
            )

        try:
            tree = ast.parse(
                expression,
                mode="eval",
            )

            result = self._evaluate(tree.body)

            return ToolExecutionResult(
                tool_name=self.metadata.name,
                task_id=context.task_id,
                task_version=context.task_version,
                success=True,
                data=result,
            )

        except Exception as exc:
            return ToolExecutionResult(
                tool_name=self.metadata.name,
                task_id=context.task_id,
                task_version=context.task_version,
                success=False,
                error=str(exc),
            )