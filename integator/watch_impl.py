import datetime
import enum
import logging

from iterpy import Arr

from integator.commit import Commit
from integator.git import Git, SourceGit
from integator.run_task import run_task
from integator.settings import RootSettings
from integator.shell import Shell
from integator.task_status import (
    ExecutionState,
    Span,
    Statuses,
    Task,
    TaskStatus,
)
from integator.task_status_repo import TaskStatusRepo

l = logging.getLogger(__name__)  # noqa: E741


class CommandRan(enum.Enum):
    YES = enum.auto()
    NO = enum.auto()


def watch_impl(
    shell: Shell, source_git: Git, status_repo: TaskStatusRepo, quiet: bool
) -> CommandRan:
    # Starting setup
    l.debug("Getting settings")
    settings = RootSettings()

    l.debug("Updating")
    latest = source_git.log.latest()
    latest_statuses = status_repo.get(latest.hash)
    if settings.integator.fail_fast and latest_statuses.has_failed():
        l.info(f"Latest commit {latest.hash} failed")
        for failure in latest_statuses.get_failures():
            l.warning(f"{failure.task.name} failed. Logs: '{failure.log}'")
        return CommandRan.NO

    l.debug("Diffing againt trunk")
    if (
        not source_git.diff_against(settings.integator.trunk)
        and settings.integator.skip_if_no_diff_against_trunk
    ):
        l.info(
            f"{latest}: No changes compared to trunk at {settings.integator.trunk}, waiting"
        )

        return CommandRan.NO

    command_ran = CommandRan.NO
    # Run commands
    for task in settings.integator.steps:
        log = logging.getLogger(f"{__name__}.{task.name}")
        log.debug(f"Processing {task.name}")
        latest_cmd_status = latest_statuses.get(task.name).state
        log.debug(f"Latest status: {latest_cmd_status}")

        match latest_cmd_status:
            case ExecutionState.SUCCESS:
                log.info(f"{task.name} succeeded on the last run, continuing")
                continue
            case ExecutionState.FAILURE:
                log.info(f"{task.name} failed on the last run, continuing")
                continue
            case ExecutionState.IN_PROGRESS:
                log.info(f"{task.name} crashed while running, executing again")
            case ExecutionState.UNKNOWN:
                log.info(f"{task.name} has not been run yet, executing")

        log_file = (
            settings.integator.log_dir
            / f"{datetime.datetime.now().strftime('%y%m%d%H%M%S')}-{latest.hash[0:4]}-{task.name.replace(' ', '-')}.log"
        )
        log_file.parent.mkdir(parents=True, exist_ok=True)

        commits = source_git.log.get(20)
        if _is_stale(
            [(commit, status_repo.get(commit.hash)) for commit in commits],
            task.max_staleness_seconds,
            task.name,
        ):
            result = run_task(
                task, latest.hash, SourceGit(source_git), status_repo, log_file, quiet
            )
            command_ran = CommandRan.YES
            if settings.integator.fail_fast and result.failed():
                break

    latest = source_git.log.latest()
    latest_statuses = status_repo.get(latest.hash)

    if latest_statuses.all(set(settings.task_names()), ExecutionState.SUCCESS):
        if settings.integator.push_on_success and not latest_statuses.is_pushed():
            l.debug("Pushing!")
            source_git.push_head()
            latest_statuses.replace(
                TaskStatus(
                    task=Task(name="Push", cmd="Push"),
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
