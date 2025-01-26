import importlib
import importlib.metadata
import json
import pathlib
from typing import Tuple, Type

import pydantic_settings
import toml
from pydantic import DirectoryPath, Field, field_validator

from integator.basemodel import BaseModel

FILE_NAME = "integator.toml"


class Settings(pydantic_settings.BaseSettings):
    model_config = pydantic_settings.SettingsConfigDict(
        toml_file=FILE_NAME, pyproject_toml_depth=100
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[pydantic_settings.BaseSettings],
        init_settings: pydantic_settings.PydanticBaseSettingsSource,
        env_settings: pydantic_settings.PydanticBaseSettingsSource,
        dotenv_settings: pydantic_settings.PydanticBaseSettingsSource,
        file_secret_settings: pydantic_settings.PydanticBaseSettingsSource,
    ) -> Tuple[pydantic_settings.PydanticBaseSettingsSource, ...]:
        return (pydantic_settings.TomlConfigSettingsSource(settings_cls),)


class StepSpec(BaseModel):
    """A specification of a step that is run during validation of a given commit."""

    # These steps are run in sequence by default.
    #
    # refactor: We might also want this naming to align as closely as possible with other CI/CD tools, e.g. GitHub Actions or Azure Pipelines.
    # In GitHub actions:
    # * Workflow; a collection of (jobs?)
    # * Job; a collection of (steps?)
    # * Step; a single operation, e.g. `git clone`

    name: str
    cmd: str
    # feat: templating/placeholders of commands. Allows us to standardise all operations, e.g. `git push` if we can replace e.g. {hash} with the latest hash.
    # Probably want this to be filled in as early as possible during program execution, to validate that it works.
    # feat: as an example, there is also "approving" a commit in GitHub actions.

    max_staleness_seconds: int = 0


def default_command() -> list[StepSpec]:
    return [
        StepSpec(
            name=str("Command 1"),
            cmd=str("echo 'test 1'"),
            max_staleness_seconds=10,
        ),
        StepSpec(
            name=" X",
            cmd="! rg -g '!integator.toml' XXX .",
            max_staleness_seconds=0,
        ),
    ]


class IntegatorSettings(BaseModel):
    # refactor: We definitely want to clean this up. Much of the experimental
    # logging and complexity functionality could be removed.

    # feat: !!! we need to error if a settings file exists, but it is not parsed correctly

    steps: list[StepSpec] = Field(default_factory=default_command)
    command_on_success: str = Field(default="")
    complexity_threshold: int = Field(default=5)
    complexity_changes_per_block: int = Field(default=10)
    complexity_bar_max: int = Field(default=100)
    fail_fast: bool = Field(default=True)
    push_on_success: bool = Field(default=False)
    source_dir: DirectoryPath = Field(default=pathlib.Path.cwd())
    skip_if_no_diff_against_trunk: bool = Field(default=False)

    # feat: Would be _awesome_ if we can specify default settings in ~/.config/integator/templates/X.toml
    # Make it an argument (e.g. --template) for many of the commands

    # feat: infer trunk from github CLI? Or at least allow it to be so, e.g. by specifying a command (prefix with $?)
    trunk: str = Field(default="main")

    # feat: add pyproject.toml support. Should be super easy, given docs here: https://docs.pydantic.dev/latest/concepts/pydantic_settings/#other-settings-source

    @classmethod
    @field_validator("source_dir")
    def validate_log_dir(cls, v: pathlib.Path) -> pathlib.Path:
        if not v.parent.exists():
            raise ValueError(f"integator.log_dir does not exist: {v.parent}")
        v.mkdir(parents=True, exist_ok=True)
        return v

    @property
    def log_dir(self) -> pathlib.Path:
        return self.source_dir / ".logs"


class RootSettings(Settings):
    # refactor: is this composition essential? I think it might be based on pydantic-settings, but worth investigating.
    # Could remove a layer of indirection.
    integator: IntegatorSettings = IntegatorSettings()

    # XXX: Log some info when init'ing here

    def write_toml(self, path: pathlib.Path):
        values = json.loads(self.model_dump_json())
        toml.dump(values, open(path, "w"))

    def step_names(self) -> list[str]:
        return [cmd.name for cmd in self.integator.steps]

    def get_step(self, name: str) -> StepSpec:
        for step in self.integator.steps:
            if step.name == name:
                return step
        raise ValueError(f"No step with name {name}")

    def version(self) -> str:
        return importlib.metadata.version("integator")


def find_settings_file() -> pathlib.Path | None:
    paths = list(pathlib.Path.cwd().parents) + [pathlib.Path.cwd()]

    for d in paths:
        if (d / FILE_NAME).exists():
            return d / FILE_NAME
    return None
