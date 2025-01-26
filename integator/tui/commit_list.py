import datetime as dt
from dataclasses import dataclass

import humanize
from iterpy import Arr
from textual import work
from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import DataTable
from textual.widgets._data_table import RowKey

from integator.commit import Commit
from integator.git import Git
from integator.settings import RootSettings
from integator.step_status import ExecutionState, Statuses
from integator.step_status_repo import StepStatusRepo


class CommitList(Widget):
    selected_hash: reactive[str] = reactive("")
    last_update: dt.datetime = dt.datetime.now()
    rows: list[tuple[Commit, Statuses]] = []

    CSS = """
.box {
    width: 1fr;
}
"""

    def __init__(self, settings: RootSettings, classes: str = "") -> None:
        super().__init__(classes=classes)
        self.settings = settings
        self.git = Git(source_dir=self.settings.integator.source_dir)
        self.columns = ["Age", *self.settings.step_names()]

    def compose(self) -> ComposeResult:
        table = DataTable(cursor_type="row")  # type: ignore
        yield table

    def on_mount(self) -> None:
        table: DataTable[ExecutionState] = self.query_one(DataTable)
        for column in self.columns:
            table.add_column(column, key=column)

        commits = self.git.log.get(8)
        pairs = [
            (entry, StepStatusRepo().get(entry.hash)) for entry in reversed(commits)
        ]
        for pair in pairs:
            self._add_row(pair)

        self._update()
        self.timer = self.set_interval(0.3, self._update)
        self.post_message(
            DataTable.RowHighlighted(
                data_table=table, cursor_row=0, row_key=RowKey(commits[0].hash)
            )
        )

    @work(exclusive=True, thread=True)
    def _update(self) -> None:
        commits = self.git.log.get(8)
        self.rows = [(entry, StepStatusRepo().get(entry.hash)) for entry in commits]

        table: DataTable[ExecutionState] = self.query_one(DataTable)
        row_keys = {v.key.value for v in table.rows.values()}

        for row in self.rows:
            if row[0].hash not in row_keys:
                self._add_row(row)
                continue
            self._update_row(row)

        table.sort("Age", reverse=True)

    def _row_key(self, commit: Commit) -> str:
        return commit.hash

    def _add_row(self, pair: tuple[Commit, Statuses]) -> None:
        table: DataTable[AgedTimestamp | ExecutionState] = self.query_one(DataTable)

        statuses = pair[1]
        values = [
            AgedTimestamp(pair[0].timestamp),
            *self._get_values_for_columns(statuses),
        ]
        table.add_row(
            *values,
            label=pair[0].hash,
            key=self._row_key(pair[0]),
        )

        if table.cursor_row == 0:
            # If at the top of the list, stay there
            self.selected_hash = pair[0].hash
        else:
            # Otherwise, keep the same element selected
            table.move_cursor(row=table.cursor_row + 1)

        self.post_message(
            DataTable.RowHighlighted(
                data_table=table,
                cursor_row=table.cursor_row,
                row_key=RowKey(self.selected_hash),
            )
        )

    def _update_row(self, row: tuple[Commit, Statuses]) -> None:
        table: DataTable[AgedTimestamp | ExecutionState] = self.query_one(DataTable)
        for column_name in Arr(self.columns):
            if column_name == "Age":
                value = AgedTimestamp(row[0].timestamp)
            else:
                value = row[1].get(column_name).state

            table.update_cell(self._row_key(row[0]), column_name, value)

    def _get_values_for_columns(self, statuses: Statuses) -> list[ExecutionState]:
        return [statuses.get(name).state for name in self.columns if name != "Age"]

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        key = event.row_key.value
        if key is not None:
            self.selected_hash = key


@dataclass
class AgedTimestamp:
    timestamp: dt.datetime

    def __gt__(self, other: "AgedTimestamp") -> bool:
        return self.timestamp > other.timestamp

    def __str__(self) -> str:
        age = dt.datetime.now() - self.timestamp
        return (
            f"{humanize.naturaldelta(age)} ago"
            if age > dt.timedelta(minutes=1)
            else "< 1 minute"
        )
