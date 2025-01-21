from textual.app import App, ComposeResult
from textual.reactive import reactive
from textual.widgets import DataTable, Footer

from integator.settings import RootSettings
from integator.tui.commit_list import CommitList
from integator.tui.detail_screen import DetailScreen


class IntegatorTUI(App[None]):
    """A Textual app to manage stopwatches."""

    settings: reactive[RootSettings] = reactive(RootSettings())
    commit_list: CommitList

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        self.commit_list = CommitList(self.settings)
        yield self.commit_list
        yield Footer()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        row_key = event.row_key.value
        if row_key is None:
            raise ValueError("No row key selected")
        self.push_screen(DetailScreen(row_key))


# TODO:
# - Auto-update the list based on status changes
# - Status bar color based on last status
# - Info pane based on selected item and width of window

if __name__ == "__main__":
    app = IntegatorTUI()
    app.run()
