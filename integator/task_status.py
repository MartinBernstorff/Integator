import datetime as dt
import re
from enum import Enum, auto

import pydantic
import pytimeparse
from pydantic import Field


class CommitDTO(pydantic.BaseModel):
    hash: str
    timestamp: dt.datetime
    author: str
    notes: str


def parse_commit_str(line: str):
    regexes = [
        ("hash", r"^C\|(.*?)\|"),
        ("timestamp", r"T\|(.*?)\s+ago\|"),
        ("author", r"A\|(.*?)\|"),
        ("notes", r"N\|(.*?)\|"),
    ]

    results = {}

    for name, regex in regexes:
        match = re.search(regex, line)

        if name == "timestamp":
            seconds = pytimeparse.parse(match.group(1))

            if seconds is None:
                raise ValueError(f"Invalid time: {match.group(1)}")

            time_since = dt.datetime.now() - dt.timedelta(seconds=seconds)

            results[name] = time_since
        elif name == "notes":
            if match.group(1) == "":
                results[name] = '{"values": []}'
            else:
                results[name] = match.group(1)
        else:
            results[name] = match.group(1) if match else ""

    return CommitDTO(**results)


class ExecutionStatus(Enum):
    UNKNOWN = auto()
    IN_PROGRESS = auto()
    SKIPPED = auto()
    FAILURE = auto()
    SUCCESS = auto()

    def __str__(self):
        match self.name:
            case "UNKNOWN":
                return "🌀"
            case "IN_PROGRESS":
                return "⏳"
            case "FAILURE":
                return "❌"
            case "SUCCESS":
                return "✅"


class TaskStatus(pydantic.BaseModel):
    name: str
    command: str
    status: ExecutionStatus
    duration: dt.timedelta


class TaskStati(pydantic.BaseModel):
    values: list[TaskStatus] = Field(default_factory=list)

    def update(self, status: ExecutionStatus, position: int):
        self.values[position].status = status

    def contains(self, status: ExecutionStatus) -> bool:
        return any(task.status == status for task in self.values)

    def all(self, compare: ExecutionStatus) -> bool:
        return all(task.status == compare for task in self.values)


class Commit(pydantic.BaseModel):
    hash: str
    timestamp: dt.datetime
    author: str
    stati: TaskStati
    pushed: bool

    @staticmethod
    def from_str(line: str):
        dto = parse_commit_str(line)
        try:
            stati = TaskStati().model_validate_json(dto.notes)
        except pydantic.ValidationError:
            stati = TaskStati()

        return Commit(
            hash=dto.hash,
            timestamp=dto.timestamp,
            author=dto.author,
            stati=stati,
            pushed=False,
        )

    def __str__(self):
        return f"{self.stati}"


# DTO to handle the empty note. Only parse the TaskStatus' if they exist.
# XXX: Remove log_entry
