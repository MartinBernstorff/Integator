from dataclasses import dataclass
from functools import partial
from multiprocessing import Process
from typing import NoReturn

import typer

from integator.commands.argument_parsing import get_settings, template_defaults
from integator.commands.watch import watch
from integator.sys_logs import init_log

tui_app = typer.Typer()


@dataclass
class WatchDaemon:
    callable: partial[NoReturn]
    process: Process

    def __post_init__(self):
        self.process.start()

    def restart(self):
        if self.process.is_alive():
            self.process.terminate()
            self.process.join()

        self.process = Process(target=self.callable, daemon=True)
        self.process.start()


@tui_app.command("t")
@tui_app.command()
def tui(
    template_name: str | None = template_defaults,
    debug: bool = False,
    quiet: bool = True,
):
    init_log(debug, quiet)
    from integator.tui.main import IntegatorTUI

    watch_target = partial(watch, template_name=template_name, debug=debug, quiet=quiet)
    side_process = Process(target=watch_target, daemon=True)
    side_process.start()

    app = IntegatorTUI(
        settings=get_settings(template_name),
        watch_process=side_process,
        watch_target=watch_target,
    )
    app.run()
