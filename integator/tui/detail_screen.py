from iterpy import Arr
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static

from integator.task_status_repo import TaskStatusRepo


class DetailScreen(Screen[None]):
    """A screen to show the details of a ListItem."""

    BINDINGS = [("escape", "app.pop_screen", "Pop the current screen")]

    def __init__(self, hash: str) -> None:
        super().__init__()
        self.hash = hash

    def compose(self) -> ComposeResult:
        statuses = TaskStatusRepo.get(self.hash)

        yield Static(
            "\n".join(
                Arr(statuses.values).map(
                    lambda it: f"{it.task.name}\n{it.state}: {it.log}\n"
                )
            ),
        )
