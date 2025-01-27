import pathlib

import typer

from integator.commit import Commit
from integator.git import Git
from integator.settings import RootSettings, StepSpec


def commit_match_or_latest(hash: str | None, git: Git) -> Commit:
    match hash:
        case str():
            commit = git.log.get_by_hash(hash)
        case None:
            commit = git.log.latest()
    return commit


def step_match_or_all(step: str | None, settings: RootSettings) -> list[StepSpec]:
    match step:
        case None:
            step_specs = settings.integator.steps
        case str():
            step_specs = [settings.get_step(step)]
    return step_specs


def get_settings(template_name: str | None) -> RootSettings:
    match template_name:
        case None:
            return RootSettings.from_toml(pathlib.Path("integator.toml"))
        case str():
            return RootSettings.from_template(template_name)


template_defaults = typer.Option(
    None,
    "-t",
    "--template",
    help="Template to use, found in $HOME/.config/integator/templates/[ARG]",
)
hash_defaults = typer.Option(None, "--hash", help="Commit hash to check")
step_defaults = typer.Option(None, "--step", help="Step to check")
