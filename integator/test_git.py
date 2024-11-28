import pathlib

from integator.git import Git, Log
from integator.task_status import TaskStati


def test_deser_from_log():
    log = Log(n_statuses=2).get()


def test_init_taskstati():
    val = TaskStati().model_validate_json(
        '{"values":[{"name":"Task 1","command":"echo","status":5,"duration":"PT1S"}]}'
    )
    Git(source_dir=pathlib.Path(), log=Log(n_statuses=1)).update_notes(
        val.model_dump_json()
    )
