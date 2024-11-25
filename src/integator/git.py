import datetime
import re
from abc import ABC
from dataclasses import dataclass

import humanize
from pytimeparse import parse

from .cons import Emojis
from .shell import Shell

# TODO: Add worktree creation and cd'ing


@dataclass
class LogEntry:
    time_since: datetime.timedelta
    hash: str
    notes: str

    def __repr__(self) -> str:
        line = f"{self.hash}"

        if statuses := self.statuses():
            line = f"[{''.join(statuses)}] {line}"

        line += f" {humanize.naturaldelta(self.time_since)}"
        return line


    @staticmethod
    def parse_from_line(line: str) -> "LogEntry":
        regex = r"^(\w+)\s+(\d+)\s+(\w+)\s+ago\s+(.+)$"
        match = re.match(regex, line)

        hash = match.group(1)
        time_int = int(match.group(2))
        time_unit = match.group(3)
        rest = match.group(4)

        if not match:
            raise ValueError(f"Invalid line: {line}")

        time_string = f"{time_int} {time_unit}"
        time_since = parse(time_string)

        if time_since is None:
            raise ValueError(f"Could not parse: {time_string}")

        return LogEntry(
            hash=hash,
            time_since=datetime.timedelta(seconds=time_since),
            notes=rest,
        )

    def statuses(self) -> list[str]:
        regex = r"\[.+\]"
        match = re.search(regex, self.notes)
        if not match:
            return []
        emojis = match.group(0).strip("[]")
        return list(emojis)

    def is_pushed(self) -> bool:
        return Emojis.PUSHED.value in self.notes

    def is_ok(self, position: int) -> bool:
        if len(statuses := self.statuses()) <= position:
            return False
        return statuses[position] == Emojis.OK.value

    def is_failed(self, position: int) -> bool:
        if len(statuses := self.statuses()) <= position:
            return False
        return statuses[position] == Emojis.FAIL.value


class Git(ABC):
    def log(self) -> list[LogEntry]: ...
    def print_log(self, entries: list[LogEntry]): ...

    @staticmethod
    def impl() -> "Git":
        return GitImpl()


class GitImpl(Git):
    def _print_status_line(self, entries: list[LogEntry]):
        ok_entries = [entry for entry in entries if entry.is_ok(0)]
        if ok_entries:
            ok_entry = ok_entries[-1]
            print(f"Last commit passing tests:\n\t{ok_entry}")
        else:
            print("No commit has passing tests yet")

    def log(self):
        values = Shell.impl().run(
            "git log -n 10 --pretty=format:'%C(auto)%h %C(green)%ar %C(auto)%aN %N%-C() ' --date=format:'%H:%M'"
        )

        if not values:
            raise RuntimeError("No values returned from git log")

        return [LogEntry.parse_from_line(value) for value in values]

    def print_log(self, log_entries: list[LogEntry]):
        print("Log:")
        for entry in log_entries:
            print(f"\t{entry}")

        Shell.impl().clear()
        self._print_status_line(log_entries)

        # Print current time
        print(f"\n{datetime.datetime.now().strftime('%H:%M:%S')}")
