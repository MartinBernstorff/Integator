import logging

import typer

from integator.commands.check import check_app
from integator.commands.init import init_app
from integator.commands.log import log_app
from integator.commands.run import run_app
from integator.commands.tui import tui_app
from integator.commands.watch import watch_app

logger = logging.getLogger(__name__)


app = typer.Typer()
app.add_typer(check_app)
app.add_typer(init_app)
app.add_typer(log_app)
app.add_typer(run_app)
app.add_typer(tui_app)
app.add_typer(watch_app)

# feat: A `clear` command, which removes all step states for a given commit. By default, removes for the latest commit.


if __name__ == "__main__":
    app()
