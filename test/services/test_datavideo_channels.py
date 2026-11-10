from pathlib import Path
from unittest.mock import patch

import pytest

from app.datavideo.channels import CHANNELS_DIRECTORY, load_channel, load_channels, text_generator
from app.datavideo.locale import SPANISH_SPAIN
from app.datavideo.theme import DEFAULT_THEME

VALID_PROFILE = """
id = "tu_dinero_es"
name = "Tu Dinero en Datos"
language = "es-ES"

[models]
provider = "openai"
writer = "gpt-6.1-sol"
judge = "gpt-6.1-sol"

[voice]
name = "es-ES-TristanMultilingualNeural-V2-Male"

[theme]
positive = [0, 200, 100]

[publish]
user = "default"
platforms = ["youtube"]
privacy = "private"
"""


def write_profile(directory: Path, name: str, content: str) -> Path:
    path = directory / name
    path.write_text(content, encoding="utf-8")
    return path


def test_profile_is_loaded_with_its_language_models_and_voice(tmp_path):
    profile = load_channel(write_profile(tmp_path, "tu_dinero_es.toml", VALID_PROFILE))

    assert profile.id == "tu_dinero_es"
    assert profile.language == SPANISH_SPAIN
    assert profile.models.writer == "gpt-6.1-sol"
    assert profile.voice.name == "es-ES-TristanMultilingualNeural-V2-Male"
    assert profile.voice.rate == 1.0


def test_profile_without_a_voice_is_rejected(tmp_path):
    content = VALID_PROFILE.replace('[voice]\nname = "es-ES-TristanMultilingualNeural-V2-Male"', "")

    with pytest.raises(ValueError, match="voice"):
        load_channel(write_profile(tmp_path, "tu_dinero_es.toml", content))


def test_theme_overrides_only_the_colors_the_profile_sets(tmp_path):
    profile = load_channel(write_profile(tmp_path, "tu_dinero_es.toml", VALID_PROFILE))

    assert profile.theme.positive == (0, 200, 100)
    assert profile.theme.negative == DEFAULT_THEME.negative


def test_unknown_fields_are_rejected_to_catch_typos(tmp_path):
    content = VALID_PROFILE.replace('language = "es-ES"', 'language = "es-ES"\nlanguaje = "es-ES"')

    with pytest.raises(ValueError, match="languaje"):
        load_channel(write_profile(tmp_path, "tu_dinero_es.toml", content))


def test_unsupported_languages_are_rejected(tmp_path):
    content = VALID_PROFILE.replace('"es-ES"', '"fr-FR"')

    with pytest.raises(ValueError, match="language"):
        load_channel(write_profile(tmp_path, "tu_dinero_es.toml", content))


def test_file_name_must_match_the_channel_id(tmp_path):
    with pytest.raises(ValueError, match="file name"):
        load_channel(write_profile(tmp_path, "other.toml", VALID_PROFILE))


def test_all_profiles_in_a_directory_are_loaded_by_id(tmp_path):
    write_profile(tmp_path, "tu_dinero_es.toml", VALID_PROFILE)

    assert list(load_channels(tmp_path)) == ["tu_dinero_es"]


def test_repository_profiles_are_valid():
    profiles = load_channels(CHANNELS_DIRECTORY)

    assert "tu_dinero_es" in profiles


def test_text_generator_uses_the_role_model_and_the_api_key_from_the_environment(tmp_path, monkeypatch):
    profile = load_channel(write_profile(tmp_path, "tu_dinero_es.toml", VALID_PROFILE))
    monkeypatch.setenv("OPENAI_API_KEY", "fixture-key")

    with patch("app.services.llm._generate_response", return_value="{}") as generate:
        reply = text_generator(profile, "writer")("prompt")

    app_config = generate.call_args.kwargs["app_config"]
    assert reply == "{}"
    assert app_config["llm_provider"] == "openai"
    assert app_config["openai_model_name"] == "gpt-6.1-sol"
    assert app_config["openai_api_key"] == "fixture-key"


def test_text_generator_rejects_unknown_roles(tmp_path):
    profile = load_channel(write_profile(tmp_path, "tu_dinero_es.toml", VALID_PROFILE))

    with pytest.raises(ValueError, match="role"):
        text_generator(profile, "editor")


def test_repository_voices_resolve_to_an_azure_voice():
    from app.services.voice import is_azure_v2_voice

    for profile in load_channels(CHANNELS_DIRECTORY).values():
        assert is_azure_v2_voice(profile.voice.name).endswith("Neural"), profile.id


def test_publish_settings_and_stories_are_loaded(tmp_path):
    content = VALID_PROFILE.replace('language = "es-ES"', 'language = "es-ES"\nstories = ["ipc_anual_ccaa"]')

    profile = load_channel(write_profile(tmp_path, "tu_dinero_es.toml", content))

    assert profile.stories == ("ipc_anual_ccaa",)
    assert profile.publish.user == "default"
    assert profile.publish.platforms == ["youtube"]
    assert profile.publish.privacy == "private"


def test_publishing_defaults_to_one_video_a_day_at_noon_in_madrid(tmp_path):
    profile = load_channel(write_profile(tmp_path, "tu_dinero_es.toml", VALID_PROFILE))

    assert profile.publish.per_day == 1
    assert profile.publish.daily_at == "12:00"
    assert profile.publish.timezone == "Europe/Madrid"


@pytest.mark.parametrize(
    "field, value",
    [
        ("privacy", '"secret"'),
        ("platforms", '["facebook"]'),
        ("per_day", "0"),
        ("per_day", "4"),
        ("daily_at", '"25:00"'),
        ("timezone", '"Mars/Olympus"'),
    ],
)
def test_publish_settings_outside_the_allowed_values_are_rejected(tmp_path, field, value):
    line = {"privacy": 'privacy = "private"', "platforms": 'platforms = ["youtube"]'}.get(field, 'privacy = "private"')
    replacement = f"{field} = {value}" if field in ("privacy", "platforms") else f'{line}\n{field} = {value}'
    content = VALID_PROFILE.replace(line, replacement)

    with pytest.raises(ValueError, match=field):
        load_channel(write_profile(tmp_path, "tu_dinero_es.toml", content))


def test_a_profile_without_publish_settings_cannot_publish(tmp_path):
    content = VALID_PROFILE.split("[publish]")[0]

    profile = load_channel(write_profile(tmp_path, "tu_dinero_es.toml", content))

    assert profile.publish is None
