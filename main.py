import subprocess
import sys
import time

import typer
from watchdog.events import FileSystemEventHandler

from git import Git


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
def main():
    # Set up watchdog observer
    # observer = Observer()
    # observer.schedule(CodeChangeHandler(), path=".", recursive=False)
    # observer.start()

    # try:
    while True:
        Git.impl().log()
        time.sleep(1)


# except KeyboardInterrupt:
#     observer.stop()
# observer.join()


if __name__ == "__main__":
    app()
