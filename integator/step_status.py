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


class StepStatus(BaseModel):
    step: Task
    state: ExecutionState
    span: Span
    log: pathlib.Path | None

    @classmethod
    def unknown(cls, step: Task) -> "StepStatus":
        return cls(
            step=step,
            state=ExecutionState.UNKNOWN,
            span=Span(start=dt.datetime.now(), end=None),
            log=None,
        )

    def __repr__(self) -> str:
        return f"{self.step.name}: {self.state}"

    def tail(self, n_lines: int) -> str:
        # feat: We could replace the paths mentioned in the printed logs (which point to the worktree) with the path to the
        # "origin directory", e.g. the directory where the code under test is copied from.
        # On the one hand, this means that we won't command-click our way into a file that is only in a temporary directory.
        # On the other hand, it means that the paths are not actually pointing towards the file that they are mentioning, so if
        #   we have something that is particular to the copied file, we are in trouble, and we have abstracted away that consideration
        #   from the user. Perhaps we can print both? Or in some way indicate that it is replaced?
        if self.log is None:
            return ""

        log_lines = self.log.read_text().split("\n")
        lines_in_log = len(log_lines)

        excess_lines = lines_in_log >= n_lines
        excerpted_lines = log_lines[-n_lines:] if excess_lines else log_lines
        return "\n".join(excerpted_lines)


class Statuses(BaseModel):
    values: list[StepStatus] = Field(default_factory=list)

    def __str__(self):
        return f"[{''.join(str(status.state) for status in self.values)}]"

    @classmethod
    def from_str(cls: type["Statuses"], line: str) -> "Statuses":
        return cls.model_validate_json(line)

    def names(self) -> set[str]:
        return {status.step.name for status in self.values}

    def remove(self, name: str):
        self.values = [status for status in self.values if status.step.name != name]

    def replace(self, new: StepStatus):
        self.values = [
            status for status in self.values if status.step.name != new.step.name
        ]
        self.add(new)

    def get(self, name: str) -> StepStatus:
        matching = [step for step in self.values if step.step.name == name]

        if len(matching) == 0:
            new_status = StepStatus(
                step=Task(name=name, cmd=str("UNKNOWN")),
                state=ExecutionState.UNKNOWN,
                span=Span(start=dt.datetime.now(), end=dt.datetime.now()),
                log=None,
            )
            self.add(new_status)
            return new_status

        return matching[0]

    def duration(self) -> dt.timedelta:
        return reduce(lambda x, y: x + y, [s.span.duration() for s in self.values])

    def add(self, step_status: StepStatus):
        self.values.append(step_status)

    def contains(self, status: ExecutionState) -> bool:
        return any(step.state == status for step in self.values)

    def all_succeeded(self, names: Set[str]) -> bool:
        return self.all(names, ExecutionState.SUCCESS)

    def all(self, names: Set[str], expected_state: ExecutionState) -> bool:
        for name in names:
            if not self.get(name).state == expected_state:
                return False
        return True

    def get_failures(self) -> list[StepStatus]:
        return [step for step in self.values if step.state == ExecutionState.FAILURE]

    def has_failed(self) -> bool:
        return self.contains(ExecutionState.FAILURE)

    def is_pushed(self) -> bool:
        return self.get("Push").state == ExecutionState.SUCCESS
