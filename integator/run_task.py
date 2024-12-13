import datetime
import logging
import tempfile
import uuid
from pathlib import Path

from integator.git import SourceGit
from integator.settings import TaskSpecification
from integator.shell import RunResult, Shell
from integator.task_status import ExecutionState, Span
from integator.task_status_repo import TaskStatusRepo


def run_in_worktree(
    task: TaskSpecification,
    hash: str,
    source: SourceGit,
    status_repo: TaskStatusRepo,
    output_file: Path,
) -> RunResult:
    log = logging.getLogger(f"{__name__}.{task.name}")
    # Create the directory
    statuses = status_repo.get(hash)
    start_time = datetime.datetime.now()

    statuses.get(task.name).state = ExecutionState.IN_PROGRESS
    statuses.get(task.name).span = Span(start=start_time, end=None)
    status_repo.update(hash, statuses)

    task_dir = (
        Path(tempfile.gettempdir()) / f"integator-{uuid.uuid4()}-{hash}-{task.name}"
    )
    worktree = source.init_worktree(task_dir, hash)

    log.debug(f"Running {task.name} in {worktree}")
    result = Shell().run(
        task.cmd,
        output_file=output_file,
        cwd=worktree,
    )

    statuses.get(task.name).state = ExecutionState.from_exit_code(result.exit)
    statuses.get(task.name).span = Span(start=start_time, end=datetime.datetime.now())
    statuses.get(task.name).log = output_file
    status_repo.update(hash, statuses)

    return result
