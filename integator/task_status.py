import datetime as dt
import pathlib
import re
from enum import Enum, auto

import humanize
import pydantic
import pytimeparse  # type: ignore
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

        if match is None:
            raise ValueError(f"Could not find {name} in {line}")

        result: str = match.group(1)  # type: ignore

        if name == "timestamp":
            seconds = pytimeparse.parse(result)  # type: ignore

            if seconds is None:
                raise ValueError(f"Invalid time: {result}")

            time_since = dt.datetime.now() - dt.timedelta(seconds=seconds)

            results[name] = time_since
        elif name == "notes":
            if result == "":
                results[name] = '{"values": []}'
            else:
                results[name] = result
        else:
            results[name] = result if match else ""

    return CommitDTO(**results)  # type: ignore


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
            case self.SKIPPED:
                return Emojis.SKIPPED.value


class Task(pydantic.BaseModel):
    name: str
    cmd: str


class TaskStatus(pydantic.BaseModel):
    task: Task
    state: ExecutionState
    duration: dt.timedelta
    log_location: pathlib.Path | None


class Statuses(pydantic.BaseModel):
    values: list[TaskStatus] = Field(default_factory=list)

    def __str__(self):
        return f"[{''.join(str(status.state) for status in self.values)}]"

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
                    log_location=None,
                )
            )
        return exist

    def names(self) -> set[str]:
        return {status.task.name for status in self.values}

    def get(self, name: str) -> TaskStatus:
        matching = [task for task in self.values if task.task.name == name]

        if len(matching) == 0:
            return TaskStatus(
                task=Task(name=name, cmd="UNKNOWN"),
                state=ExecutionState.UNKNOWN,
                duration=dt.timedelta(),
                log_location=None,
            )
        return matching[0]

    def update(self, status: ExecutionState, name: str):
        self.get(name).state = status

    def set_ok(self, name: str):
        self.update(ExecutionState.SUCCESS, name)

    def create_ok(self, name: str):
        self.values.append(
            TaskStatus(
                task=Task(name=name, cmd="From main"),
                state=ExecutionState.SUCCESS,
                duration=dt.timedelta(),
                log_location=None,
            )
        )

    def set_failed(self, name: str):
        self.update(ExecutionState.FAILURE, name)

    def contains(self, status: ExecutionState) -> bool:
        return any(task.state == status for task in self.values)

    def all(self, compare: ExecutionState) -> bool:
        return all(task.state == compare for task in self.values)

    def get_failures(self) -> list[TaskStatus]:
        return [task for task in self.values if task.state == ExecutionState.FAILURE]


class Commit(pydantic.BaseModel):
    hash: str
    timestamp: dt.datetime
    author: str
    statuses: Statuses
    pushed: bool

    def __str__(self):
        line = f"({self.hash[0:4]}) {self.statuses}"
        line += f" {humanize.naturaldelta(dt.datetime.now() - self.timestamp)} ago"
        if self.pushed:
            line += f" {Emojis.PUSHED.value} "
        return line

    @staticmethod
    def from_str(line: str, expected_names: set[str]) -> "Commit":
        dto = parse_commit_str(line)
        try:
            statuses = Statuses().from_str(dto.notes, expected_names)
        except pydantic.ValidationError:
            statuses = Statuses()

        return Commit(
            hash=dto.hash,
            timestamp=dto.timestamp,
            author=dto.author,
            statuses=statuses,
            pushed=False,
        )

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

    def age(self) -> dt.timedelta:
        return dt.datetime.now() - self.timestamp


# DTO to handle the empty note. Only parse the TaskStatus' if they exist.
