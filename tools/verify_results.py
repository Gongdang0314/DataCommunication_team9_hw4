"""Verify three completed runs and write the HW4 hash_result.txt submission.

Usage: python tools/verify_results.py runs/n1 runs/run1 runs/run2 --team 9
       --out output/verification
Uses only the Python standard library. Metadata checks do not independently
prove a remote deployment; retain server details and the demonstration video.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROUNDS = tuple(range(0, 3001, 100))
FRAMES = tuple(range(0, 3001, 10))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_json(path):
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"{path}: expected a JSON object")
    return value


def board_bytes(path):
    data = path.read_bytes()
    rows = data.split(b"\n")
    require(len(data) == 12880 and len(rows) == 81 and rows[-1] == b""
            and all(len(row) == 160 for row in rows[:-1]),
            f"{path}: expected 80 x 160 characters and LF after every row")
    require(all(32 <= char <= 126 for row in rows[:-1] for char in row),
            f"{path}: only printable ASCII is allowed")
    return data


def check_log(path, worker=False):
    lines = path.read_text(encoding="utf-8").splitlines()
    require(not any("| FAIL |" in line for line in lines), f"{path}: FAIL event present")
    terminated = [line for line in lines if "| TERMINATE | SUCCESS |" in line]
    require(len(terminated) == 1, f"{path}: exactly one successful termination required")
    if worker:
        require(re.search(r"\brounds=3000\b", terminated[0]) is not None,
                f"{path}: Worker did not report 3000 rounds")
        require("BYE" in terminated[0], f"{path}: missing BYE termination")
        return None
    details = json.loads(terminated[0].split("|", 3)[-1])
    require(details.get("rounds") == 3000, f"{path}: Assigner did not report 3000 rounds")
    return details


def verify_run(folder, team, distributed):
    folder = Path(folder)
    run = read_json(folder / "run.json")
    summary = read_json(folder / "summary.json")
    n = run.get("n")
    require(type(n) is int and n in (1, 4, 5, 6, 7, 8), f"{folder}: invalid N")
    require(type(run.get("team")) is int and run["team"] == team,
            f"{folder}: TEAM does not match --team {team}")
    require(summary.get("rounds") == 3000, f"{folder}: not a completed 3000-round run")
    for key in ("n", "team", "random_n", "bands", "timezone", "port"):
        require(key in run and summary.get(key) == run[key],
                f"{folder}: run.json/summary.json disagree or omit {key}")
    require(run["bands"] == [80 * k // n for k in range(n + 1)],
            f"{folder}: incorrect band boundaries")
    if distributed:
        require(4 <= n <= 8 and run.get("random_n") is True,
                f"{folder}: submission run requires random N=4..8")
    else:
        require(n == 1, f"{folder}: baseline must use N=1")
    logged = check_log(folder / "Assigner.txt")
    require(logged == summary, f"{folder}: summary.json differs from Assigner termination log")

    expected_names = {f"round{r:04d}.txt" for r in ROUNDS}
    # Windows glob is case-insensitive, so round*.txt would include RoundHash.txt.
    require({p.name for p in folder.iterdir() if p.name.startswith("round") and p.suffix == ".txt"}
            == expected_names,
            f"{folder}: require exactly the 31 round0000..round3000 files")
    records = {}
    raw_records = (folder / "RoundHash.txt").read_bytes()
    require(b"\r" not in raw_records, f"{folder}/RoundHash.txt: CRLF is not allowed")
    for line in raw_records.decode("ascii").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        fields = line.split()
        require(len(fields) == 2, f"{folder}/RoundHash.txt: malformed record")
        name, digest = fields
        require(name in expected_names and name not in records,
                f"{folder}/RoundHash.txt: duplicate/unexpected file {name}")
        require(re.fullmatch("[0-9a-f]{8}", digest) is not None,
                f"{folder}/RoundHash.txt: invalid lowercase hash {digest}")
        records[name] = digest
    require(list(records) == [f"round{r:04d}.txt" for r in ROUNDS],
            f"{folder}/RoundHash.txt: 31 records must be in round order")
    actual = {}
    for r in ROUNDS:
        name = f"round{r:04d}.txt"
        actual[name] = hashlib.sha256(board_bytes(folder / name)).hexdigest()[:8]
        require(actual[name] == records[name], f"{folder}/{name}: recorded/calculated hash mismatch")

    frames_dir = folder / "frames"
    expected_frames = {f"frame{r:04d}.txt" for r in FRAMES}
    require({p.name for p in frames_dir.glob("frame*.txt")} == expected_frames,
            f"{folder}: require exactly 301 frame0000..frame3000 files")
    for r in FRAMES:
        data = board_bytes(frames_dir / f"frame{r:04d}.txt")
        if r % 100 == 0:
            require(data == (folder / f"round{r:04d}.txt").read_bytes(),
                    f"{folder}: frame/round mismatch at {r}")

    workers = folder / "workers"
    require(workers.is_dir() or not distributed,
            f"{folder}: distributed evidence requires workers/ logs and JSON summaries")
    checked_workers = 0
    if workers.exists():
        require({p.name for p in workers.glob("Worker*.json")} ==
                {f"Worker{k}.json" for k in range(n)}, f"{workers}: expected exactly N summaries")
        require({p.name for p in workers.glob("Worker*.txt")} ==
                {f"Worker{k}.txt" for k in range(n)}, f"{workers}: expected exactly N logs")
        for k in range(n):
            worker = read_json(workers / f"Worker{k}.json")
            for key, expected in (("k", k), ("n", n), ("team", team), ("rounds", 3000),
                                  ("height", 80 * (k + 1) // n - 80 * k // n)):
                require(worker.get(key) == expected, f"{workers}/Worker{k}.json: invalid {key}")
            check_log(workers / f"Worker{k}.txt", worker=True)
            checked_workers += 1
    return dict(path=str(folder.resolve()), n=n, team=team, random_n=run["random_n"],
                round_files=31, frame_files=301, workers_checked=checked_workers,
                hashes=actual, status="PASS")


def verify_all(n1, run1, run2, team, out):
    results = [verify_run(path, team, index != 0)
               for index, path in enumerate((n1, run1, run2))]
    require(results[1]["n"] != results[2]["n"], "The two distributed runs must have different N")
    require(results[0]["hashes"] == results[1]["hashes"] == results[2]["hashes"],
            "The three runs do not have identical hashes at all 31 checkpoints")
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    lines = [f"TEAM {team}",
             f'ROUND N=1 N={results[1]["n"]} N={results[2]["n"]} RESULT']
    for r in ROUNDS:
        digest = results[0]["hashes"][f"round{r:04d}.txt"]
        lines.append(f"{r:04d} {digest} {digest} {digest} SAME")
    digest = results[0]["hashes"]["round3000.txt"]
    lines.extend((f"FINAL {digest} {digest} {digest} SAME", "TOTAL 31/31 SAME -> PASS"))
    report = dict(team=team, status="PASS", same=31, total=31, runs=results,
                  scope="File format, recorded hashes, cross-run equality, frames and completion logs. "
                        "Remote deployment and simulation correctness require separate evidence.")
    (out / "hash_result.txt").write_bytes(("\n".join(lines) + "\n").encode("ascii"))
    (out / "verification.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main():
    # Redirected Windows consoles may use cp949 while the path contains Chinese.
    # A successful verification must not fail merely while printing its path.
    sys.stdout.reconfigure(errors="backslashreplace")
    sys.stderr.reconfigure(errors="backslashreplace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("n1", type=Path)
    parser.add_argument("run1", type=Path)
    parser.add_argument("run2", type=Path)
    parser.add_argument("--team", type=int, required=True)
    parser.add_argument("--out", type=Path, default=Path("output/verification"))
    args = parser.parse_args()
    if args.team <= 0:
        parser.error("--team must be positive")
    # Clear stale PASS artifacts before checking a changed set of runs.
    for name in ("hash_result.txt", "verification.json"):
        path = args.out / name
        if path.is_file():
            path.unlink()
    try:
        verify_all(args.n1, args.run1, args.run2, args.team, args.out)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / "verification.json").write_text(
            json.dumps(dict(status="FAIL", error=str(exc)), indent=2) + "\n", encoding="utf-8")
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(f"TOTAL 31/31 SAME -> PASS; results: {args.out.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
