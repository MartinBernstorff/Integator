import datetime as dt
from pathlib import Path

from integator.task_status import (
    CommandName,
    ExecutionState,
    Statuses,
    Task,
    TaskName,
    TaskStatus,
)


def test_status():
    return Statuses(
        values=[
            TaskStatus(
                task=Task(name=TaskName("Test 1"), cmd=CommandName("echo")),
                state=ExecutionState.IN_PROGRESS,
                span=(dt.datetime.now(), dt.datetime.now()),
                log=Path(),
            )
        ]
    )


def test_init_taskstati():
    input = test_status().model_dump_json()
    val = Statuses().from_str(input)
    assert len(val.values) == 1
