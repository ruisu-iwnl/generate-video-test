"""Generates a 1920x1080 background frame per segment: vertical gradient +
title text + segment index. No network required (procedural, via Pillow)."""
import pathlib
from PIL import Image, ImageDraw, ImageFont

W, H = 1920, 1080
FONT_PATH = "C:/Windows/Fonts/arialbd.ttf"
FONT_PATH_REG = "C:/Windows/Fonts/arial.ttf"


def _hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _gradient(c1, c2):
    top = _hex_to_rgb(c1)
    bottom = _hex_to_rgb(c2)
    img = Image.new("RGB", (W, H), top)
    draw = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        r = int(top[0] + (bottom[0] - top[0]) * t)
        g = int(top[1] + (bottom[1] - top[1]) * t)
        b = int(top[2] + (bottom[2] - top[2]) * t)
        draw.line([(0, y), (W, y)], fill=(r, g, b))
    return img


def _wrap_text(draw, text, font, max_width):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=font) <= max_width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def render_segment_image(segment: dict, total: int, out_path: pathlib.Path):
    img = _gradient(segment["color_top"], segment["color_bottom"])
    draw = ImageDraw.Draw(img)

    title_font = ImageFont.truetype(FONT_PATH, 96)
    label_font = ImageFont.truetype(FONT_PATH_REG, 34)

    lines = _wrap_text(draw, segment["title"], title_font, W * 0.8)
    line_height = 112
    total_h = line_height * len(lines)
    y = (H - total_h) / 2
    for line in lines:
        w = draw.textlength(line, font=title_font)
        draw.text(((W - w) / 2 + 3, y + 3), line, font=title_font, fill=(0, 0, 0, 120))
        draw.text(((W - w) / 2, y), line, font=title_font, fill="white")
        y += line_height

    accent_w = 140
    draw.rectangle([(W - accent_w) / 2, y + 20, (W + accent_w) / 2, y + 26], fill="white")

    label = f"{segment['id'] + 1} / {total}"
    draw.text((W - 160, H - 70), label, font=label_font, fill=(255, 255, 255, 180))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "PNG")
    return out_path
