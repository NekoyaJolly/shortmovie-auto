"""画像処理ユーティリティ（リサイズ・テロップ合成）"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from src.config import get_settings

# デフォルト背景色（画像がない場合）
DEFAULT_BG_COLOR = (30, 30, 40)
# テロップ背景の半透明帯
TELOP_BG_COLOR = (0, 0, 0, 180)
TELOP_TEXT_COLOR = (255, 255, 255)
TELOP_MARGIN = 40
TELOP_PADDING = 20


def resize_and_crop(image_path: Path, output_path: Path, width: int = 1080, height: int = 1920) -> Path:
    """画像を指定サイズにリサイズ＆中央クロップ"""
    img = Image.open(image_path).convert("RGB")

    # アスペクト比を維持してリサイズ
    img_ratio = img.width / img.height
    target_ratio = width / height

    if img_ratio > target_ratio:
        # 横が広い → 高さに合わせてリサイズ、横をクロップ
        new_height = height
        new_width = int(height * img_ratio)
    else:
        # 縦が長い → 幅に合わせてリサイズ、縦をクロップ
        new_width = width
        new_height = int(width / img_ratio)

    img = img.resize((new_width, new_height), Image.LANCZOS)

    # 中央クロップ
    left = (new_width - width) // 2
    top = (new_height - height) // 2
    img = img.crop((left, top, left + width, top + height))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, "PNG")
    return output_path


def create_blank_frame(output_path: Path, width: int = 1080, height: int = 1920) -> Path:
    """無地の背景フレームを作成"""
    img = Image.new("RGB", (width, height), DEFAULT_BG_COLOR)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, "PNG")
    return output_path


def _get_font(size: int | None = None) -> ImageFont.FreeTypeFont:
    """フォントを取得"""
    settings = get_settings()
    if size is None:
        size = settings.video.font_size

    font_path = settings.assets_dir / "fonts" / settings.video.font
    if font_path.exists():
        return ImageFont.truetype(str(font_path), size)

    # フォールバック: システムフォントを探す
    fallback_fonts = [
        "C:/Windows/Fonts/meiryo.ttc",
        "C:/Windows/Fonts/msgothic.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",
    ]
    for fb in fallback_fonts:
        if Path(fb).exists():
            return ImageFont.truetype(fb, size)

    return ImageFont.load_default()


def add_text_overlay(
    image_path: Path,
    text: str,
    output_path: Path,
    position: str = "bottom",
) -> Path:
    """画像にテロップ（テキストオーバーレイ）を追加"""
    base = Image.open(image_path).convert("RGBA")
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    font = _get_font()

    # テキストを折り返し
    max_width = base.width - TELOP_MARGIN * 2
    lines = _wrap_text(text, font, max_width)

    # テキスト全体の高さを計算
    line_height = font.size + 8
    total_text_height = len(lines) * line_height

    # 背景帯の位置
    if position == "bottom":
        bg_top = base.height - total_text_height - TELOP_PADDING * 2 - TELOP_MARGIN
    elif position == "top":
        bg_top = TELOP_MARGIN
    else:  # center
        bg_top = (base.height - total_text_height - TELOP_PADDING * 2) // 2

    bg_bottom = bg_top + total_text_height + TELOP_PADDING * 2

    # 半透明背景帯
    draw.rectangle(
        [(0, bg_top), (base.width, bg_bottom)],
        fill=TELOP_BG_COLOR,
    )

    # テキスト描画
    y = bg_top + TELOP_PADDING
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        text_width = bbox[2] - bbox[0]
        x = (base.width - text_width) // 2
        draw.text((x, y), line, fill=TELOP_TEXT_COLOR, font=font)
        y += line_height

    result = Image.alpha_composite(base, overlay).convert("RGB")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.save(output_path, "PNG")
    return output_path


def _wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    """テキストを最大幅に合わせて折り返し"""
    lines = []
    current_line = ""

    for char in text:
        test_line = current_line + char
        bbox = font.getbbox(test_line)
        if bbox[2] > max_width and current_line:
            lines.append(current_line)
            current_line = char
        else:
            current_line = test_line

    if current_line:
        lines.append(current_line)

    return lines
