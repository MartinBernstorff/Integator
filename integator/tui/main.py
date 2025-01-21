from textual import events
from textual.app import App, ComposeResult
from textual.reactive import reactive

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
