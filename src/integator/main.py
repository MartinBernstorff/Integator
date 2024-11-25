import pathlib
import subprocess
import sys
import time

import typer
from watchdog.events import FileSystemEventHandler

from integator.monitor_impl import monitor_impl

from .config import FILE_NAME, RootSettings, settings_file_exists
from .git import Git


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
    monitor_impl()

@app.command()
def log():
    # Set up watchdog observer
    # observer = Observer()
    # observer.schedule(CodeChangeHandler(), path=".", recursive=False)
    # observer.start()

    while True:
        git = Git.impl()
        log_items = git.log()
        git.print_log(log_items)
        time.sleep(1)

    # except KeyboardInterrupt:
    #     observer.stop()
    # observer.join()


if __name__ == "__main__":
    app()
