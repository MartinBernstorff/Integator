import pathlib
import subprocess
import sys
import time
from contextlib import contextmanager

import typer
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from integator.git import Git, Log
from integator.monitor_impl import CommandRan, monitor_impl
from integator.settings import FILE_NAME, RootSettings, settings_file_exists
from integator.shell import Shell


class CodeChangeHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith(".py"):  # type: ignore
            print("Code changed, restarting...")
            # Restart the current script
            subprocess.call([sys.executable] + sys.argv)
            sys.exit()


@contextmanager
def watch_directory(
    path: pathlib.Path, handler: FileSystemEventHandler, recursive: bool = True
):
    observer = Observer()
    observer.schedule(handler, path=str(path), recursive=recursive)
    observer.start()

    try:
        yield observer
    finally:
        observer.stop()
        observer.join()


app = typer.Typer()

# TODO: Add monitoring command which runs a verify script


@app.command("i")
@app.command()
def init():
    settings = RootSettings()

    if not settings_file_exists():
        settings.write_toml(pathlib.Path.cwd() / FILE_NAME)

    print("Settings file created")


@app.command("m")
@app.command()
def monitor():
    settings = RootSettings()

    shell = Shell()
    while True:
        shell.clear()

        status = monitor_impl(
            shell,
            git=Git(
                source_dir=settings.integator.source_dir,
                log=Log(n_statuses=len(settings.integator.commands)),
            ),
        )

        if status == CommandRan.YES:
            time.sleep(1)


@app.command("l")
@app.command()
def log():
    # Set up watchdog observer
    settings = RootSettings()

    git = Git(
        source_dir=settings.integator.source_dir,
        log=Log(n_statuses=len(settings.integator.commands)),
    )
    shell = Shell()

    while True:
        settings = RootSettings()
        log_items = git.get_log(n_statuses=len(settings.integator.commands))
        shell.clear()

        for item in log_items:
            print(item.__repr__())

        time.sleep(1)


if __name__ == "__main__":
    monitor()
    # log()
    # app()
