"""Whole-board, no-network reference used to check rule correctness.

This is a development check, NOT the required Assigner + one Worker baseline.
Example: python tools/reference.py --canvas tests/fixtures/G11_sample --team 11
         --out output/reference_g11 --expected tests/fixtures/G11_sample/RoundHash_N1.txt
"""
import argparse
import hashlib
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import read_board
from myrules import repaint, rule1, rule2, rule3, to_brian, to_cyclic


def run(args):
    if args.out.exists() and any(args.out.iterdir()):
        raise ValueError("reference output directory must be empty")
    canvases = [[list(row) for row in read_board(args.canvas / f"canvas{i}.txt")]
                for i in range(3)]
    expected = None
    if args.expected:
        expected = dict(line.split() for line in args.expected.read_text(encoding="ascii").splitlines()
                        if line.strip() and not line.startswith("#"))
        if set(expected) != {f"round{r:04d}.txt" for r in range(0, 3001, 100)}:
            raise ValueError("expected hash file must contain all 31 checkpoints")
    args.out.mkdir(parents=True, exist_ok=True)
    board = canvases[0]
    hashes = []
    started = time.perf_counter()
    for r in range(3001):
        if r % 100 == 0:
            name = f"round{r:04d}.txt"
            data = ("".join("".join(row) + "\n" for row in board)).encode("ascii")
            digest = hashlib.sha256(data).hexdigest()[:8]
            (args.out / name).write_bytes(data)
            hashes.append(f"{name} {digest}")
            if expected and expected[name] != digest:
                raise ValueError(f"{name}: expected {expected[name]}, got {digest}")
        if r == 3000:
            break
        if r == 1000:
            repaint(board, canvases[1])
            to_brian(board)
        elif r == 2000:
            repaint(board, canvases[2])
            to_cyclic(board, 0, args.team)
        board = (rule1, rule2, rule3)[r // 1000](board)
    (args.out / "RoundHash.txt").write_bytes(("\n".join(hashes) + "\n").encode("ascii"))
    print(f"REFERENCE PASS: G{args.team}, 3000 rounds, 31 checkpoints, "
          f"{time.perf_counter() - started:.2f}s" +
          (", all supplied expected hashes matched" if expected else ""))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--canvas", type=Path, required=True)
    parser.add_argument("--team", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--expected", type=Path)
    args = parser.parse_args()
    try:
        run(args)
    except (OSError, ValueError) as exc:
        print(f"REFERENCE FAIL: {exc}", file=sys.stderr)
        sys.exit(1)
