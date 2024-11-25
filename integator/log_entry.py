import datetime
import re
from dataclasses import dataclass
from typing import NewType

import humanize
from pytimeparse import parse

from integator.cons import Emojis

Status = NewType("Status", str)


@dataclass
class LogEntry:
    time_since: datetime.timedelta
    hash: str
    author: str
    notes: str
    statuses: list[Status]

    def to_str(self) -> str:
        line = f"{self.hash} {humanize.naturaldelta(self.time_since)} ago {self.author} {self.note()}"
        return line

    def note(self) -> str:
        return f"[{''.join(self.statuses)}] {self.notes}".strip()

    @staticmethod
    def from_str(line: str, n_statuses: int) -> "LogEntry | None":
        regex = r"^(\w+)\s+(\d+)\s+(\w+)\s+ago\s+(.+)(\[.*\])(.*)$"
        match = re.match(regex, line)

        if not match:
            return None

        hash = match.group(1)
        time_int = int(match.group(2))
        time_unit = match.group(3)
        author = match.group(4).strip()
        statuses = LogEntry._statuses(match.group(5), n_statuses)
        notes = match.group(6).strip()

        time_string = f"{time_int} {time_unit}"
        time_since = parse(time_string)

        if time_since is None:
            return None

        return LogEntry(
            hash=hash,
            time_since=datetime.timedelta(seconds=time_since),
            author=author,
            statuses=statuses,
            notes=notes,
        )

    @staticmethod
    def _statuses(notes: str, n_statuses: int) -> list[Status]:
        regex = r"\[.+\]"
        match = re.search(regex, notes)
        if not match:
            return []
        emojis = match.group(0).strip("[]")

        missing_statuses = n_statuses - len(emojis)
        if missing_statuses > 0:
            emojis += "?" * missing_statuses

        return [Status(emoji) for emoji in emojis]

    def set_ok(self, position: int):
        self.statuses[position] = Status(Emojis.OK.value)

    def set_failed(self, position: int):
        self.statuses[position] = Status(Emojis.FAIL.value)

    def has_status(self) -> bool:
        return len(self.statuses) > 0

    def is_pushed(self) -> bool:
        return Emojis.PUSHED.value in self.statuses

    def is_failed(self, position: int) -> bool:
        if len(self.statuses) <= position:
            return False
        return self.statuses[position] == Emojis.FAIL.value

    def has_failed(self) -> bool:
        return any(status == Emojis.FAIL.value for status in self.statuses)

    def is_ok(self, position: int) -> bool:
        if not self.has_status():
            return False
        return self.statuses[position] == Emojis.OK.value

    def all_ok(self) -> bool:
        return all(status == Emojis.OK.value for status in self.statuses)
