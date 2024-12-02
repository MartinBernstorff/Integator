import datetime as dt
from pathlib import Path

from integator.task_status import ExecutionState, Statuses, Task, TaskStatus


def test_status():
    return Statuses(
        values=[
            TaskStatus(
                task=Task(name="Test 1", cmd="echo"),
                state=ExecutionState.IN_PROGRESS,
                duration=dt.timedelta(seconds=1),
                log_location=Path(),
            )
        ]
    )


def test_init_taskstati():
    input = test_status().model_dump_json()
    val = Statuses().from_str(input, {"Test 1", "Task 2"})
    assert len(val.values) == 2
