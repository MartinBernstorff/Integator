import datetime
import enum
import logging
import pathlib

from iterpy import Arr

from integator.git import Commit, Git, Log
from integator.settings import RootSettings
from integator.shell import Shell
from integator.task_status import (
    ExecutionState,
    Statuses,
    Task,
    TaskStatus,
)
from integator.task_status_repo import TaskStatusRepo

l = logging.getLogger(__name__)


class CommandRan(enum.Enum):
    YES = enum.auto()
    NO = enum.auto()


def monitor_impl(shell: Shell, git: Git, status_repo: TaskStatusRepo) -> CommandRan:
    # Starting setup
    l.debug("Getting settings")
    settings = RootSettings()

    l.debug("Checking out latest commit")
    if pathlib.Path.cwd() != settings.integator.source_dir:
        git.checkout_head()

    l.debug("Updating")
    latest = git.log.latest()
    latest_statuses = status_repo.get(latest.hash)
    if settings.integator.fail_fast and latest_statuses.has_failed():
        print(f"Latest commit {latest.hash} failed")
        for failure in latest_statuses.get_failures():
            print(f"{failure.task.name} failed. Logs: '{failure.log}'")
        return CommandRan.NO

    l.debug("Diffing againt trunk")
    if not git.diff_against(settings.integator.trunk):
        print(
            f"{latest}: No changes compared to trunk at {settings.integator.trunk}, waiting"
        )

        return CommandRan.NO

    command_ran = CommandRan.NO
    # Run commands
    for cmd in settings.integator.commands:
        l.debug(f"Processing {cmd.name}")
        latest_cmd_status = latest_statuses.get(cmd.name).state
        l.debug(f"Latest status: {latest_cmd_status}")

        match latest_cmd_status:
            case ExecutionState.SUCCESS:
                print(f"{cmd.name} succeeded on the last run, continuing")
                continue
            case ExecutionState.FAILURE:
                print(f"{cmd.name} failed on the last run, continuing")
                continue
            case ExecutionState.IN_PROGRESS:
                print(f"{cmd.name} crashed while running, executing again")
            case ExecutionState.UNKNOWN:
                print(f"{cmd.name} has not been run yet, executing")

        now = datetime.datetime.now()
        current_date = now.strftime("%Y-%m-%d")
        output_file = (
            settings.integator.log_dir
            / current_date
            / cmd.name.replace(" ", "-")
            / f"{now.strftime('%H-%M-%S')}-{latest.hash}-{cmd.name.replace(' ', '-')}.log"
        )
        output_file.parent.mkdir(parents=True, exist_ok=True)

        commits = git.log.get()
        if _is_stale(
            [(commit, status_repo.get(commit.hash)) for commit in commits],
            cmd.max_staleness_seconds,
            cmd.name,
        ):
            print(f"Running {cmd.name}")
            latest_statuses.get(cmd.name).state = ExecutionState.IN_PROGRESS
            status_repo.update(latest.hash, latest_statuses)

            result = shell.run(
                cmd.cmd,
                output_file=output_file,
            )

            latest_statuses.get(cmd.name).state = ExecutionState.from_exit_code(
                result.exit
            )

            latest_statuses.get(cmd.name).log = output_file
            status_repo.update(latest.hash, latest_statuses)

            command_ran = CommandRan.YES
            if settings.integator.fail_fast:
                break
        l.debug(f"Finished checking for {cmd.name}")

    latest = git.log.latest()
    latest_statuses = status_repo.get(latest.hash)

    if latest_statuses.all(ExecutionState.SUCCESS):
        if settings.integator.push_on_success and not latest_statuses.is_pushed():
            l.debug("Pushing!")
            git.push_head()
            latest_statuses.add(
                TaskStatus(
                    task=Task(name=str("Push"), cmd=str("Push")),
                    state=ExecutionState.SUCCESS,
                    span=(datetime.datetime.now(), datetime.datetime.now()),
                    log=None,
                )
            )
            status_repo.update(latest.hash, latest_statuses)

        if settings.integator.command_on_success:
            shell.run_interactively(settings.integator.command_on_success)

    l.info("Finished monitoring")
    # shell.clear()

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
        datetime.datetime.now() - successes[0].span[1]
        if successes
        else datetime.timedelta(days=30)
    )

    max_staleness = datetime.timedelta(seconds=max_staleness_seconds)
    if time_since_success >= max_staleness:
        return True

    return False


if __name__ == "__main__":
    monitor_impl(
        Shell(), Git(source_dir=pathlib.Path.cwd(), log=Log({"None"})), TaskStatusRepo()
    )
