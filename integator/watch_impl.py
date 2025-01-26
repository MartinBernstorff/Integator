import datetime
import enum
import logging

from iterpy import Arr

from integator.commit import Commit
from integator.git import Git, RootWorktree
from integator.run_step import run_step
from integator.settings import RootSettings
from integator.shell import Shell
from integator.step_status import (
    ExecutionState,
    Span,
    Statuses,
    StepStatus,
    Task,
)
from integator.step_status_repo import StepStatusRepo

l = logging.getLogger(__name__)  # noqa: E741


class CommandRan(enum.Enum):
    YES = enum.auto()
    NO = enum.auto()


def watch_impl(
    shell: Shell, root_git: Git, status_repo: StepStatusRepo, quiet: bool
) -> CommandRan:
    # Starting setup
    l.debug("Getting settings")
    settings = RootSettings()

    l.debug("Updating")
    latest = root_git.log.latest()
    latest_statuses = status_repo.get(latest.hash)
    if settings.integator.fail_fast and latest_statuses.has_failed():
        l.info(f"Latest commit {latest.hash} failed")
        for failure in latest_statuses.get_failures():
            l.warning(f"{failure.step.name} failed. Logs: '{failure.log}'")
        return CommandRan.NO

    l.debug("Diffing againt trunk")
    if (
        not root_git.diff_against(settings.integator.trunk)
        and settings.integator.skip_if_no_diff_against_trunk
    ):
        l.info(
            f"{latest}: No changes compared to trunk at {settings.integator.trunk}, waiting"
        )

        return CommandRan.NO

    command_ran = CommandRan.NO
    # Run commands
    for step in settings.integator.steps:
        log = logging.getLogger(f"{__name__}.{step.name}")
        log.debug(f"Processing {step.name}")
        latest_cmd_status = latest_statuses.get(step.name).state
        log.debug(f"Latest status: {latest_cmd_status}")

        match latest_cmd_status:
            case ExecutionState.SUCCESS:
                log.info(f"{step.name} succeeded on the last run, continuing")
                continue
            case ExecutionState.FAILURE:
                log.info(f"{step.name} failed on the last run, continuing")
                continue
            case ExecutionState.IN_PROGRESS:
                log.info(f"{step.name} crashed while running, executing again")
            case ExecutionState.UNKNOWN:
                log.info(f"{step.name} has not been run yet, executing")

        commits = root_git.log.get(20)
        if _is_stale(
            [(commit, status_repo.get(commit.hash)) for commit in commits],
            step.max_staleness_seconds,
            step.name,
        ):
            result = run_step(
                step,
                latest,
                RootWorktree(root_git),
                status_repo,
                settings.integator.log_dir,
                quiet,
            )
            command_ran = CommandRan.YES
            if settings.integator.fail_fast and result.failed():
                break

    latest = root_git.log.latest()
    latest_statuses = status_repo.get(latest.hash)

    if latest_statuses.all(set(settings.step_names()), ExecutionState.SUCCESS):
        if settings.integator.push_on_success and not latest_statuses.is_pushed():
            l.debug("Pushing!")
            root_git.push_head()
            latest_statuses.replace(
                StepStatus(
                    step=Task(name="Push", cmd="Push"),
                    state=ExecutionState.SUCCESS,
                    span=Span(
                        start=datetime.datetime.now(), end=datetime.datetime.now()
                    ),
                    log=None,
                )
            )
            status_repo.update(latest.hash, latest_statuses)

        if settings.integator.command_on_success:
            shell.run_interactively(settings.integator.command_on_success)

    l.info("Finished watching")

    return command_ran


def _is_stale(
    entries: list[tuple[Commit, Statuses]],
    max_staleness_seconds: int,
    cmd_name: str,
) -> bool:
    successes = (
        Arr(entries)
        .map(lambda it: it[1].get(cmd_name))
        .filter(lambda it: it.state == ExecutionState.SUCCESS)
        .to_list()
    )

    time_since_success = (
        datetime.datetime.now() - successes[0].span.start
        if successes
        else datetime.timedelta(days=30)
    )

    max_staleness = datetime.timedelta(seconds=max_staleness_seconds)
    if time_since_success >= max_staleness:
        return True

    return False
