from __future__ import annotations

from dataclasses import dataclass

from app.safety.models import (
    ActionProposal,
    Decision,
    RiskAssessment,
    RiskLevel,
)


@dataclass(frozen=True, slots=True)
class PolicyConfig:
    minimum_confidence: float = 0.55

    block_critical: bool = True

    require_confirmation_above: float = 0.30


class SafetyPolicy:

    def __init__(
        self,
        config: PolicyConfig | None = None,
    ) -> None:
        self.config = config or PolicyConfig()

    def evaluate(
        self,
        proposal: ActionProposal,
        assessment: RiskAssessment,
    ) -> Decision:

        if (
            proposal.confidence
            < self.config.minimum_confidence
        ):
            return Decision.APPROVAL_REQUIRED

        if (
            self.config.block_critical
            and assessment.level
            == RiskLevel.CRITICAL
        ):
            return Decision.BLOCK

        if (
            assessment.score
            >= self.config.require_confirmation_above
        ):
            return Decision.APPROVAL_REQUIRED

        return Decision.ALLOW