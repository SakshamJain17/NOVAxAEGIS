from app.runtime.events import AgentEvent, EventType
from app.runtime.event_bus import EventBus
from app.runtime.tasks import Task, TaskStatus


def test_event_creation():
    event = AgentEvent(
        event_type=EventType.USER_INPUT,
        data={"text": "Hello AEGIS"},
    )

    assert event.event_type == EventType.USER_INPUT
    assert event.data["text"] == "Hello AEGIS"
    assert event.event_id


def test_event_bus():
    bus = EventBus()

    received = []

    def handler(event):
        received.append(event)

    bus.subscribe(handler)

    event = AgentEvent(
        event_type=EventType.USER_INPUT
    )

    bus.publish(event)

    assert len(received) == 1
    assert received[0] == event


def test_task_creation():
    task = Task(
        instruction="Find laptops under ₹80,000"
    )

    assert task.version == 1
    assert task.status == TaskStatus.ACTIVE


def test_task_versioning():
    task = Task(
        instruction="Find laptops under ₹80,000"
    )

    assert task.version == 1

    task.update(
        "Find laptops under ₹60,000 with 16GB RAM"
    )

    assert task.version == 2
    assert task.instruction == (
        "Find laptops under ₹60,000 with 16GB RAM"
    )


def test_task_supersede():
    task = Task(
        instruction="Find laptops"
    )

    task.supersede()

    assert task.status == TaskStatus.SUPERSEDED