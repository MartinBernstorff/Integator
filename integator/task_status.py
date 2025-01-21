import datetime as dt
import pathlib
from enum import Enum, auto
from functools import reduce
from typing import Set

import humanize
from pydantic import Field

from integator.basemodel import BaseModel
from integator.emojis import Emojis
from integator.shell import ExitCode


class ExecutionState(Enum):
    UNKNOWN = auto()
    IN_PROGRESS = auto()
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

    @classmethod
    def from_exit_code(cls, exit_code: ExitCode) -> "ExecutionState":
        match exit_code:
            case ExitCode.OK:
                return ExecutionState.SUCCESS
            case ExitCode.ERROR:
                return ExecutionState.FAILURE


class Task(BaseModel):
    name: str
    cmd: str


class Span(BaseModel):
    start: dt.datetime
    end: dt.datetime | None

    def duration(self) -> dt.timedelta:
        if self.start is None or self.end is None:
            return dt.timedelta()

        return self.end - self.start

    def __str__(self):
        return f"{humanize.naturaldelta(self.duration())}"


class TaskStatus(BaseModel):
    task: Task
    state: ExecutionState
    span: Span
    log: pathlib.Path | None

    @classmethod
    def unknown(cls, task: Task) -> "TaskStatus":
        return cls(
            task=task,
            state=ExecutionState.UNKNOWN,
            span=Span(start=dt.datetime.now(), end=None),
            log=None,
        )

    def __repr__(self) -> str:
        return f"{self.task.name}: {self.state}"


class Statuses(BaseModel):
    values: list[TaskStatus] = Field(default_factory=list)

    def __str__(self):
        return f"[{''.join(str(status.state) for status in self.values)}]"

    @classmethod
    def from_str(cls: type["Statuses"], line: str) -> "Statuses":
        return cls.model_validate_json(line)

    def names(self) -> set[str]:
        return {status.task.name for status in self.values}

    def replace(self, new: TaskStatus):
        self.values = [
            status for status in self.values if status.task.name != new.task.name
        ]
        self.add(new)

    def get(self, name: str) -> TaskStatus:
        matching = [task for task in self.values if task.task.name == name]

        if len(matching) == 0:
            new_status = TaskStatus(
                task=Task(name=name, cmd=str("UNKNOWN")),
                state=ExecutionState.UNKNOWN,
                span=Span(start=dt.datetime.now(), end=dt.datetime.now()),
                log=None,
            )
            self.add(new_status)
            return new_status

        return matching[0]

    def duration(self) -> dt.timedelta:
        return reduce(lambda x, y: x + y, [s.span.duration() for s in self.values])

    def add(self, task_status: TaskStatus):
        self.values.append(task_status)

    def contains(self, status: ExecutionState) -> bool:
        return any(task.state == status for task in self.values)

    def all_succeeded(self, names: Set[str]) -> bool:
        return self.all(names, ExecutionState.SUCCESS)

    def all(self, names: Set[str], expected_state: ExecutionState) -> bool:
        for name in names:
            if not self.get(name).state == expected_state:
                return False
        return True

    def get_failures(self) -> list[TaskStatus]:
        return [task for task in self.values if task.state == ExecutionState.FAILURE]

    def has_failed(self) -> bool:
        return self.contains(ExecutionState.FAILURE)

    def is_pushed(self) -> bool:
        return self.get("Push").state == ExecutionState.SUCCESS
