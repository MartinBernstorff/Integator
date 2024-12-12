from iterpy import Arr

from integator.commit import Commit
from integator.task_status import Statuses


def status(pairs: list[tuple[Commit, Statuses]], task_names: list[str]) -> list[str]:
    return (
        Arr(pairs)
        .map(lambda pair: _status_row(pair, task_names))
        .map(lambda statuses: "".join(statuses))
        .to_list()
    )


def _status_row(pair: tuple[Commit, Statuses], task_names: list[str]) -> list[str]:
    return [pair[1].get(cmd).state.__str__() for cmd in task_names]
