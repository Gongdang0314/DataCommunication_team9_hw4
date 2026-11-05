"""Render a verified 301-frame run as a GIF, using Pillow.

Example: python tools/make_gif.py output/run1/frames output/G9HW4.gif --n 6

Adapted from the instructor-provided HW4_student_pack/2_tools/python/make_gif.py.
The layout, colors, and timing follow that helper. Added strict input checks,
team identification, boundary-state labels, and a saved GIF frame-count check.
"""

import argparse
from pathlib import Path
import tempfile

from PIL import Image, ImageDraw, ImageFont


WIDTH, HEIGHT = 160, 80
CW, CH, LEFT, TOP = 6, 10, 34, 24
IMAGE_SIZE = (LEFT + WIDTH * CW + 6, TOP + HEIGHT * CH + 6)
COLORS = ((127, 224, 255), (255, 150, 125), (205, 180, 255))
ROUNDS = tuple(range(0, 3001, 10))


def load_font():
    candidates = (
        "DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "C:/Windows/Fonts/consola.ttf",
        "/System/Library/Fonts/Menlo.ttc",
    )
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, 10)
        except OSError:
            continue
    return ImageFont.load_default()


def read_frames(folder):
    expected = {f"frame{r:04d}.txt" for r in ROUNDS}
    actual = {p.name for p in folder.glob("frame*.txt") if p.is_file()}
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise ValueError(f"Expected exactly 301 frames; missing={missing}, extra={extra}")
    frames = []
    for r in ROUNDS:
        path = folder / f"frame{r:04d}.txt"
        raw = path.read_bytes()
        rows = raw.split(b"\n")
        if (len(raw) != 12880 or len(rows) != 81 or rows[-1] != b""
                or any(len(row) != WIDTH for row in rows[:-1])
                or any(c < 32 or c > 126 for row in rows[:-1] for c in row)):
            raise ValueError(f"Invalid ASCII/LF canvas format: {path}")
        frames.append([row.decode("ascii") for row in rows[:-1]])
    return frames


def phase(round_number):
    # Saved S(1000) and S(2000) precede repaint/conversion: they contain the
    # result of Rule1 round 999 and Rule2 round 1999 respectively.
    rule_index = max(0, (round_number - 1) // 1000)
    label = f"Rule{rule_index + 1}"
    if round_number in (1000, 2000):
        label += " done / before repaint"
    elif round_number == 0:
        label += " initial"
    return rule_index, label


def make_gif(folder, output, n, team):
    frames = read_frames(folder)
    font = load_font()
    bounds = [HEIGHT * k // n for k in range(n + 1)]
    images, durations = [], []
    for r, rows in zip(ROUNDS, frames):
        rule_index, label = phase(r)
        color = COLORS[rule_index]
        im = Image.new("RGB", IMAGE_SIZE, (12, 20, 32))
        draw = ImageDraw.Draw(im)
        # Round changes even when the board repeats, preventing GIF encoders
        # from combining identical adjacent snapshots into one long frame.
        draw.text((6, 6), f"G{team}   Round {r:4d} / 3000   {label}   N={n}",
                  font=font, fill=color)
        for k in range(n):
            y = TOP + bounds[k] * CH
            draw.line([(LEFT, y), (LEFT + WIDTH * CW, y)], fill=(60, 75, 100))
            draw.text((4, y + 2), f"W{k}", font=font, fill=(150, 160, 180))
        for y, row in enumerate(rows):
            draw.text((LEFT, TOP + y * CH), row, font=font, fill=color)
        images.append(im.convert("P", palette=Image.Palette.ADAPTIVE, colors=16))
        durations.append(1000 if r in (0, 1000, 2000, 3000) else 80)

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".gif", dir=output.parent, delete=False) as temp:
        temporary_output = Path(temp.name)
    try:
        images[0].save(temporary_output, format="GIF", save_all=True,
                       append_images=images[1:], duration=durations, loop=0,
                       optimize=True)
        with Image.open(temporary_output) as saved:
            if saved.n_frames != 301 or saved.size != IMAGE_SIZE:
                raise ValueError(f"GIF verification failed: {saved.n_frames} frames, {saved.size}")
            for i, duration in enumerate(durations):
                saved.seek(i)
                if saved.info.get("duration") != duration:
                    raise ValueError(f"GIF timing mismatch at frame {i}")
        temporary_output.replace(output)
    finally:
        temporary_output.unlink(missing_ok=True)
    print(f"{output}: verified 301 frames, {output.stat().st_size / 1e6:.2f} MB, G{team}, N={n}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("frames", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--n", type=int, required=True, choices=(1, 4, 5, 6, 7, 8))
    parser.add_argument("--team", type=int, default=9)
    args = parser.parse_args()
    if args.team < 1:
        parser.error("--team must be positive")
    try:
        make_gif(args.frames, args.output, args.n, args.team)
    except (ValueError, OSError) as exc:
        parser.exit(1, f"ERROR: {exc}\n")


if __name__ == "__main__":
    main()
