from time import sleep

import typer

from git import Git

app = typer.Typer()


@app.command()
def log():
    while True:
        Git.impl().log()
        sleep(1)


if __name__ == "__main__":
    app()
