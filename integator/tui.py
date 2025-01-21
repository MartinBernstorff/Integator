import datetime as dt

from textual import events, work
from textual.app import App, ComposeResult
from textual.reactive import reactive
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import DataTable, Label

from integator.columns import status_row
from integator.commit import Commit
from integator.git import Git
from integator.git_log import GitLog
from integator.settings import RootSettings
from integator.task_status import ExecutionState, Statuses
from integator.task_status_repo import TaskStatusRepo


class DetailScreen(Screen[None]):
    """A screen to show the details of a ListItem."""

    BINDINGS = [("escape", "app.pop_screen", "Pop the current screen")]

    def __init__(self, hash: str) -> None:
        super().__init__()
        self.hash = hash

    def compose(self) -> ComposeResult:
        yield Label(f"ON screen for {self.hash}!")


def label_string(pair: tuple[Commit, Statuses], task_names: list[str]) -> str:
    entry = pair[0]
    return f"{entry.hash[0:4]} {''.join(status_row(pair, task_names))}"


class CommitList(Widget):
    selected_hash: reactive[str] = reactive("")
    last_update: dt.datetime = dt.datetime.now()
    rows: list[tuple[Commit, Statuses]] = []

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        key = event.row_key.value
        if key is not None:
            self.selected_hash = key

    def __init__(self, settings: RootSettings):
        super().__init__()
        self.settings = settings
        self.git = Git(source_dir=self.settings.integator.source_dir, log=GitLog())
        self.columns = [*self.settings.task_names()]

    def compose(self) -> ComposeResult:
        yield DataTable(cursor_type="row")

    def on_mount(self) -> None:
        table: DataTable[ExecutionState] = self.query_one(DataTable)
        for column in self.columns:
            table.add_column(column, key=column)

        commits = self.git.log.get(8)
        pairs = [
            (entry, TaskStatusRepo().get(entry.hash)) for entry in reversed(commits)
        ]
        for pair in pairs:
            self._add_row(pair)

        self.update()
        self.timer = self.set_interval(1, self.update)

    @work(exclusive=True, thread=True)
    def update(self) -> None:
        commits = self.git.log.get(8)
        self.rows = [(entry, TaskStatusRepo().get(entry.hash)) for entry in commits]

        table: DataTable[ExecutionState] = self.query_one(DataTable)
        row_keys = {v.key.value for v in table.rows.values()}
        for row in self.rows:
            if row[0].hash not in row_keys:
                self._add_row(row)
                continue
            self._update_row(row)

    def _row_key(self, commit: Commit) -> str:
        return commit.hash

    def _add_row(self, pair: tuple[Commit, Statuses]) -> None:
        table: DataTable[ExecutionState] = self.query_one(DataTable)
        statuses = pair[1]
        table.add_row(
            *self._get_values_for_columns(statuses),
            label=pair[0].hash,
            key=self._row_key(pair[0]),
        )

    def _get_values_for_columns(self, statuses: Statuses) -> list[ExecutionState]:
        return [statuses.get(name).state for name in self.columns]

    def _update_row(self, row: tuple[Commit, Statuses]) -> None:
        table: DataTable[ExecutionState] = self.query_one(DataTable)
        for column_name in self.columns:
            value = row[1].get(column_name).state
            table.update_cell(self._row_key(row[0]), column_name, value)


class IntegatorTUI(App[None]):
    """A Textual app to manage stopwatches."""

    settings: reactive[RootSettings] = reactive(RootSettings())
    commit_list: CommitList

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        self.commit_list = CommitList(self.settings)
        yield self.commit_list

    def on_key(self, event: events.Key) -> None:
        if event.key == "enter" and self.commit_list.selected_hash:
            screen = DetailScreen(self.commit_list.selected_hash)
            self.push_screen(screen)


# TODO:
# - Auto-update the list based on status changes
# - Status bar color based on last status
# - Info pane based on selected item and width of window

if __name__ == "__main__":
    app = IntegatorTUI()
    app.run()
