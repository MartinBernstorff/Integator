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


class TaskSpecification(BaseModel):
    name: str
    cmd: str
    max_staleness_seconds: int = 0


def default_command() -> list[TaskSpecification]:
    return [
        TaskSpecification(
            name=str("Command 1"),
            cmd=str("echo 'test 1'"),
            max_staleness_seconds=10,
        ),
        TaskSpecification(
            name=str("Command 2"),
            cmd=str("echo 'test 2'"),
            max_staleness_seconds=10,
        ),
    ]


class IntegatorSettings(BaseModel):
    commands: list[TaskSpecification] = Field(default_factory=default_command)
    command_on_success: str = Field(default="")
    complexity_threshold: int = Field(default=5)
    complexity_changes_per_block: int = Field(default=10)
    complexity_bar_max: int = Field(default=100)
    fail_fast: bool = Field(default=True)
    push_on_success: bool = Field(default=False)
    source_dir: DirectoryPath = Field(default=pathlib.Path.cwd())
    skip_if_no_diff_against_trunk: bool = Field(default=False)
    trunk: str = Field(default="main")

    @classmethod
    @field_validator("source_dirs")
    def validate_log_dir(cls, v: pathlib.Path) -> pathlib.Path:
        if not v.parent.exists():
            raise ValueError(f"integator.log_dir does not exist: {v.parent}")
        v.mkdir(parents=True, exist_ok=True)
        return v

    @property
    def log_dir(self) -> pathlib.Path:
        return self.source_dir / ".logs"


class RootSettings(Settings):
    integator: IntegatorSettings = IntegatorSettings()

    def write_toml(self, path: pathlib.Path):
        values = json.loads(self.model_dump_json())
        toml.dump(values, open(path, "w"))

    def task_names(self) -> list[str]:
        return [cmd.name for cmd in self.integator.commands]


def settings_file_exists() -> bool:
    for d in pathlib.Path.cwd().parents:
        if (d / FILE_NAME).exists():
            return True
    return False
