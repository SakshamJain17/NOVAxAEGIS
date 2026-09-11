from __future__ import annotations

from app.runtime.event_bus import EventBus
from app.runtime.events import Event, EventType
from app.safety.models import (
    ActionProposal,
    Decision,
    RiskAssessment,
)
from app.safety.policy import SafetyPolicy
from app.safety.risk import RiskEngine


class SafetyEngine:

    def __init__(
        self,
        risk_engine: RiskEngine,
        policy: SafetyPolicy,
        event_bus: EventBus,
    ) -> None:
        self.risk_engine = risk_engine
        self.policy = policy
        self.event_bus = event_bus

    async def evaluate(
        self,
        proposal: ActionProposal,
    ) -> RiskAssessment:

        assessment = self.risk_engine.assess(
            proposal
        )

        decision = self.policy.evaluate(
            proposal,
            assessment,
        )

        assessment = assessment.model_copy(
            update={
                "decision": decision,
                "user_authorized": (
                    decision == Decision.ALLOW
                ),
            }
        )

        await self.event_bus.publish(
            Event(
                type=EventType.RISK_ASSESSED,
                task_id=proposal.task_id,
                task_version=proposal.task_version,
                payload={
                    "tool": proposal.tool_name,
                    "risk": assessment.level.value,
                    "score": assessment.score,
                    "decision": decision.value,
                    "confidence": proposal.confidence,
                    "reasons": assessment.reasons,
                },
                source="safety_engine",
            )
        )

        if decision == Decision.APPROVAL_REQUIRED:

            await self.event_bus.publish(
                Event(
                    type=EventType.APPROVAL_REQUIRED,
                    task_id=proposal.task_id,
                    task_version=proposal.task_version,
                    payload={
                        "tool": proposal.tool_name,
                        "risk": assessment.level.value,
                        "reasons": assessment.reasons,
                    },
                    source="safety_engine",
                )
            )

        elif decision == Decision.BLOCK:

            await self.event_bus.publish(
                Event(
                    type=EventType.ACTION_BLOCKED,
                    task_id=proposal.task_id,
                    task_version=proposal.task_version,
                    payload={
                        "tool": proposal.tool_name,
                        "risk": assessment.level.value,
                        "reasons": assessment.reasons,
                    },
                    source="safety_engine",
                )
            )

        return assessment