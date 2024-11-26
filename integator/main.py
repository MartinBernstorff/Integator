import pathlib
import subprocess
import sys
import time

import typer
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from integator.git import Git
from integator.monitor_impl import monitor_impl
from integator.settings import FILE_NAME, RootSettings, settings_file_exists
from integator.shell import Shell


class CodeChangeHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith(".py"):  # type: ignore
            print("Code changed, restarting...")
            # Restart the current script
            subprocess.call([sys.executable] + sys.argv)
            sys.exit()


app = typer.Typer()

# TODO: Add monitoring command which runs a verify script


@app.command()
def init():
    settings = RootSettings()

    if not settings_file_exists():
        settings.write_toml(pathlib.Path.cwd() / FILE_NAME)

    print("Settings file created")


@app.command()
def monitor():
    while True:
        shell = Shell()
        shell.clear()

        monitor_impl(
            shell,
            git=Git(),
        )

        time.sleep(1)


@app.command()
def log():
    # Set up watchdog observer
    observer = Observer()
    settings = RootSettings()
    # observer.schedule(
    #     CodeChangeHandler(), path=str(settings.integator.source_dir), recursive=True
    # )
    # observer.start()

    try:
        git = Git()
        shell = Shell()
        while True:
            settings = RootSettings()
            log_items = git.get_log(n_statuses=len(settings.integator.commands))
            shell.clear()

            for item in log_items:
                print(item.__repr__())
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == "__main__":
    monitor()
    # log()
    # app()
