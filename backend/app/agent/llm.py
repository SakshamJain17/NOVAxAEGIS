from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from app.agent.context import AgentContext
from app.agent.models import AgentPlan
from app.config.settings import settings


class LLMError(RuntimeError):
    pass


class LLMClient:

    def __init__(
        self,
        *,
        base_url: str = "http://127.0.0.1:11434",
        timeout: float = 120.0,
    ) -> None:

        self.base_url = base_url.rstrip("/")

        self.timeout = timeout

        self.logger = logging.getLogger(
            "aegis.llm"
        )

    async def plan(
        self,
        context: AgentContext,
    ) -> AgentPlan:

        prompt = self._build_prompt(context)

        payload = {
            "model": settings.model_name,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0.2,
                "top_p": 0.9,
            },
            "messages": [
                {
                    "role": "system",
                    "content": context.system_instruction,
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
        }

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout
            ) as client:

                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                )

                response.raise_for_status()

        except httpx.HTTPError as exc:
            raise LLMError(
                f"LLM request failed: {exc}"
            ) from exc

        try:
            body = response.json()

            content = body["message"]["content"]

            raw_plan = json.loads(content)

            plan = AgentPlan.model_validate(
                raw_plan
            )

        except (
            KeyError,
            json.JSONDecodeError,
            TypeError,
            ValueError,
        ) as exc:

            raise LLMError(
                "LLM returned an invalid AEGIS plan."
            ) from exc

        if plan.task_id != context.task_id:
            raise LLMError(
                "LLM returned an incorrect task ID."
            )

        if plan.task_version != context.task_version:
            raise LLMError(
                "LLM returned a stale task version."
            )

        return plan

    @staticmethod
    def _build_prompt(
        context: AgentContext,
    ) -> str:

        tools = json.dumps(
            context.available_tools,
            indent=2,
        )

        constraints = json.dumps(
            context.constraints,
            indent=2,
        )

        return f"""
Current task ID:
{context.task_id}

Current task version:
{context.task_version}

User request:
{context.user_instruction}

Constraints:
{constraints}

Available tools:
{tools}

Return ONLY valid JSON matching this schema:

{{
  "task_id": "{context.task_id}",
  "task_version": {context.task_version},
  "objective": "string",
  "confidence": 0.0,
  "actions": [
    {{
      "id": "action-1",
      "type": "respond | tool",
      "tool_name": "tool name or null",
      "arguments": {{}},
      "rationale": "string",
      "confidence": 0.0
    }}
  ],
  "final_response": "string or null"
}}

Rules:

1. Never invent tool names.
2. Never invent tool results.
3. Use a tool only when it is necessary.
4. If the request can be answered safely without
   a tool, return a respond action.
5. If uncertain, lower confidence.
6. Never claim an action was completed unless
   the execution layer confirms it.
7. Keep actions minimal.
8. The task version MUST remain exactly:
   {context.task_version}
"""