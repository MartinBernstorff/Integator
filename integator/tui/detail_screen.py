from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Label


class DetailScreen(Screen[None]):
    """A screen to show the details of a ListItem."""

    BINDINGS = [("escape", "app.pop_screen", "Pop the current screen")]

    def __init__(self, hash: str) -> None:
        super().__init__()
        self.hash = hash

    def compose(self) -> ComposeResult:
        yield Label(f"ON screen for {self.hash}!")
