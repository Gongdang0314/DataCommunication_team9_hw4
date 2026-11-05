"""Build a verified HW4 ZIP; the default output is explicitly a DRAFT.

python tools/package_submission.py runs/n1 runs/run1 runs/run2
python tools/package_submission.py runs/n1 runs/run1 runs/run2 --final

The GIF must already have been generated from run1 using tools/make_gif.py.
Final mode also requires completed Readme.txt and download.txt. Video access,
team member information, and remote-deployment evidence need human review.
"""

import argparse
import hashlib
from pathlib import Path
import re
import tempfile
from urllib.parse import urlsplit
import zipfile

from PIL import Image

from make_gif import make_gif
from verify_results import FRAMES, ROUNDS, board_bytes, require, verify_all


ROOT = Path(__file__).resolve().parents[1]


def documents(final):
    result = {}
    for name in ("Readme.txt", "download.txt"):
        path = ROOT / name
        if path.is_file():
            result[name] = path.read_bytes()
        else:
            require(not final, f"Final submission requires {name}")
            result[name] = f"DRAFT - TODO: complete {name} before submission.\n".encode("utf-8")
        text = result[name].decode("utf-8-sig")
        if final:
            require(bool(text.strip()), f"{name} is empty")
            require(re.search(r"TODO|미입력|TBD|미작성", text, re.IGNORECASE) is None,
                    f"{name} still contains unfinished placeholders")
    if final:
        text = result["download.txt"].decode("utf-8-sig")
        urls = re.findall(r'https://[^\s<>"\']+', text)
        require(any(urlsplit(url).hostname and not urlsplit(url).username for url in urls),
                "download.txt must contain an HTTPS download URL")
    return result


def check_gif(gif, run1, n, team, temporary):
    require(gif.is_file(), f"Missing GIF: {gif}; first run tools/make_gif.py")
    with Image.open(gif) as actual:
        require(actual.format == "GIF" and actual.n_frames == 301,
                "Submission GIF must contain exactly 301 frames")
    # Regeneration checks every frame, including the first/last board and the
    # G/team/N header, against this exact run. This deliberately requires our
    # current renderer so an old or unrelated GIF cannot silently be packaged.
    expected = temporary / "expected.gif"
    make_gif(run1 / "frames", expected, n, team)
    require(gif.read_bytes() == expected.read_bytes(),
            "GIF does not match run1/current renderer. Regenerate it with "
            f"tools/make_gif.py {run1 / 'frames'} {gif} --n {n} --team {team}")


def package(n1, run1, run2, output, gif, team=9, final=False):
    entries = documents(final)
    for filename in ("requirements.txt", ".gitattributes", "AllDefinedLogs.txt"):
        entries[filename] = (ROOT / filename).read_bytes()
    if (ROOT / "README.md").is_file():
        entries["README.md"] = (ROOT / "README.md").read_bytes()
    for path in ROOT.glob("*.py"):
        entries[path.name] = path.read_bytes()
    # Explicit directory and extension allowlists exclude .git, private keys,
    # environments, caches, unrelated downloads, and failed-run directories.
    for folder, suffixes in (("tools", {".py"}), ("tests", {".py", ".txt", ".json"}),
                             ("docs", {".md", ".txt"})):
        for path in (ROOT / folder).rglob("*"):
            if path.is_file() and path.suffix in suffixes and "__pycache__" not in path.parts:
                entries[path.relative_to(ROOT).as_posix()] = path.read_bytes()
    for i in range(3):
        name = f"canvas{i}.txt"
        raw = board_bytes(ROOT / "canvas" / name)
        dots, spaces = raw.count(b"."), raw.count(b" ")
        require(0.04 <= dots / max(1, dots + spaces) <= 0.06
                and 12800 - dots - spaces >= 384, f"{name}: invalid dot/stroke count")
        entries[name] = entries[f"canvas/{name}"] = raw
    require(entries["canvas0.txt"] == (n1 / "round0000.txt").read_bytes(),
            "Current canvas0 differs from the verified runs")

    with tempfile.TemporaryDirectory(prefix="hw4-package-") as temporary_name:
        temporary = Path(temporary_name)
        report = verify_all(n1, run1, run2, team, temporary / "verification")
        check_gif(gif, run1, report["runs"][1]["n"], team, temporary)
        entries[f"G{team}HW4.gif"] = gif.read_bytes()
        for name in ("hash_result.txt", "verification.json"):
            entries[name] = (temporary / "verification" / name).read_bytes()
        for label, folder, result in zip(("n1", "run1", "run2"), (n1, run1, run2), report["runs"]):
            names = ["run.json", "summary.json", "Assigner.txt", "RoundHash.txt"]
            names += [f"round{r:04d}.txt" for r in ROUNDS]
            names += [f"frames/frame{r:04d}.txt" for r in FRAMES]
            if (folder / "metrics.json").is_file():
                names.append("metrics.json")
            if (folder / "workers").is_dir():
                names += [f"workers/Worker{k}.{suffix}" for k in range(result["n"])
                          for suffix in ("txt", "json")]
            for name in names:
                raw = (folder / name).read_bytes()
                entries[f"evidence/{label}/{name}"] = raw
                if label == "run1" and (name.startswith("round") or name == "Assigner.txt"):
                    entries[name] = raw
                if label == "run1" and name.startswith("workers/") and name.endswith(".txt"):
                    entries[Path(name).name] = raw

    state = "FINAL" if final else "DRAFT - NOT READY FOR SUBMISSION"
    status = (f"{state}\nTEAM {team}\n31/31 cross-run hashes verified.\n"
              "GIF verified against run1 frames and current renderer.\n"
              "Root round files and node logs are from evidence/run1.\n"
              "Full runs: evidence/n1, evidence/run1, evidence/run2.\n"
              "Human checks: team details, remote-server evidence, video contents and sharing access.\n")
    if not final:
        status += "Complete Readme.txt/download.txt, then rerun with --final.\n"
    entries["STATUS.txt"] = status.encode("utf-8")
    manifest = "".join(f"{hashlib.sha256(data).hexdigest()}  {name}\n"
                       for name, data in sorted(entries.items()))
    entries["MANIFEST.sha256"] = manifest.encode("utf-8")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".zip", dir=output.parent, delete=False) as temp:
        temporary_zip = Path(temp.name)
    try:
        with zipfile.ZipFile(temporary_zip, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for name, data in sorted(entries.items()):
                archive.writestr(name, data)
        with zipfile.ZipFile(temporary_zip) as archive:
            require(archive.testzip() is None, "ZIP CRC validation failed")
            require(len(archive.namelist()) == len(entries), "ZIP entry count mismatch")
        temporary_zip.replace(output)
    finally:
        temporary_zip.unlink(missing_ok=True)
    print(f"{state}: {output.resolve()} ({len(entries)} files; {output.stat().st_size / 1e6:.2f} MB)")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("n1", type=Path)
    parser.add_argument("run1", type=Path)
    parser.add_argument("run2", type=Path)
    parser.add_argument("--team", type=int, default=9)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--gif", type=Path)
    parser.add_argument("--final", action="store_true")
    args = parser.parse_args()
    if args.team < 1:
        parser.error("--team must be positive")
    output = args.out or ROOT / "dist" / f"G{args.team}HW4{'' if args.final else '_DRAFT'}.zip"
    gif = args.gif or ROOT / "output" / f"G{args.team}HW4.gif"
    try:
        package(args.n1, args.run1, args.run2, output, gif, args.team, args.final)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        parser.exit(1, f"ERROR: {exc}\n")


if __name__ == "__main__":
    main()
