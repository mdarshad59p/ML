"""
Pillow-based image generators for the fun-zone features:
- meme (top/bottom caption on a template)
- fakechat (generic messaging-app style screenshot)
- fakewhatsapp (WhatsApp-style bubble mockup)
- friendship card

NOTE ON FONTS (please read):
This sandbox only has Latin/CJK fonts available (DejaVu, Noto CJK, etc.) —
there's no Bengali/Devanagari/Arabic-script font bundled here because building
this project happened without internet access to download one.
For Bangla (or Hindi/Urdu/Arabic) text to render correctly in generated
images, download a font that covers that script — e.g. "Noto Sans Bengali"
from Google Fonts — and drop the .ttf file into assets/fonts/ as
"script_font.ttf". This module will automatically prefer it if present.
Without it, non-Latin captions may show as blank boxes (□□□) in the image —
this is a Pillow/font limitation, not a bug in the bot logic.
"""
import os
import textwrap
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont

_ASSETS = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")
_FONTS_DIR = os.path.join(_ASSETS, "fonts")
_TEMPLATES_DIR = os.path.join(_ASSETS, "templates")

_DEJAVU_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
_SCRIPT_FONT = os.path.join(_FONTS_DIR, "script_font.ttf")  # user-provided, see docstring


def get_font(size: int) -> ImageFont.FreeTypeFont:
    """Prefer a user-supplied script font (for Bangla/Hindi/Urdu/Arabic),
    fall back to DejaVu Sans Bold (Latin/Cyrillic/Greek), fall back to PIL default."""
    if os.path.exists(_SCRIPT_FONT):
        try:
            return ImageFont.truetype(_SCRIPT_FONT, size)
        except OSError:
            pass
    if os.path.exists(_DEJAVU_BOLD):
        try:
            return ImageFont.truetype(_DEJAVU_BOLD, size)
        except OSError:
            pass
    return ImageFont.load_default(size=size)


def _draw_outlined_text(draw: ImageDraw.ImageDraw, xy, text, font, fill="white", outline="black", outline_width=2):
    x, y = xy
    for dx in range(-outline_width, outline_width + 1):
        for dy in range(-outline_width, outline_width + 1):
            if dx or dy:
                draw.text((x + dx, y + dy), text, font=font, fill=outline)
    draw.text((x, y), text, font=font, fill=fill)


def _wrap(text: str, width: int = 22) -> str:
    return "\n".join(textwrap.wrap(text, width=width)) or ""


def generate_meme(template_name: str, top_text: str, bottom_text: str) -> BytesIO:
    """
    Looks for assets/templates/<template_name>.jpg (or .png). If it isn't
    there (no real meme templates are bundled — see assets/templates/README.txt),
    falls back to a plain dark placeholder canvas so the feature still works
    end-to-end; just drop real template images in that folder to upgrade it.
    """
    path_jpg = os.path.join(_TEMPLATES_DIR, f"{template_name}.jpg")
    path_png = os.path.join(_TEMPLATES_DIR, f"{template_name}.png")

    if os.path.exists(path_jpg):
        img = Image.open(path_jpg).convert("RGB")
    elif os.path.exists(path_png):
        img = Image.open(path_png).convert("RGB")
    else:
        img = Image.new("RGB", (800, 800), color=(30, 30, 30))

    img = img.resize((800, int(800 * img.height / img.width)))
    draw = ImageDraw.Draw(img)
    font_size = max(28, img.width // 14)
    font = get_font(font_size)

    if top_text:
        wrapped = _wrap(top_text)
        bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, align="center")
        w = bbox[2] - bbox[0]
        _draw_outlined_text(draw, ((img.width - w) / 2, 15), wrapped, font)

    if bottom_text:
        wrapped = _wrap(bottom_text)
        bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, align="center")
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        _draw_outlined_text(draw, ((img.width - w) / 2, img.height - h - 25), wrapped, font)

    buf = BytesIO()
    buf.name = "meme.jpg"
    img.save(buf, "JPEG", quality=90)
    buf.seek(0)
    return buf


def generate_fake_chat(platform: str, sender: str, receiver: str, messages: list[str]) -> BytesIO:
    """Generic chat-bubble mockup. `messages` alternates sender/receiver starting with sender."""
    width = 720
    padding = 20
    bubble_gap = 14
    header_h = 70
    font = get_font(24)
    small_font = get_font(18)

    # pre-measure to size canvas
    tmp_img = Image.new("RGB", (10, 10))
    tmp_draw = ImageDraw.Draw(tmp_img)
    line_height = 34
    bubble_heights = []
    for msg in messages:
        wrapped = _wrap(msg, width=30)
        n_lines = wrapped.count("\n") + 1
        bubble_heights.append(n_lines * line_height + 24)

    total_h = header_h + sum(h + bubble_gap for h in bubble_heights) + padding

    img = Image.new("RGB", (width, total_h), color=(15, 20, 26) if platform.lower() != "whatsapp" else (7, 94, 84))
    draw = ImageDraw.Draw(img)

    # header bar
    draw.rectangle([0, 0, width, header_h], fill=(30, 35, 45))
    draw.text((20, 20), f"{receiver}  •  {platform}", font=font, fill="white")

    y = header_h + 10
    for i, msg in enumerate(messages):
        wrapped = _wrap(msg, width=30)
        h = bubble_heights[i]
        is_sender = i % 2 == 0
        bubble_w = min(width - 80, max(120, max(draw.textlength(line, font=font) for line in wrapped.split("\n")) + 40))
        x = width - bubble_w - 20 if is_sender else 20
        bubble_color = (0, 132, 255) if is_sender else (55, 60, 70)
        draw.rounded_rectangle([x, y, x + bubble_w, y + h], radius=16, fill=bubble_color)
        draw.multiline_text((x + 16, y + 12), wrapped, font=small_font, fill="white", spacing=6)
        y += h + bubble_gap

    buf = BytesIO()
    buf.name = "fakechat.png"
    img.save(buf, "PNG")
    buf.seek(0)
    return buf


def generate_friendship_card(name1: str, name2: str) -> BytesIO:
    width, height = 800, 450
    img = Image.new("RGB", (width, height), color=(255, 105, 135))
    draw = ImageDraw.Draw(img)

    # simple gradient background
    for y in range(height):
        ratio = y / height
        r = int(255 * (1 - ratio) + 120 * ratio)
        g = int(105 * (1 - ratio) + 40 * ratio)
        b = int(135 * (1 - ratio) + 160 * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    title_font = get_font(46)
    name_font = get_font(38)

    title = "Friendship Card"
    bbox = draw.textbbox((0, 0), title, font=title_font)
    tw = bbox[2] - bbox[0]
    _draw_outlined_text(draw, ((width - tw) / 2, 40), title, title_font)

    names_text = f"{name1}  💞  {name2}"
    bbox = draw.textbbox((0, 0), names_text, font=name_font)
    nw = bbox[2] - bbox[0]
    _draw_outlined_text(draw, ((width - nw) / 2, height / 2 - 10), names_text, name_font)

    buf = BytesIO()
    buf.name = "friendship.png"
    img.save(buf, "PNG")
    buf.seek(0)
    return buf
