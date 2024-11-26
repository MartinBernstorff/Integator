import datetime
import pathlib
from dataclasses import dataclass

from integator.log_entry import LogEntry
from integator.shell import Shell


@dataclass
class Log:
    n_statuses: int

    def get_all(self) -> list[LogEntry]:
        values = Shell().run_quietly(
            'git log -n 10 --pretty=format:"C|%h| T|%ar| A|%aN| N|%N%-C()|%-C()"'
        )

        if not values:
            raise RuntimeError("No values returned from git log")

        entries = [LogEntry.from_str(value, self.n_statuses) for value in values]
        valid_entries = [e for e in entries if e]
        if not valid_entries:
            raise RuntimeError("No entries parsed from git log")

        return valid_entries

    def latest(self) -> LogEntry:
        return self.get_all()[0]


@dataclass
class Git:
    source_dir: pathlib.Path
    log: Log

    def push(self):
        latest_commit = self._latest_commit()
        source_branch = self._source_branch()

        Shell().run_quietly(f"git push origin {latest_commit}:{source_branch}")

    def _latest_commit(self) -> str:
        values = Shell().run_quietly(f"git -C {self.source_dir} rev-parse HEAD")
        if not values:
            raise RuntimeError("No commit found")
        return values[0]

    def _source_branch(self) -> str:
        values = Shell().run_quietly(f"git -C {self.source_dir} branch --show-current")

        if not values:
            raise RuntimeError("No branch found")

        return values[0]

    def checkout_latest_commit(self):
        latest_commit = self._latest_commit()
        Shell().run_quietly(f"git checkout {latest_commit}")

    def get_notes(self) -> str | None:
        values = Shell().run_quietly("git notes show")
        if not values:
            return None
        return values[0]

    def update_notes(self, notes: str):
        Shell().run_quietly(f"git notes add -f -m '{notes}'")

    def get_log(self, n_statuses: int) -> list[LogEntry]:
        values = Shell().run_quietly(
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
        Shell().clear()

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
