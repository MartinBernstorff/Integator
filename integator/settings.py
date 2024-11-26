import json
import pathlib
from typing import Tuple, Type

import pydantic
import pydantic_settings
import toml
from pydantic import Field

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


class Command(pydantic.BaseModel):
    name: str
    cmd: str
    max_staleness_seconds: int


def default_command() -> list[Command]:
    return [
        Command(
            name="Command 1",
            cmd="echo 'test 1'",
            max_staleness_seconds=10,
        ),
        Command(
            name="Command 2",
            cmd="echo 'test 2'",
            max_staleness_seconds=10,
        ),
    ]


class IntegatorSettings(pydantic.BaseModel):
    command_on_success: str = Field(default="echo 'Success!'")
    fail_fast: bool = Field(default=True)
    push_on_success: bool = Field(default=False)
    commands: list[Command] = Field(default_factory=default_command)
    log_dir: pathlib.Path = Field(default=pathlib.Path.cwd() / ".logs")
    source_dir: pathlib.Path = Field(default=pathlib.Path.cwd())


class RootSettings(Settings):
    integator: IntegatorSettings = IntegatorSettings()

    def write_toml(self, path: pathlib.Path):
        values = json.loads(self.model_dump_json())
        toml.dump(values, open(path, "w"))


def settings_file_exists() -> bool:
    for dir in pathlib.Path.cwd().parents:
        if (dir / FILE_NAME).exists():
            return True
    return False
