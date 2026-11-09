import os
from pathlib import Path
from typing import Callable

from app.datavideo.channels import PublishSettings
from app.datavideo.packaging import Package
from app.services import upload_post

_YOUTUBE_TITLE_LIMIT = 100


def upload_account(user: str) -> dict:
    api_key = os.environ.get("UPLOAD_POST_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("UPLOAD_POST_API_KEY is not set")
    return {"upload_post_api_key": api_key, "upload_post_username": user, "upload_post_enabled": True}


def publish_video(
    video_path: Path,
    package: Package,
    target: PublishSettings,
    cross_post: Callable[..., dict] = upload_post.cross_post_video,
) -> dict:
    account = upload_account(target.user)
    youtube_extra = {
        "youtube_title": package.title[:_YOUTUBE_TITLE_LIMIT],
        "youtube_description": package.description,
        "tags": list(package.tags),
        "privacyStatus": target.privacy,
        "selfDeclaredMadeForKids": False,
    }
    return cross_post(
        video_path=str(video_path),
        title=package.description,
        platforms=list(target.platforms),
        youtube_extra=youtube_extra,
        account=account,
    )
