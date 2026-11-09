import pytest
import requests

from app.datavideo.channels import PublishSettings
from app.datavideo.notify import send_alert
from app.datavideo.packaging import Package
from app.datavideo.publish import publish_video

PACKAGE = Package(title="Galicia lidera la inflación", description="Narración.\n\nFuente: INE.", tags=("inflación", "IPC"))
TARGET = PublishSettings(user="default", platforms=["youtube"], privacy="private")


def test_video_is_sent_with_its_youtube_title_description_tags_and_privacy(tmp_path, monkeypatch):
    calls = {}
    monkeypatch.setenv("UPLOAD_POST_API_KEY", "fixture-key")

    def fake_cross_post(**kwargs):
        calls.update(kwargs)
        return {"success": True, "request_id": "abc"}

    result = publish_video(tmp_path / "final.mp4", PACKAGE, TARGET, cross_post=fake_cross_post)

    extra = calls["youtube_extra"]
    assert result["success"] is True
    assert calls["platforms"] == ["youtube"]
    assert extra["youtube_title"] == PACKAGE.title
    assert extra["youtube_description"] == PACKAGE.description
    assert extra["tags"] == ["inflación", "IPC"]
    assert extra["privacyStatus"] == "private"
    assert extra["selfDeclaredMadeForKids"] is False


def test_the_caption_for_other_networks_is_the_description(tmp_path, monkeypatch):
    calls = {}
    monkeypatch.setenv("UPLOAD_POST_API_KEY", "fixture-key")

    publish_video(tmp_path / "final.mp4", PACKAGE, TARGET, cross_post=lambda **kwargs: calls.update(kwargs) or {})

    assert calls["title"] == PACKAGE.description


def test_the_upload_account_comes_from_the_environment_and_the_profile_user(tmp_path, monkeypatch):
    calls = {}
    monkeypatch.setenv("UPLOAD_POST_API_KEY", "fixture-key")

    publish_video(tmp_path / "final.mp4", PACKAGE, TARGET, cross_post=lambda **kwargs: calls.update(kwargs) or {})

    assert calls["account"] == {
        "upload_post_api_key": "fixture-key",
        "upload_post_username": "default",
        "upload_post_enabled": True,
    }


def test_publishing_without_an_api_key_fails_before_uploading(tmp_path, monkeypatch):
    monkeypatch.delenv("UPLOAD_POST_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="UPLOAD_POST_API_KEY"):
        publish_video(tmp_path / "final.mp4", PACKAGE, TARGET, cross_post=lambda **kwargs: pytest.fail("uploaded"))


def test_alert_is_sent_to_the_owner_chat(monkeypatch):
    calls = {}
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fixture-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "42")

    class Response:
        ok = True

    def fake_post(url, json, timeout):
        calls.update(url=url, json=json)
        return Response()

    assert send_alert("Vídeo bloqueado", post=fake_post) is True
    assert calls["url"].endswith("/sendMessage")
    assert calls["json"] == {"chat_id": "42", "text": "Vídeo bloqueado"}


def test_alerts_are_skipped_when_telegram_is_not_configured(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)

    assert send_alert("Hola", post=lambda **kwargs: pytest.fail("sent")) is False


def test_a_failed_alert_never_breaks_the_caller(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fixture-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "42")

    def failing_post(**kwargs):
        raise requests.ConnectionError("offline")

    assert send_alert("Hola", post=failing_post) is False
