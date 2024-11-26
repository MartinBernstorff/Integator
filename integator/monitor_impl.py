import datetime
import time

from integator.config import RootSettings
from integator.git import Git
from integator.log_entry import LogEntry
from integator.shell import Shell


def monitor_impl(shell: Shell, git: Git):
    while True:
        settings = RootSettings()
        commands = list(enumerate(settings.integator.commands))
        n_statuses = len(commands)

        entries = git.get_log(n_statuses=n_statuses)
        latest_entry = entries[-1]

        for position, cmd in commands:
            if _is_stale(entries, cmd.max_staleness_seconds, position):
                print(f"Running {cmd.name}")
                try:
                    shell.run(cmd.cmd)
                    latest_entry.set_ok(position)
                except Exception as e:
                    latest_entry.set_failed(position)
                    print(f"Command {cmd.name} failed: {e}")
                git.update_notes(latest_entry.note())
            else:
                print(f"{cmd.name} is up to date")
        print(datetime.datetime.now().strftime("%H:%M:%S"))
        time.sleep(1)
        # Print time
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
