from enum import Enum


class AgentState(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    PLANNING = "planning"
    AWAITING_APPROVAL = "awaiting_approval"
    EXECUTING = "executing"
    VALIDATING = "validating"
    RESPONDING = "responding"
    COMPLETED = "completed"

    INTERRUPTED = "interrupted"
    RECONCILING = "reconciling"

    RECOVERING = "recovering"
    FAILED = "failed"
    CANCELLED = "cancelled"


TRANSITIONS = {
    AgentState.IDLE: {
        AgentState.LISTENING,
        AgentState.THINKING,
    },

    AgentState.LISTENING: {
        AgentState.THINKING,
        AgentState.IDLE,
        AgentState.INTERRUPTED,
    },

    AgentState.THINKING: {
        AgentState.PLANNING,
        AgentState.RESPONDING,
        AgentState.INTERRUPTED,
        AgentState.FAILED,
    },

    AgentState.PLANNING: {
        AgentState.AWAITING_APPROVAL,
        AgentState.EXECUTING,
        AgentState.RESPONDING,
        AgentState.INTERRUPTED,
        AgentState.FAILED,
    },

    AgentState.AWAITING_APPROVAL: {
        AgentState.EXECUTING,
        AgentState.CANCELLED,
        AgentState.INTERRUPTED,
    },

    AgentState.EXECUTING: {
        AgentState.VALIDATING,
        AgentState.INTERRUPTED,
        AgentState.RECOVERING,
        AgentState.FAILED,
        AgentState.CANCELLED,
    },

    AgentState.VALIDATING: {
        AgentState.RESPONDING,
        AgentState.RECOVERING,
        AgentState.FAILED,
        AgentState.INTERRUPTED,
    },

    AgentState.RESPONDING: {
        AgentState.COMPLETED,
        AgentState.INTERRUPTED,
    },

    AgentState.COMPLETED: {
        AgentState.IDLE,
        AgentState.LISTENING,
    },

    AgentState.INTERRUPTED: {
        AgentState.RECONCILING,
        AgentState.CANCELLED,
    },

    AgentState.RECONCILING: {
        AgentState.PLANNING,
        AgentState.EXECUTING,
        AgentState.RESPONDING,
        AgentState.FAILED,
    },

    AgentState.RECOVERING: {
        AgentState.EXECUTING,
        AgentState.RESPONDING,
        AgentState.FAILED,
    },

    AgentState.FAILED: {
        AgentState.RECOVERING,
        AgentState.IDLE,
    },

    AgentState.CANCELLED: {
        AgentState.IDLE,
    },
}


class InvalidStateTransition(Exception):
    pass


class StateMachine:

    def __init__(self):
        self.current_state = AgentState.IDLE

    def can_transition(self, new_state: AgentState) -> bool:
        return new_state in TRANSITIONS.get(
            self.current_state,
            set()
        )

    def transition(self, new_state: AgentState):
        if not self.can_transition(new_state):
            raise InvalidStateTransition(
                f"Cannot transition from "
                f"{self.current_state.value} "
                f"to {new_state.value}"
            )

        previous_state = self.current_state
        self.current_state = new_state

        return previous_state, new_state