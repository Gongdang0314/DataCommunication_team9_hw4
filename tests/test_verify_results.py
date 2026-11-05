"""Verifier must reject corrupt/partial evidence, not only compare hash strings."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from tools.verify_results import verify_all, verify_run


class VerificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.runs = [cls.root / name for name in ("n1", "run1", "run2")]
        data = (b" " * 160 + b"\n") * 80
        digest = hashlib.sha256(data).hexdigest()[:8]
        for folder, n in zip(cls.runs, (1, 4, 5)):
            (folder / "frames").mkdir(parents=True)
            (folder / "workers").mkdir()
            meta = dict(n=n, team=9, random_n=n != 1,
                        bands=[80 * k // n for k in range(n + 1)], timezone="UTC", port=19009)
            summary = dict(meta, rounds=3000)
            (folder / "run.json").write_text(json.dumps(meta), encoding="utf-8")
            (folder / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
            (folder / "Assigner.txt").write_text(
                "[00:00:00.000] ASSIGNER | TERMINATE | SUCCESS | " + json.dumps(summary) + "\n",
                encoding="utf-8")
            records = []
            for r in range(0, 3001, 10):
                (folder / "frames" / f"frame{r:04d}.txt").write_bytes(data)
                if r % 100 == 0:
                    (folder / f"round{r:04d}.txt").write_bytes(data)
                    records.append(f"round{r:04d}.txt {digest}")
            (folder / "RoundHash.txt").write_bytes(("\n".join(records) + "\n").encode("ascii"))
            for k in range(n):
                worker = dict(k=k, n=n, team=9, rounds=3000,
                              height=80 * (k + 1) // n - 80 * k // n)
                (folder / "workers" / f"Worker{k}.json").write_text(json.dumps(worker), encoding="utf-8")
                (folder / "workers" / f"Worker{k}.txt").write_text(
                    f"[00:00:00.000] WORKER{k} | TERMINATE | SUCCESS | BYE rounds=3000\n",
                    encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_consistent_evidence_produces_submission_format(self):
        out = self.root / "verified"
        report = verify_all(*self.runs, team=9, out=out)
        self.assertEqual(report["status"], "PASS")
        lines = (out / "hash_result.txt").read_bytes().split(b"\n")
        self.assertEqual(lines[0], b"TEAM 9")
        self.assertEqual(lines[1], b"ROUND N=1 N=4 N=5 RESULT")
        self.assertEqual(lines[-2], b"TOTAL 31/31 SAME -> PASS")
        self.assertEqual(len(lines), 36)

    def test_corrupt_or_incomplete_evidence_is_rejected(self):
        folder = self.runs[1]
        cases = [
            ("round0100.txt", lambda b: b.replace(b"\n", b"\r\n")),
            ("round0100.txt", lambda b: b"A" + b[1:]),
            ("frames/frame0010.txt", lambda b: b"\t" + b[1:]),
            ("frames/frame0100.txt", lambda b: b"B" + b[1:]),
            ("RoundHash.txt", lambda b: b + b.splitlines()[0] + b"\n"),
            ("run.json", lambda b: b.replace(b'"random_n": true', b'"random_n": false')),
            ("workers/Worker0.json", lambda b: b.replace(b'"rounds": 3000', b'"rounds": 2999')),
            ("workers/Worker0.txt", lambda b: b.replace(b"SUCCESS", b"FAIL")),
        ]
        for name, corrupt in cases:
            path = folder / name
            original = path.read_bytes()
            with self.subTest(file=name):
                try:
                    path.write_bytes(corrupt(original))
                    with self.assertRaises(ValueError):
                        verify_run(folder, team=9, distributed=True)
                finally:
                    path.write_bytes(original)
        path = folder / "frames/frame3000.txt"
        original = path.read_bytes()
        try:
            path.unlink()
            with self.assertRaises(ValueError):
                verify_run(folder, team=9, distributed=True)
        finally:
            path.write_bytes(original)

    def test_two_runs_with_same_n_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "different N"):
            verify_all(self.runs[0], self.runs[1], self.runs[1], 9, self.root / "bad")


if __name__ == "__main__":
    unittest.main()
