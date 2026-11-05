"""Independent expected results from the professor's HW4_student_pack.

Fixtures are unmodified teaching materials from 1_rule_test_kit; G11_canvas0
is 3_G11_sample/canvas0.txt. They are verification inputs, not G9 submissions.
Run from the repository root: python -m unittest discover -s tests -v
"""
import hashlib
from pathlib import Path
import unittest

import myrules as rules

FIXTURES = Path(__file__).parent / "fixtures"
KIT = FIXTURES / "rule_test_kit"


def read_board(path):
    return [list(row.decode("ascii")) for row in path.read_bytes().splitlines()]


def serialize(board):
    return ("".join("".join(row) + "\n" for row in board)).encode("ascii")


class OfficialRuleTests(unittest.TestCase):
    def test_all_embedded_official_cases(self):
        lines = (KIT / "tests.txt").read_text(encoding="utf-8").splitlines()
        count = 0
        for start, line in enumerate(lines):
            if not line.startswith("TEST "):
                continue
            _, name, number, rounds = line.split()[:4]
            out = lines.index("OUT", start)
            end = lines.index("END", out)
            board = [list(row.replace("·", " ")) for row in lines[start + 2:out]]
            expected = [list(row.replace("·", " ")) for row in lines[out + 1:end]]
            rule = getattr(rules, "rule" + number)
            with self.subTest(case=name):
                for _ in range(int(rounds)):
                    board = rule(board)
                self.assertEqual(board, expected)
            count += 1
        self.assertEqual(count, 10)

    def test_official_answer_files_byte_for_byte(self):
        for number, checkpoints in ((1, (1, 2, 3, 10)), (2, (1, 2, 3)),
                                    (3, (1, 2, 10))):
            board = read_board(KIT / f"rule{number}_input.txt")
            rule = getattr(rules, f"rule{number}")
            for r in range(1, max(checkpoints) + 1):
                board = rule(board)
                if r in checkpoints:
                    with self.subTest(rule=number, round=r):
                        self.assertEqual(serialize(board),
                                         (KIT / f"rule{number}_output_R{r}.txt").read_bytes())

    def test_rule1_does_not_update_input_in_place(self):
        board = read_board(KIT / "rule1_input.txt")
        before = serialize(board)
        result = rules.rule1(board)
        self.assertEqual(serialize(board), before)
        self.assertNotEqual(serialize(result),
                            (KIT / "rule1_WRONG_inplace_R1.txt").read_bytes())

    def test_repaint_and_brian_transition(self):
        board = read_board(KIT / "repaint_S1000.txt")
        rules.repaint(board, read_board(KIT / "repaint_canvas1.txt"))
        self.assertEqual(serialize(board), (KIT / "repaint_step1_painted.txt").read_bytes())
        rules.to_brian(board)
        self.assertEqual(serialize(board), (KIT / "repaint_step2_brian.txt").read_bytes())
        board = rules.rule2(board)
        self.assertEqual(serialize(board), (KIT / "repaint_step3_R1000.txt").read_bytes())

    def test_cyclic_conversion_global_coordinates(self):
        board = read_board(KIT / "cyclic_convert_input.txt")
        rules.to_cyclic(board, 25, 11)
        self.assertEqual(serialize(board),
                         (KIT / "cyclic_convert_output_y25_team11.txt").read_bytes())

    def test_cyclic_conversion_wraps_halo_and_uses_team9(self):
        board = [list(" _@"), list(" _@"), list(" _@")]
        rules.to_cyclic(board, 79, 9)
        # Global rows are 79, 0, 1, not local work rows 0, 1, 2.
        self.assertEqual(board, [list("*+@"), list("@*@"), list(": @")])

    def test_official_three_bands_include_halos(self):
        output = []
        for k in range(3):
            with self.subTest(worker=k):
                board = read_board(KIT / f"band_N3_W{k}_work.txt")
                result = rules.band(board, rules.rule1_cell)
                self.assertEqual(serialize(result),
                                 (KIT / f"band_N3_W{k}_output.txt").read_bytes())
                output.extend(result)
        self.assertEqual(serialize(output), (KIT / "rule1_output_R1.txt").read_bytes())

    def test_sample_g11_first_round_known_hash(self):
        board = read_board(FIXTURES / "G11_canvas0.txt")
        self.assertEqual(hashlib.sha256(serialize(board)).hexdigest()[:8], "74aebc0f")
        result = rules.rule1(board)
        self.assertEqual(hashlib.sha256(serialize(result)).hexdigest()[:8], "2d651c01")


if __name__ == "__main__":
    unittest.main()
