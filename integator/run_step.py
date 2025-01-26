import datetime
import logging
import tempfile
from pathlib import Path

from integator.commit import Commit
from integator.git import RootWorktree
from integator.settings import StepSpec
from integator.shell import RunResult, Shell, Stream
from integator.step_status import ExecutionState, Span
from integator.step_status_repo import StepStatusRepo


def run_step(
    step: StepSpec,
    commit: Commit,
    root_worktree: RootWorktree,
    status_repo: StepStatusRepo,
    output_dir: Path,
    quiet: bool,
) -> RunResult:
    # refactor: this is a lot of intermingled state, but unsure if it gives problems or if I should just let it be.
    log = logging.getLogger(f"{__name__}.{step.name}")
    log_file = (
        output_dir
        / f"{datetime.datetime.now().strftime('%y%m%d%H%M%S')}-{commit.hash[0:4]}-{step.name.replace(' ', '-')}.log"
    )
    log_file.parent.mkdir(parents=True, exist_ok=True)

    statuses = status_repo.get(commit.hash)
    start_time = datetime.datetime.now()

    # refactor: we could move "starting" and "finishing" a step into the status repo
    statuses.get(step.name).state = ExecutionState.IN_PROGRESS
    statuses.get(step.name).span = Span(start=start_time, end=None)
    statuses.get(step.name).log = log_file
    status_repo.update(commit.hash, statuses)

    step_dir = Path(tempfile.gettempdir()) / f"integator-{commit.hash}"
    worktree = root_worktree.init(step_dir, commit.hash)

    log.info(f"Running {step.name} in {worktree}")
    result = Shell().run(
        step.cmd,
        output_file=log_file,
        cwd=worktree,
        stream=Stream.NO if quiet else Stream.YES,
    )

    statuses.get(step.name).state = ExecutionState.from_exit_code(result.exit)
    statuses.get(step.name).span = Span(start=start_time, end=datetime.datetime.now())
    statuses.get(step.name).log = log_file
    status_repo.update(commit.hash, statuses)

    return result
