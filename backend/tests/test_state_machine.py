import pytest

from app.runtime.state_machine import (
    AgentState,
    InvalidStateTransition,
    StateMachine,
)


def test_initial_state():
    machine = StateMachine()

    assert machine.current_state == AgentState.IDLE


def test_valid_transition():
    machine = StateMachine()

    machine.transition(AgentState.THINKING)

    assert machine.current_state == AgentState.THINKING


def test_invalid_transition():
    machine = StateMachine()

    with pytest.raises(InvalidStateTransition):
        machine.transition(AgentState.EXECUTING)


def test_normal_execution_flow():
    machine = StateMachine()

    machine.transition(AgentState.THINKING)
    machine.transition(AgentState.PLANNING)
    machine.transition(AgentState.EXECUTING)
    machine.transition(AgentState.VALIDATING)
    machine.transition(AgentState.RESPONDING)
    machine.transition(AgentState.COMPLETED)

    assert machine.current_state == AgentState.COMPLETED


def test_interruption_flow():
    machine = StateMachine()

    machine.transition(AgentState.THINKING)
    machine.transition(AgentState.PLANNING)
    machine.transition(AgentState.EXECUTING)

    machine.transition(AgentState.INTERRUPTED)
    machine.transition(AgentState.RECONCILING)
    machine.transition(AgentState.PLANNING)

    assert machine.current_state == AgentState.PLANNING


def test_recovery_flow():
    machine = StateMachine()

    machine.transition(AgentState.THINKING)
    machine.transition(AgentState.PLANNING)
    machine.transition(AgentState.EXECUTING)
    machine.transition(AgentState.RECOVERING)

    machine.transition(AgentState.EXECUTING)

    assert machine.current_state == AgentState.EXECUTING