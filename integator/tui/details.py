from iterpy import Arr
from textual import work
from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widgets import Label

from integator.task_status import ExecutionState, Statuses, TaskStatus
from integator.task_status_repo import TaskStatusRepo


class Details(Label):
    """A screen to show the details of a ListItem."""

    hash: reactive[str] = reactive("", recompose=True)
    statuses: reactive[Statuses]

    def __init__(self, hash: str, classes: str) -> None:
        super().__init__(classes=classes)
        self.hash = hash
        self.statuses = Statuses()

    @work(thread=True, exclusive=True)
    def _update(self) -> None:
        self.statuses = TaskStatusRepo.get(self.hash)

    @staticmethod
    def _status_line(status: TaskStatus) -> str:
        base = f"{status.state} {status.task.name} ({status.span}): {status.log}"
        if status.state != ExecutionState.FAILURE:
            return base
        return f"""{base}

Log excerpt:
{status.tail(20)}
"""

    def compose(self) -> ComposeResult:
        self._update()
        self.set_timer(1 / 3, self.recompose)

        if self.hash == "":
            yield Label("No highlighted item")
        else:
            yield Label(
                "\n".join(Arr(self.statuses.values).map(self._status_line)),
            )
