import datetime
import enum
import logging
import pathlib

from integator.git import Git
from integator.settings import RootSettings
from integator.shell import ExitCode, Shell
from integator.task_status import Commit, Statuses

l = logging.getLogger(__name__)


class CommandRan(enum.Enum):
    YES = enum.auto()
    NO = enum.auto()


def monitor_impl(shell: Shell, git: Git) -> CommandRan:
    l.debug("Getting settings")
    settings = RootSettings()

    l.debug("Checking out latest commit")
    if pathlib.Path.cwd() != settings.integator.source_dir:
        git.checkout_latest_commit()

    l.debug("Updating")
    latest = git.log.latest()
    if settings.integator.fail_fast and latest.has_failed():
        print(f"Latest commit {latest.hash} failed")
        for failure in latest.statuses.get_failures():
            print(f"{failure.task.name} failed. Logs: '{failure.log}'")
        return CommandRan.NO

    l.debug("Diffing againt trunk")
    if not git.diff_against(settings.integator.trunk):
        print(
            f"{latest}: No changes compared to trunk at {settings.integator.trunk}, waiting"
        )

        return CommandRan.NO

    command_ran = CommandRan.NO
    statuses = latest.statuses
    # Run commands
    for cmd in settings.integator.commands:
        l.debug(f"Checking status for {cmd.name}")
        if latest.is_failed(cmd.name):
            print(f"{cmd.name} failed on the last run, continuing")
            continue

        now = datetime.datetime.now()
        current_date = now.strftime("%Y-%m-%d")
        output_file = (
            settings.integator.log_dir
            / current_date
            / cmd.name.replace(" ", "-")
            / f"{now.strftime('%H-%M-%S')}-{latest.hash}-{cmd.name.replace(' ', '-')}.log"
        )
        output_file.parent.mkdir(parents=True, exist_ok=True)

        if _is_stale(git.log.get(), cmd.max_staleness_seconds, cmd.name):
            print(f"Running {cmd.name}")
            command_ran = CommandRan.YES
            result = shell.run(
                cmd.cmd,
                output_file=output_file,
            )

            match result.exit:
                case ExitCode.OK:
                    statuses.set_ok(cmd.name)
                case ExitCode.ERROR:
                    statuses.set_failed(cmd.name)

            statuses.get(cmd.name).log = output_file

            update_status(git, statuses)

            if settings.integator.fail_fast:
                break
        l.debug(f"Finished checking for {cmd.name}")

    latest = git.log.latest()
    if latest.all_ok():
        if settings.integator.push_on_success and not latest.is_pushed():
            l.debug("Pushing!")
            git.push()
            latest.statuses.create_ok("Push")
            update_status(git, latest.statuses)

        if settings.integator.command_on_success:
            shell.run_interactively(settings.integator.command_on_success)

    l.info("Finished monitoring")
    # shell.clear()

    return command_ran


def update_status(git: Git, statuses: Statuses):
    git.update_notes(statuses.model_dump_json())


def _is_stale(entries: list[Commit], max_staleness_seconds: int, cmd_name: str) -> bool:
    if entries[0].is_ok(cmd_name):
        return False

    successes = [entry for entry in entries if entry.is_ok(cmd_name)]

    time_since_success = (
        datetime.datetime.now() - successes[0].timestamp
        if successes
        else datetime.timedelta(days=30)
    )

    max_staleness = datetime.timedelta(seconds=max_staleness_seconds)
    if time_since_success >= max_staleness:
        return True

    return False
