import datetime
import enum
import pathlib

from integator.git import Git
from integator.settings import RootSettings
from integator.shell import ExitCode, Shell
from integator.task_status import Commit, Statuses


class CommandRan(enum.Enum):
    YES = enum.auto()
    NO = enum.auto()


def monitor_impl(shell: Shell, git: Git) -> CommandRan:
    settings = RootSettings()

    if pathlib.Path.cwd() != settings.integator.source_dir:
        git.checkout_latest_commit()

    # Update with the unknown state
    latest = git.log.latest()
    if settings.integator.fail_fast and latest.has_failed():
        print(f"Latest commit {latest.hash} failed: {latest.statuses}")
        return CommandRan.NO

    if not git.diff_against(settings.integator.trunk):
        print(
            f"{latest}: No changes compared to trunk at {settings.integator.trunk}, marking as good and skipping"
        )
        return CommandRan.NO

    command_ran = CommandRan.NO
    statuses = latest.statuses
    # Run commands
    for cmd in settings.integator.commands:
        if latest.is_failed(cmd.name):
            print(f"{cmd.name} failed on the last run, continuing")
            continue

        now = datetime.datetime.now()
        current_date = now.strftime("%Y-%m-%d")
        output_file = (
            settings.integator.log_dir
            / current_date
            / cmd.name
            / f"{now.strftime('%H-%M-%S')}-{cmd.name}.log"
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

            update_status(git, statuses)

            if settings.integator.fail_fast:
                break

    latest = git.log.latest()
    if latest.all_ok():
        if settings.integator.push_on_success and not latest.pushed:
            git.push()
            latest.pushed = True

        if settings.integator.command_on_success:
            shell.run_interactively(settings.integator.command_on_success)

    print(f"{datetime.datetime.now().strftime('%H:%M:%S')} {latest.__repr__()}")
    shell.clear()

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
