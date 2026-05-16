"""One-off generator for the mock Analysis Sheet image.

Produces ``mock_pptx_data/analysis-sheet.png`` — a screenshot-style
mock of the MS Word table that analysts fill in with GramFrame
measurements (harmonics, base frequencies, speed, etc.). The runtime
pipeline (``mock_pptx.py``) only copies the committed PNG; this
script is the offline tool that rebuilds it when the layout changes.

Requires Pillow. Not in the project's air-gapped runtime deps — run
this script on a developer machine and commit the resulting PNG.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def _load_font(size: int) -> ImageFont.ImageFont:
    for name in (
        "DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _load_bold(size: int) -> ImageFont.ImageFont:
    for name in (
        "DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


WIDTH = 760
HEIGHT = 560
MARGIN = 24
BG = (255, 255, 255)
TEXT = (32, 32, 32)
RULE = (130, 130, 130)
HEADER_BG = (224, 230, 240)
ROW_ALT_BG = (247, 249, 252)


ROWS: list[tuple[str, str]] = [
    ("Contact / Gram ID", "Gram 17"),
    ("Bearing (deg true)", "047"),
    ("Estimated speed (kn)", "12.5"),
    ("Base frequency f0 (Hz)", "63.4"),
    ("Harmonic 2 (Hz)", "126.8"),
    ("Harmonic 3 (Hz)", "190.1"),
    ("Harmonic 4 (Hz)", "253.6"),
    ("Shaft rate (Hz)", "5.28"),
    ("Blade rate / blade count", "31.7 Hz  /  6"),
    ("Bandwidth observed (Hz)", "0 - 400"),
    ("Tonal stability", "Stable, slight drift"),
    ("Classification", "Cat 2 - Merchant"),
    ("Identification (vessel)", "MV NORTH STAR"),
    ("Analyst notes", "Strong f0 with 4 harmonics; brief speed-up at t=180s"),
]


def render(path: Path) -> None:
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)

    title_font = _load_bold(18)
    sub_font = _load_font(12)
    header_font = _load_bold(13)
    body_font = _load_font(13)

    draw.text((MARGIN, MARGIN), "ACOUSTIC ANALYSIS SHEET", font=title_font, fill=TEXT)
    draw.text(
        (MARGIN, MARGIN + 26),
        "Complete each row from your GramFrame measurements.",
        font=sub_font,
        fill=(90, 90, 90),
    )

    table_top = MARGIN + 60
    table_left = MARGIN
    table_right = WIDTH - MARGIN
    col_split = table_left + 280
    row_h = 30
    header_h = 28

    # Header row
    draw.rectangle(
        [table_left, table_top, table_right, table_top + header_h],
        fill=HEADER_BG, outline=RULE,
    )
    draw.text((table_left + 10, table_top + 6), "Field", font=header_font, fill=TEXT)
    draw.text((col_split + 10, table_top + 6), "Measurement", font=header_font, fill=TEXT)
    draw.line(
        [(col_split, table_top), (col_split, table_top + header_h)],
        fill=RULE,
    )

    # Body rows
    y = table_top + header_h
    for idx, (label, value) in enumerate(ROWS):
        if idx % 2 == 1:
            draw.rectangle(
                [table_left, y, table_right, y + row_h], fill=ROW_ALT_BG,
            )
        draw.rectangle(
            [table_left, y, table_right, y + row_h],
            outline=RULE,
        )
        draw.line([(col_split, y), (col_split, y + row_h)], fill=RULE)
        draw.text((table_left + 10, y + 8), label, font=body_font, fill=TEXT)
        draw.text((col_split + 10, y + 8), value, font=body_font, fill=TEXT)
        y += row_h

    # Footer line
    footer_y = y + 18
    draw.text(
        (MARGIN, footer_y),
        "Analyst: ____________________     Date: __________     Sheet ref: AS-017",
        font=sub_font, fill=(70, 70, 70),
    )

    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, format="PNG", optimize=True)


if __name__ == "__main__":
    here = Path(__file__).resolve().parent.parent
    out = here / "mock_pptx_data" / "analysis-sheet.png"
    render(out)
    print(f"wrote {out}")
