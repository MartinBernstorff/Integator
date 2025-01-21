from iterpy import Arr
from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widgets import Label

from integator.task_status_repo import TaskStatusRepo


class Details(Label):
    """A screen to show the details of a ListItem."""

    hash: reactive[str] = reactive("", recompose=True)

    def __init__(self, hash: str, classes: str) -> None:
        super().__init__(classes=classes)
        self.hash = hash

    def compose(self) -> ComposeResult:
        statuses = TaskStatusRepo.get(self.hash)

        self.set_timer(1, self.refresh)

        if self.hash == "":
            yield Label("No highlighted item")
        else:
            yield Label(
                "\n".join(
                    Arr(statuses.values).map(
                        lambda it: f"{it.task.name}\n{it.state}: {it.log}\n"
                    )
                ),
            )
