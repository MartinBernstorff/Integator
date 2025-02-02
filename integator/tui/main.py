from textual.app import App, ComposeResult
from textual.reactive import reactive
from textual.widgets import DataTable

from integator.settings import RootSettings
from integator.tui.commit_list import CommitList
from integator.tui.details import Details


class IntegatorTUI(App[None]):
    """A Textual app to manage stopwatches."""

    CSS = """
Screen {
    layout: horizontal;
    overflow-x: auto;
}

.box {
    height: 100%;
    width: 1fr;
    border: solid black;
    overflow-x: auto;
    overflow-y: auto;
}"""

    settings: reactive[RootSettings]
    commit_list: reactive[CommitList]
    details: Details

    def __init__(self, settings: RootSettings) -> None:
        super().__init__()
        self.settings = settings

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        self.commit_list = CommitList(self.settings, classes="box")
        yield self.commit_list

        self.details = Details(self.commit_list.selected_hash, classes="box")
        yield self.details

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        row_key = event.row_key.value
        if row_key is None:
            raise ValueError("No row key selected")
        self.details.hash = row_key

    def on_data_table_cell_highlighted(self, event: DataTable.CellHighlighted) -> None:
        self.details.hash = self.commit_list.selected_hash
