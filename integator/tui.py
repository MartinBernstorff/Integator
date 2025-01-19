from textual.app import App, ComposeResult
from textual.reactive import var
from textual.screen import Screen
from textual.widgets import Footer, Header, Label, ListItem, ListView

from integator.columns import status_row
from integator.commit import Commit
from integator.git import Git
from integator.git_log import GitLog
from integator.settings import RootSettings
from integator.task_status import Statuses
from integator.task_status_repo import TaskStatusRepo


class DetailScreen(Screen[None]):
    """A screen to show the details of a ListItem."""

    BINDINGS = [("escape", "app.pop_screen", "Pop the current screen")]

    def compose(self) -> ComposeResult:
        yield Label("ON screen!")


def label_string(pair: tuple[Commit, Statuses], task_names: list[str]) -> str:
    entry = pair[0]
    status = pair[1]
    return f"{entry.hash[0:4]} {''.join(status_row(pair, task_names))}"


class IntegatorTUI(App[None]):
    """A Textual app to manage stopwatches."""

    selected_item = var(None)

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        settings = RootSettings()
        git = Git(source_dir=settings.integator.source_dir, log=GitLog())
        commits = git.log.get(8)
        pairs = [(entry, TaskStatusRepo().get(entry.hash)) for entry in commits]

        labels = [
            ListItem(Label(label_string(pair, settings.task_names()))) for pair in pairs
        ]
        self.list_view = ListView(*labels)

        yield Header()
        yield self.list_view
        yield Footer()

    def on_list_view_selected(self, event) -> None:
        """Handle the selection of a ListItem."""
        self.selected_item = event.item

    def on_key(self, event) -> None:
        if event.key == "enter" and self.selected_item:
            self.push_screen(DetailScreen())


if __name__ == "__main__":
    app = IntegatorTUI()
    app.run()
