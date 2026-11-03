from dataclasses import dataclass

Color = tuple[int, int, int]


@dataclass(frozen=True)
class Theme:
    background: Color = (14, 17, 23)
    neutral: Color = (88, 101, 122)
    positive: Color = (46, 204, 113)
    negative: Color = (231, 76, 60)
    text: Color = (240, 242, 245)
    muted: Color = (150, 160, 175)
    font_file: str = "BeVietnamPro-Bold.ttf"


DEFAULT_THEME = Theme()
