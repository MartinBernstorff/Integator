import datetime

from integator.git import Git
from integator.log_entry import LogEntry
from integator.settings import RootSettings
from integator.shell import ExitCode, Shell


def monitor_impl(shell: Shell, git: Git):
    settings = RootSettings()

    git.checkout_latest_commit(settings.integator.source_dir)

    commands = list(enumerate(settings.integator.commands))
    n_statuses = len(commands)
    entries = git.get_log(n_statuses=n_statuses)

    latest_entry = entries[0]

    # Update with the unknown state
    git.update_notes(latest_entry.note())
    if latest_entry.has_failed():
        print(f"Latest commit {latest_entry.hash} failed: {latest_entry.statuses}")
        return

    # Run commands
    for position, cmd in commands:
        now = datetime.datetime.now()
        current_time = now.strftime("%H:%M:%S")
        current_date = now.strftime("%Y-%m-%d")
        output_file = (
            settings.integator.log_dir
            / current_date
            / cmd.name
            / f"{current_time}-{cmd.name}.log"
        )
        output_file.parent.mkdir(parents=True, exist_ok=True)

        if _is_stale(entries, cmd.max_staleness_seconds, position):
            print(f"Running {cmd.name}")
            result = shell.run(
                cmd.cmd,
                output_file=output_file,
            )

            match result.exit_code:
                case ExitCode.OK:
                    latest_entry.set_ok(position)
                case ExitCode.ERROR:
                    latest_entry.set_failed(position)

            git.update_notes(latest_entry.note())

    print(f"{current_time} ({latest_entry.hash}) [{latest_entry.statuses}]")
    shell.clear()


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
    if time_since_success > max_staleness:
        return True

    return False
