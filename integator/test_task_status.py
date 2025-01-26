import datetime as dt
from pathlib import Path

from integator.step_status import (
    ExecutionState,
    Span,
    Statuses,
    StepStatus,
    Task,
)


def dummy_status():
    return Statuses(
        values=[
            StepStatus(
                step=Task(name=str("Test 1"), cmd=str("echo")),
                state=ExecutionState.IN_PROGRESS,
                span=Span(start=dt.datetime.now(), end=dt.datetime.now()),
                log=Path(),
            )
        ]
    )


def test_init_stepstati():
    input = dummy_status().model_dump_json()
    val = Statuses().from_str(input)
    assert len(val.values) == 1
