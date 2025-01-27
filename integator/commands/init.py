import pathlib

import typer

from integator.commands.argument_parsing import get_settings, template_defaults
from integator.settings import FILE_NAME, find_settings_file

init_app = typer.Typer()


def update_gitignore(gitignore_path: pathlib.Path):
    if ".logs/" not in gitignore_path.read_text().strip():
        with open(gitignore_path, "a") as f:
            f.write("\n.logs/")
            print("Added .logs to .gitignore")


@init_app.command("i")
@init_app.command()
def init(template_name: str | None = template_defaults):
    settings = get_settings(template_name)

    # feat: add a selector here, to choose from existing files in ~/.config/integator/templates
    # Then we can have e.g. a Python.toml template, which can be used as a starting point.
    # Perhaps we want merging of the default with whichever settings are specified in the template?
    # This means we can
    destination_dir = find_settings_file()

    match destination_dir:
        case pathlib.Path():
            print(f"Settings file already exists at: {destination_dir}")
        case None:
            new_path = pathlib.Path.cwd() / FILE_NAME
            settings.write_toml(new_path)
            print(f"Settings file created at: {new_path}")

    gitignore_path = pathlib.Path.cwd() / ".gitignore"
    match gitignore_path.exists():
        case True:
            update_gitignore(gitignore_path)
        case False:
            pass
