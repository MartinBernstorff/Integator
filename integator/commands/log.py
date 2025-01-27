import typer

from integator.log import log_impl
from integator.logging import init_log

log_app = typer.Typer()


@log_app.command("l")
@log_app.command()
def log(debug: bool = False, quiet: bool = False):
    # feat: I want the log to be super-simple, a one-time-run thing you can call to get the current status, e.g. in CI.
    # refactor: remove the log_impl layer
    init_log(debug, quiet)
    log_impl(debug)
