import datetime
import enum
import pathlib

from integator.git import Git
from integator.log_entry import LogEntry
from integator.settings import RootSettings
from integator.shell import ExitCode, RunResult, Shell


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
        for i in range(len(settings.integator.commands)):
            latest.set_ok(i)
            git.update_notes(latest.note())
        print(
            f"{latest.__repr__()}: No changes compared to trunk at {settings.integator.trunk}, marking as good and skipping"
        )
        return CommandRan.NO

    command_ran = CommandRan.NO
    # Run commands
    for status_position, cmd in enumerate(settings.integator.commands):
        if latest.is_failed(status_position):
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

        if _is_stale(git.log.get_all(), cmd.max_staleness_seconds, status_position):
            print(f"Running {cmd.name}")
            command_ran = CommandRan.YES
            result = shell.run(
                cmd.cmd,
                output_file=output_file,
            )

            update_status(git, latest, status_position, result)

            if settings.integator.fail_fast:
                break

    latest = git.log.latest()
    if latest.all_ok():
        if settings.integator.push_on_success and not latest.pushed:
            git.push()
            latest.pushed = True
            git.update_notes(latest.note())

        if settings.integator.command_on_success:
            shell.run_interactively(settings.integator.command_on_success)

    print(f"{now.strftime('%H:%M:%S')} {latest.__repr__()}")
    shell.clear()

    return command_ran


def update_status(git: Git, latest: LogEntry, position: int, result: RunResult):
    match result.exit_code:
        case ExitCode.OK:
            latest.set_ok(position)
        case ExitCode.ERROR:
            latest.set_failed(position)
    git.update_notes(latest.note())


def _is_stale(
    entries: list[LogEntry], max_staleness_seconds: int, position: int
) -> bool:
    if entries[0].is_ok(position):
        return False

    successes = [entry for entry in entries if entry.is_ok(position)]

    time_since_success = (
        successes[0].time_since if successes else datetime.timedelta(days=30)
    )

    max_staleness = datetime.timedelta(seconds=max_staleness_seconds)
    if time_since_success >= max_staleness:
        return True

    return False
