from functools import partial
from multiprocessing import Process

import typer

from integator.commands.argument_parsing import template_defaults
from integator.commands.watch import watch
from integator.logging import init_log

tui_app = typer.Typer()


@tui_app.command("t")
@tui_app.command()
def tui(
    template_name: str | None = template_defaults,
    debug: bool = False,
    quiet: bool = True,
):
    init_log(debug, quiet)
    from integator.tui.main import IntegatorTUI

    side_process = Process(
        target=partial(watch, template_name=template_name, debug=debug, quiet=quiet),
        daemon=True,
    )
    side_process.start()

    app = IntegatorTUI()
    app.run()
