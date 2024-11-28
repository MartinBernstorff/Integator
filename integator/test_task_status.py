import datetime as dt

import pytest

from integator.task_status import Commit, ExecutionStatus, TaskStati, TaskStatus


@pytest.mark.parametrize(
    "val",
    [
        Commit(
            hash="a9c7203",
            timestamp=dt.datetime.now(),
            author="Martin Bernstorff",
            stati=TaskStati(
                values=[
                    TaskStatus(
                        name="Task 1",
                        command="echo 'Hello'",
                        status=ExecutionStatus.SUCCESS,
                        duration=dt.timedelta(seconds=1),
                    ),
                    TaskStatus(
                        name="Task 2",
                        command="echo 'World'",
                        status=ExecutionStatus.SUCCESS,
                        duration=dt.timedelta(seconds=1),
                    ),
                ]
            ),
            pushed=False,
        )
    ],
)
def test_serde_identity(val: Commit):
    ser = val.model_dump_json()
    deser = Commit.model_validate_json(ser)
    assert val == deser
