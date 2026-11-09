import subprocess

from app.datavideo.qa import SHORT_LIMITS, check_video
from app.services.video import get_ffmpeg_binary

SIZE = (180, 320)


def make_video(path, size=SIZE, seconds=20, volume="0.5", audio=True):
    command = [
        get_ffmpeg_binary(), "-v", "error", "-y", "-f", "lavfi",
        "-i", f"color=c=black:s={size[0]}x{size[1]}:d={seconds}",
    ]
    if audio:
        command += ["-f", "lavfi", "-i", f"sine=frequency=300:duration={seconds}", "-af", f"volume={volume}", "-shortest"]
    command.append(str(path))
    subprocess.run(command, check=True)
    return path


def subtitles(path):
    path.write_text("1\n00:00:00,000 --> 00:00:01,000\nHola\n", encoding="utf-8")
    return path


def loud_video(tmp_path, **overrides):
    return make_video(tmp_path / "final.mp4", volume="2.6", **overrides)


def test_a_video_that_meets_every_check_passes(tmp_path):
    report = check_video(loud_video(tmp_path), SIZE, 20.0, subtitles(tmp_path / "a.srt"), SHORT_LIMITS)

    assert report.passed, report.problems


def test_a_video_without_audio_is_blocked(tmp_path):
    video = make_video(tmp_path / "final.mp4", audio=False)

    report = check_video(video, SIZE, 20.0, subtitles(tmp_path / "a.srt"), SHORT_LIMITS)

    assert any("audio" in problem for problem in report.problems)


def test_a_video_with_the_wrong_size_is_blocked(tmp_path):
    report = check_video(loud_video(tmp_path), (1080, 1920), 20.0, subtitles(tmp_path / "a.srt"), SHORT_LIMITS)

    assert any("size" in problem for problem in report.problems)


def test_a_video_whose_length_does_not_match_the_narration_is_blocked(tmp_path):
    report = check_video(loud_video(tmp_path), SIZE, 25.0, subtitles(tmp_path / "a.srt"), SHORT_LIMITS)

    assert any("narration" in problem for problem in report.problems)


def test_a_short_too_brief_for_the_format_is_blocked(tmp_path):
    video = make_video(tmp_path / "final.mp4", seconds=5, volume="2.6")

    report = check_video(video, SIZE, 5.0, subtitles(tmp_path / "a.srt"), SHORT_LIMITS)

    assert any("duration" in problem for problem in report.problems)


def test_a_quiet_video_is_blocked(tmp_path):
    video = make_video(tmp_path / "final.mp4", volume="0.01")

    report = check_video(video, SIZE, 20.0, subtitles(tmp_path / "a.srt"), SHORT_LIMITS)

    assert any("loudness" in problem for problem in report.problems)


def test_a_video_without_subtitles_is_blocked(tmp_path):
    report = check_video(loud_video(tmp_path), SIZE, 20.0, tmp_path / "missing.srt", SHORT_LIMITS)

    assert any("subtitles" in problem for problem in report.problems)
