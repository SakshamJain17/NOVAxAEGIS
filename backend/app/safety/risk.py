from __future__ import annotations

from dataclasses import dataclass

from app.safety.models import (
    ActionProposal,
    Decision,
    RiskAssessment,
    RiskLevel,
)
from app.tools.base import ToolRisk
from app.tools.registry import ToolRegistry


@dataclass(frozen=True, slots=True)
class RiskFactors:
    tool_risk: float
    confidence_penalty: float
    authorization_penalty: float
    reversibility_penalty: float


TOOL_RISK_SCORE = {
    ToolRisk.LOW: 0.05,
    ToolRisk.MEDIUM: 0.30,
    ToolRisk.HIGH: 0.65,
    ToolRisk.CRITICAL: 0.95,
}


class RiskEngine:

    def __init__(
        self,
        registry: ToolRegistry,
    ) -> None:
        self.registry = registry

    def assess(
        self,
        proposal: ActionProposal,
    ) -> RiskAssessment:

        tool = self.registry.get(
            proposal.tool_name
        )

        metadata = tool.metadata

        reasons: list[str] = []

        tool_score = TOOL_RISK_SCORE[
            metadata.risk
        ]

        confidence_penalty = (
            1.0 - proposal.confidence
        ) * 0.35

        authorization_penalty = 0.0

        if metadata.requires_approval:
            authorization_penalty = 0.25

            reasons.append(
                "Tool requires explicit approval."
            )

        reversibility_penalty = 0.0

        if metadata.risk in {
            ToolRisk.HIGH,
            ToolRisk.CRITICAL,
        }:
            reversibility_penalty = 0.15

            reasons.append(
                "Action may have significant consequences."
            )

        score = min(
            1.0,
            tool_score
            + confidence_penalty
            + authorization_penalty
            + reversibility_penalty,
        )

        if score >= 0.85:
            level = RiskLevel.CRITICAL
        elif score >= 0.60:
            level = RiskLevel.HIGH
        elif score >= 0.30:
            level = RiskLevel.MEDIUM
        elif score > 0.05:
            level = RiskLevel.LOW
        else:
            level = RiskLevel.NONE

        if level == RiskLevel.CRITICAL:
            decision = Decision.BLOCK

        elif (
            level in {
                RiskLevel.HIGH,
                RiskLevel.MEDIUM,
            }
            or metadata.requires_approval
        ):
            decision = Decision.APPROVAL_REQUIRED

        else:
            decision = Decision.ALLOW

        return RiskAssessment(
            level=level,
            decision=decision,
            score=score,
            reasons=reasons,
            requires_human_confirmation=(
                decision
                == Decision.APPROVAL_REQUIRED
            ),
            reversible=(
                metadata.risk
                not in {
                    ToolRisk.CRITICAL
                }
            ),
            user_authorized=(
                decision == Decision.ALLOW
            ),
        )