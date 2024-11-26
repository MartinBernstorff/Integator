import datetime
from dataclasses import dataclass

import humanize

from integator.commit_parser import parse_commit
from integator.cons import Emojis


@dataclass
class Statuses:
    values: list[str]
    size: int

    def __str__(self) -> str:
        return "".join(self.values)

    def __post_init__(self):
        deficit = self.size - len(self.values)
        if deficit > 0:
            self.values += ["?"] * deficit

    def update(self, status: str, position: int):
        self.values[position] = status

    def contains(self, status: str) -> bool:
        return status in self.values

    def all(self, compare: str) -> bool:
        return all(status == compare for status in self.values)


@dataclass
class LogEntry:
    time_since: datetime.timedelta
    hash: str
    author: str
    notes: str
    statuses: Statuses

    def __repr__(self) -> str:
        return (
            f"({self.hash}) [{self.statuses}] {humanize.naturaldelta(self.time_since)}"
        )

    def __str__(self) -> str:
        line = f"C|{self.hash}| T|{humanize.naturaldelta(self.time_since)} ago| A|{self.author}| N|{self.note()}|"
        return line

    def note(self) -> str:
        if not self.statuses:
            return self.notes
        return f"[{self.statuses}] {self.notes}".strip()

    @staticmethod
    def from_str(line: str, n_statuses: int) -> "LogEntry":
        result = parse_commit(line, n_statuses)
        statuses = Statuses(values=result["statuses"], size=n_statuses)
        return LogEntry(
            time_since=result["time"],
            hash=result["commit"],
            author=result["author"],
            notes=result["notes"],
            statuses=statuses,
        )

    def set_ok(self, position: int):
        self.statuses.update(Emojis.OK.value, position)

    def set_failed(self, position: int):
        self.statuses.update(Emojis.FAIL.value, position)

    def is_pushed(self) -> bool:
        return self.statuses.contains(Emojis.PUSHED.value)

    def is_failed(self, position: int) -> bool:
        return self.statuses.values[position] == Emojis.FAIL.value

    def has_failed(self) -> bool:
        return self.statuses.contains(Emojis.FAIL.value)

    def is_ok(self, position: int) -> bool:
        return self.statuses.values[position] == Emojis.OK.value

    def all_ok(self) -> bool:
        return self.statuses.all(Emojis.OK.value)
