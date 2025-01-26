import datetime
import logging
import tempfile
from pathlib import Path

from integator.git import SourceGit
from integator.settings import StepSpec
from integator.shell import RunResult, Shell, Stream
from integator.step_status import ExecutionState, Span
from integator.step_status_repo import StepStatusRepo


def run_step(
    step: StepSpec,
    hash: str,
    source: SourceGit,
    status_repo: StepStatusRepo,
    output_file: Path,
    quiet: bool,
) -> RunResult:
    log = logging.getLogger(f"{__name__}.{step.name}")

    # Create the directory
    statuses = status_repo.get(hash)
    start_time = datetime.datetime.now()

    statuses.get(step.name).state = ExecutionState.IN_PROGRESS
    statuses.get(step.name).span = Span(start=start_time, end=None)
    statuses.get(step.name).log = output_file
    status_repo.update(hash, statuses)

    step_dir = Path(tempfile.gettempdir()) / f"integator-{hash}"
    worktree = source.init_worktree(step_dir, hash)

    log.info(f"Running {step.name} in {worktree}")
    result = Shell().run(
        step.cmd,
        output_file=output_file,
        cwd=worktree,
        stream=Stream.NO if quiet else Stream.YES,
    )

    statuses.get(step.name).state = ExecutionState.from_exit_code(result.exit)
    statuses.get(step.name).span = Span(start=start_time, end=datetime.datetime.now())
    statuses.get(step.name).log = output_file
    status_repo.update(hash, statuses)

    return result
