"""Generate the three reproducible G9 input canvases (standard library only).

Run from any directory: python tools/make_canvas.py
Optional PNG previews: python tools/make_canvas.py --preview
The previews require Pillow; generating the actual ASCII inputs does not.
"""

import argparse
from pathlib import Path
import random


WIDTH, HEIGHT = 160, 80
ROOT = Path(__file__).resolve().parents[1]

# A hand-defined 5-by-7 uppercase bitmap font. Each occupied pixel is printed
# twice horizontally, making the letters legible in a tall terminal cell.
FONT = {
    "A": "01110/10001/10001/11111/10001/10001/10001",
    "B": "11110/10001/10001/11110/10001/10001/11110",
    "C": "01111/10000/10000/10000/10000/10000/01111",
    "D": "11110/10001/10001/10001/10001/10001/11110",
    "E": "11111/10000/10000/11110/10000/10000/11111",
    "F": "11111/10000/10000/11110/10000/10000/10000",
    "G": "01111/10000/10000/10111/10001/10001/01111",
    "H": "10001/10001/10001/11111/10001/10001/10001",
    "I": "11111/00100/00100/00100/00100/00100/11111",
    "J": "00111/00010/00010/00010/10010/10010/01100",
    "K": "10001/10010/10100/11000/10100/10010/10001",
    "L": "10000/10000/10000/10000/10000/10000/11111",
    "M": "10001/11011/10101/10101/10001/10001/10001",
    "N": "10001/11001/10101/10011/10001/10001/10001",
    "O": "01110/10001/10001/10001/10001/10001/01110",
    "P": "11110/10001/10001/11110/10000/10000/10000",
    "Q": "01110/10001/10001/10001/10101/10010/01101",
    "R": "11110/10001/10001/11110/10100/10010/10001",
    "S": "01111/10000/10000/01110/00001/00001/11110",
    "T": "11111/00100/00100/00100/00100/00100/00100",
    "U": "10001/10001/10001/10001/10001/10001/01110",
    "V": "10001/10001/10001/10001/10001/01010/00100",
    "W": "10001/10001/10001/10101/10101/10101/01010",
    "X": "10001/10001/01010/00100/01010/10001/10001",
    "Y": "10001/10001/01010/00100/00100/00100/00100",
    "Z": "11111/00001/00010/00100/01000/10000/11111",
    "9": "01110/10001/10001/01111/00001/00001/11110",
    " ": "00000/00000/00000/00000/00000/00000/00000",
}

# (text, column, row, stroke character). The three non-team phrases and their
# positions differ between canvases. Coordinates are zero-based.
LAYOUTS = (
    (("DATA COMM", 10, 7, "#"), ("TCP SOCKET", 30, 25, "@"),
     ("G9", 100, 45, "+"), ("TEAM WORK", 14, 64, "=")),
    (("ROUND SYNC", 40, 5, "*"), ("G9", 15, 24, "%"),
     ("MUTEX LOCK", 35, 44, "#"), ("HALO LINK", 12, 65, "+")),
    (("CYCLIC WAVE", 18, 8, "@"), ("BARRIER", 10, 28, "*"),
     ("G9", 115, 47, "#"), ("PYTHON", 38, 65, "=")),
)


def draw_text(board, text, x, y, ink):
    if x < 0 or y < 0 or x + len(text) * 12 - 2 > WIDTH or y + 7 > HEIGHT:
        raise ValueError(f"Text outside the canvas: {text!r}")
    for index, character in enumerate(text):
        for dy, row in enumerate(FONT[character].split("/")):
            for dx, pixel in enumerate(row):
                if pixel == "1":
                    px = x + index * 12 + dx * 2
                    board[y + dy][px:px + 2] = [ink, ink]


def make_canvas(index):
    board = [[" "] * WIDTH for _ in range(HEIGHT)]
    for text, x, y, ink in LAYOUTS[index]:
        draw_text(board, text, x, y, ink)
    rng = random.Random(900 + index)
    for row in board:
        for x, char in enumerate(row):
            if char == " " and rng.random() < 0.05:
                row[x] = "."
    return board


def encode_and_check(board):
    raw = ("\n".join("".join(row) for row in board) + "\n").encode("ascii")
    rows = raw.split(b"\n")
    assert len(raw) == 12880 and len(rows) == 81 and rows[-1] == b""
    assert all(len(row) == WIDTH for row in rows[:-1])
    assert all(32 <= c <= 126 for row in rows[:-1] for c in row)
    dots, spaces = raw.count(b"."), raw.count(b" ")
    ratio = dots / (dots + spaces)
    strokes = WIDTH * HEIGHT - dots - spaces
    assert 0.04 <= ratio <= 0.06, ratio
    assert strokes >= 384, strokes
    return raw, ratio, strokes


def save_preview(board, path, index):
    from PIL import Image, ImageDraw, ImageFont

    font_paths = ("C:/Windows/Fonts/consola.ttf", "DejaVuSansMono.ttf",
                  "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf")
    for font_path in font_paths:
        try:
            font = ImageFont.truetype(font_path, 10)
            break
        except OSError:
            continue
    else:
        font = ImageFont.load_default()
    im = Image.new("RGB", (1000, 850), (12, 20, 32))
    draw = ImageDraw.Draw(im)
    color = ((127, 224, 255), (255, 150, 125), (205, 180, 255))[index]
    draw.text((20, 10), f"G9 / canvas{index} / 160 x 80 / seed {900 + index}",
              font=font, fill=color)
    for y, row in enumerate(board):
        draw.text((20, 30 + y * 10), "".join(row), font=font, fill=color)
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "canvas")
    parser.add_argument("--preview", action="store_true")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    for index in range(3):
        board = make_canvas(index)
        raw, ratio, strokes = encode_and_check(board)
        path = args.out / f"canvas{index}.txt"
        path.write_bytes(raw)  # LF bytes on Windows, Linux, and macOS alike.
        print(f"{path.name}: {len(raw)} bytes, dots={ratio:.2%}, strokes={strokes}")
        if args.preview:
            save_preview(board, ROOT / "output" / "previews" / f"canvas{index}.png", index)


if __name__ == "__main__":
    main()
