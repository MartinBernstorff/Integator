import datetime

from integator.log_entry import LogEntry
from integator.shell import Shell

# TODO: Add worktree creation and cd'ing


class Git:
    def get_notes(self) -> str | None:
        values = Shell.impl().run("git notes show")
        if not values:
            return None
        return values[0]

    def update_notes(self, notes: str):
        Shell.impl().interactive_cmd(f"git notes add -f -m '{notes}'")

    def get_log(self, n_statuses: int) -> list[LogEntry]:
        values = Shell.impl().run(
            "git log -n 10 --pretty=format:'%C(auto)%h %C(green)%ar %C(auto)%aN %N%-C() ' --date=format:'%H:%M'"
        )

        if not values:
            raise RuntimeError("No values returned from git log")

        entries = [LogEntry.from_str(value, n_statuses=n_statuses) for value in values]
        if not entries:
            raise RuntimeError("No entries parsed from git log")

        return [e for e in entries if e]

    def print_log(self, log_entries: list[LogEntry]):
        Shell.impl().clear()

        print("Log:")
        for entry in log_entries:
            print(f"\t{entry.to_str()}")

        self._print_status_line(log_entries)

        # Print current time
        print(f"\n{datetime.datetime.now().strftime('%H:%M:%S')}")

    def _print_status_line(self, entries: list[LogEntry]):
        ok_entries = [entry for entry in entries if entry.is_ok(0)]
        if ok_entries:
            ok_entry = ok_entries[-1]
            print(f"Last commit passing tests:\n\t{ok_entry.to_str()}")
        else:
            print("No commit has passing tests yet")
