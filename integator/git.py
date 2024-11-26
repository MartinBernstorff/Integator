import datetime
import pathlib

from integator.log_entry import LogEntry
from integator.shell import Shell


class Git:
    def checkout_latest_commit(self, source_dir: pathlib.Path):
        values = Shell.impl().run_quietly(f"git -C {source_dir} rev-parse HEAD")

        if not values:
            raise RuntimeError("No commit found")

        Shell.impl().run_quietly(f"git checkout {values[0]}")

    def get_notes(self) -> str | None:
        values = Shell.impl().run_quietly("git notes show")
        if not values:
            return None
        return values[0]

    def update_notes(self, notes: str):
        Shell.impl().run_quietly(f"git notes add -f -m '{notes}'")

    def get_log(self, n_statuses: int) -> list[LogEntry]:
        values = Shell.impl().run_quietly(
            'git log -n 10 --pretty=format:"C|%h| T|%ar| A|%aN| N|%N%-C()|%-C()"'
        )

        if not values:
            raise RuntimeError("No values returned from git log")

        entries = [LogEntry.from_str(value, n_statuses=n_statuses) for value in values]
        valid_entries = [e for e in entries if e]
        if not valid_entries:
            raise RuntimeError("No entries parsed from git log")

        return valid_entries

    def print_log(self, log_entries: list[LogEntry]):
        Shell.impl().clear()

        print("Log:")
        for entry in log_entries:
            print(f"\t{entry.__str__()}")

        self._print_status_line(log_entries)

        # Print current time
        print(f"\n{datetime.datetime.now().strftime('%H:%M:%S')}")

    def _print_status_line(self, entries: list[LogEntry]):
        ok_entries = [entry for entry in entries if entry.is_ok(0)]
        if ok_entries:
            ok_entry = ok_entries[-1]
            print(f"Last commit passing tests:\n\t{ok_entry.__str__()}")
        else:
            print("No commit has passing tests yet")
