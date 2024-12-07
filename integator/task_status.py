import datetime as dt
import pathlib
from enum import Enum, auto

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


class TaskStatus(BaseModel):
    task: Task
    state: ExecutionState
    span: tuple[dt.datetime, dt.datetime]
    log: pathlib.Path | None

    @classmethod
    def unknown(cls, task: Task) -> "TaskStatus":
        return cls(
            task=task,
            state=ExecutionState.UNKNOWN,
            span=(dt.datetime.now(), dt.datetime.now()),
            log=None,
        )


class Statuses(BaseModel):
    values: list[TaskStatus] = Field(default_factory=list)

    def __str__(self):
        return f"[{''.join(str(status.state) for status in self.values)}]"

    @classmethod
    def from_str(cls: type["Statuses"], line: str) -> "Statuses":
        return cls.model_validate_json(line)

    def names(self) -> set[str]:
        return {status.task.name for status in self.values}

    def get(self, name: str) -> TaskStatus:
        matching = [task for task in self.values if task.task.name == name]

        if len(matching) == 0:
            new_status = TaskStatus(
                task=Task(name=name, cmd=str("UNKNOWN")),
                state=ExecutionState.UNKNOWN,
                span=(dt.datetime.now(), dt.datetime.now()),
                log=None,
            )
            self.add(new_status)
            return new_status

        return matching[0]

    def add(self, task_status: TaskStatus):
        self.values.append(task_status)

    def contains(self, status: ExecutionState) -> bool:
        return any(task.state == status for task in self.values)

    def all(self, compare: ExecutionState) -> bool:
        return all(task.state == compare for task in self.values)

    def get_failures(self) -> list[TaskStatus]:
        return [task for task in self.values if task.state == ExecutionState.FAILURE]

    def has_failed(self) -> bool:
        return self.contains(ExecutionState.FAILURE)

    def is_pushed(self) -> bool:
        return self.get(str("Push")).state == ExecutionState.SUCCESS
