import os
import tomllib
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Callable, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from app.datavideo.locale import SUPPORTED_LOCALES
from app.datavideo.theme import DEFAULT_THEME, Color, Theme
from app.utils import utils

CHANNELS_DIRECTORY = Path(utils.root_dir()) / "channels"
MODEL_ROLES = ("writer", "judge")


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ModelRoles(_StrictModel):
    provider: str = "openai"
    writer: str
    judge: str


class VoiceSettings(_StrictModel):
    name: str = Field(min_length=1)
    rate: float = Field(default=1.0, gt=0)


class PublishSettings(_StrictModel):
    user: str = Field(pattern=r"^[A-Za-z0-9_@-]+$")
    platforms: list[Literal["youtube", "instagram"]] = Field(min_length=1)
    privacy: Literal["private", "unlisted", "public"]
    per_day: int = Field(default=1, ge=1, le=3)
    daily_at: str = Field(default="12:00", pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    timezone: str = "Europe/Madrid"

    @field_validator("timezone")
    @classmethod
    def _known_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as error:
            raise ValueError(f"unknown timezone: {value}") from error
        return value


class _ThemeOverrides(_StrictModel):
    background: Color | None = None
    neutral: Color | None = None
    positive: Color | None = None
    negative: Color | None = None
    text: Color | None = None
    muted: Color | None = None
    font_file: str | None = None


class _ProfilePayload(_StrictModel):
    id: str = Field(pattern=r"^[a-z0-9_]+$")
    name: str = Field(min_length=1)
    language: str
    stories: list[str] = []
    models: ModelRoles
    voice: VoiceSettings
    theme: _ThemeOverrides = _ThemeOverrides()
    publish: PublishSettings | None = None


@dataclass(frozen=True)
class ChannelProfile:
    id: str
    name: str
    language: str
    models: ModelRoles
    voice: VoiceSettings
    theme: Theme
    stories: tuple[str, ...] = ()
    publish: PublishSettings | None = None


def load_channel(path: Path) -> ChannelProfile:
    try:
        payload = _ProfilePayload.model_validate(tomllib.loads(path.read_text(encoding="utf-8")))
    except (tomllib.TOMLDecodeError, ValidationError) as error:
        raise ValueError(f"invalid channel profile {path.name}: {error}") from error
    if payload.language not in SUPPORTED_LOCALES:
        raise ValueError(f"invalid channel profile {path.name}: unsupported language {payload.language}")
    if path.stem != payload.id:
        raise ValueError(f"invalid channel profile {path.name}: file name must match id {payload.id}")
    return ChannelProfile(
        id=payload.id,
        name=payload.name,
        language=payload.language,
        models=payload.models,
        voice=payload.voice,
        theme=replace(DEFAULT_THEME, **payload.theme.model_dump(exclude_none=True)),
        stories=tuple(payload.stories),
        publish=payload.publish,
    )


def load_channels(directory: Path = CHANNELS_DIRECTORY) -> dict[str, ChannelProfile]:
    profiles = [load_channel(path) for path in sorted(directory.glob("*.toml"))]
    return {profile.id: profile for profile in profiles}


def text_generator(profile: ChannelProfile, role: str) -> Callable[[str], str]:
    if role not in MODEL_ROLES:
        raise ValueError(f"unknown model role: {role}")
    from app.config import config
    from app.services import llm

    provider = profile.models.provider
    app_config = {
        **config.app,
        "llm_provider": provider,
        f"{provider}_model_name": getattr(profile.models, role),
        f"{provider}_api_key": config.app.get(f"{provider}_api_key") or os.environ.get(f"{provider.upper()}_API_KEY", ""),
    }

    def generate(prompt: str) -> str:
        return llm._generate_response(prompt, app_config=app_config)

    return generate
