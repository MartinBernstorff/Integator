import datetime as dt
import re
from enum import Enum, auto

import pydantic
import pytimeparse
from pydantic import Field

from integator.emojis import Emojis


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


class ExecutionState(Enum):
    UNKNOWN = auto()
    IN_PROGRESS = auto()
    SKIPPED = auto()
    FAILURE = auto()
    SUCCESS = auto()

    def __str__(self):
        match self:
            case self.UNKNOWN:
                return Emojis.UNKNOWN.value
            case self.IN_PROGRESS:
                return Emojis.IN_PROGRESS.value
            case self.FAILURE:
                return Emojis.FAIL.value
            case self.SUCCESS:
                return Emojis.OK.value


class Task(pydantic.BaseModel):
    name: str
    cmd: str


class TaskStatus(pydantic.BaseModel):
    task: Task
    state: ExecutionState
    duration: dt.timedelta


class Statuses(pydantic.BaseModel):
    values: list[TaskStatus] = Field(default_factory=list)

    @classmethod
    def from_str(
        cls: type["Statuses"], line: str, expected_names: set[str]
    ) -> "Statuses":
        exist = cls.model_validate_json(line)
        existing_names = {status.task.name for status in exist.values}

        missing_names = expected_names - existing_names

        for name in missing_names:
            exist.values.append(
                TaskStatus(
                    task=Task(name=name, cmd="UNKNOWN"),
                    state=ExecutionState.UNKNOWN,
                    duration=dt.timedelta(),
                )
            )
        return exist

    def get(self, name: str) -> TaskStatus:
        return next((status for status in self.values if status.task.name == name))

    def update(self, status: ExecutionState, name: str):
        self.get(name).state = status

    def set_ok(self, name: str):
        self.update(ExecutionState.SUCCESS, name)

    def set_failed(self, name: str):
        self.update(ExecutionState.FAILURE, name)

    def contains(self, status: ExecutionState) -> bool:
        return any(task.state == status for task in self.values)

    def all(self, compare: ExecutionState) -> bool:
        return all(task.state == compare for task in self.values)


class Commit(pydantic.BaseModel):
    hash: str
    timestamp: dt.datetime
    author: str
    statuses: Statuses
    pushed: bool

    @staticmethod
    def from_str(line: str):
        dto = parse_commit_str(line)
        try:
            statuses = Statuses().model_validate_json(dto.notes)
        except pydantic.ValidationError:
            statuses = Statuses()

        return Commit(
            hash=dto.hash,
            timestamp=dto.timestamp,
            author=dto.author,
            statuses=statuses,
            pushed=False,
        )

    def __str__(self):
        return f"{self.statuses}"

    # TODO: Move these to the statuses collection
    def is_pushed(self) -> bool:
        return self.statuses.contains(ExecutionState.IN_PROGRESS)

    def is_failed(self, name: str) -> bool:
        return self.statuses.get(name).state == ExecutionState.FAILURE

    def has_failed(self) -> bool:
        return self.statuses.contains(ExecutionState.FAILURE)

    def is_ok(self, name: str) -> bool:
        return self.statuses.get(name).state == ExecutionState.SUCCESS

    def all_ok(self) -> bool:
        return self.statuses.all(ExecutionState.SUCCESS)


# DTO to handle the empty note. Only parse the TaskStatus' if they exist.
