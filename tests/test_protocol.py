"""TCP framing and failure cleanup; no cloud or 3,000-round run required."""
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from common import Wire


class FragmentSocket:
    """Deliver fixed recv fragments, including multiple lines in one fragment."""
    def __init__(self, fragments):
        self.fragments = iter(fragments)
        self.sent = b''

    def setsockopt(self, *args):
        pass

    def recv(self, size):
        return next(self.fragments, b'')

    def sendall(self, data):
        self.sent += data


class WireTests(unittest.TestCase):
    def test_fragmented_commands_and_coalesced_rows_preserve_spaces(self):
        row1, row2 = ' ' * 159 + '@', '#' + ' ' * 159
        data = ('ROUND 17\n' + row1 + '\n' + row2 + '\n').encode('ascii')
        wire = Wire(FragmentSocket([data[:2], data[2:8], data[8:40], data[40:]]))
        self.assertEqual(wire.line(), 'ROUND 17')
        self.assertEqual(wire.rows(2), [row1, row2])
        self.assertEqual(wire.received, len(data))

    def test_send_adds_exactly_one_lf_per_line(self):
        sock = FragmentSocket([])
        wire = Wire(sock)
        wire.send(['HELLO', ' ' * 160])
        self.assertEqual(sock.sent, b'HELLO\n' + b' ' * 160 + b'\n')
        self.assertEqual(wire.sent, len(sock.sent))

    def test_rejects_oversized_line_with_or_without_lf(self):
        for suffix in (b'', b'\n'):
            with self.subTest(suffix=suffix):
                with self.assertRaisesRegex(ValueError, 'too long'):
                    Wire(FragmentSocket([b'A' * 1025 + suffix])).line()

    def test_rejects_non_ascii_and_invalid_row_format(self):
        with self.assertRaises(UnicodeDecodeError):
            Wire(FragmentSocket([b'\xff\n'])).line()
        for row in (b' ' * 159, b' ' * 160 + b'\r', b' ' * 159 + b'\t'):
            with self.subTest(row=row):
                with self.assertRaises(ValueError):
                    Wire(FragmentSocket([row + b'\n'])).rows(1)

    def test_incomplete_line_disconnect_is_not_silently_accepted(self):
        with self.assertRaises(EOFError):
            Wire(FragmentSocket([b'ROUND 2'])).line()


class AssignerFailureTests(unittest.TestCase):
    def check_failure(self, mode, expected_error):
        with tempfile.TemporaryDirectory(prefix='hw4-protocol-') as folder:
            temporary = Path(folder)
            canvas = temporary / 'canvas'
            canvas.mkdir()
            # These transport-only fixtures intentionally contain no artwork.
            # Content/ratio validation is independently covered by canvas tools.
            for i in range(3):
                (canvas / f'canvas{i}.txt').write_bytes((b' ' * 160 + b'\n') * 80)
            with socket.socket() as reservation:
                reservation.bind(('127.0.0.1', 0))
                port = reservation.getsockname()[1]
            output = temporary / 'run'
            transcript = temporary / 'console.txt'
            sock, reader, process = None, None, None
            with transcript.open('wb') as console:
                try:
                    process = subprocess.Popen(
                        [sys.executable, str(ROOT / 'assigner.py'), '--host', '127.0.0.1',
                         '--port', str(port), '--team', '9', '--canvas', str(canvas),
                         '--out', str(output), '--n', '1', '--timeout', '2'],
                        cwd=ROOT, stdout=console, stderr=console)
                    deadline = time.monotonic() + 5
                    while 'READY' not in transcript.read_text(encoding='utf-8'):
                        if process.poll() is not None or time.monotonic() > deadline:
                            self.fail('Assigner failed to become ready: ' + transcript.read_text())
                        time.sleep(0.02)
                    sock = socket.create_connection(('127.0.0.1', port), timeout=5)
                    sock.sendall(b'HELLO\n')
                    reader = sock.makefile('rb')
                    self.assertEqual(reader.readline(), b'ASSIGN 0 1 0 80 9\n')
                    for _ in range(80 + 82 + 82):
                        self.assertEqual(reader.readline(), b' ' * 160 + b'\n')
                    self.assertEqual(reader.readline(), b'ROUND 0\n')
                    reader.readline()
                    reader.readline()
                    if mode == 'bad_round':
                        sock.sendall(b'RESULT 1 0\n')
                    elif mode == 'disconnect':
                        reader.close()
                        sock.close()
                    # timeout case deliberately sends no RESULT.
                    self.assertEqual(process.wait(timeout=6), 1)
                    log = (output / 'Assigner.txt').read_text(encoding='utf-8')
                    self.assertIn('TERMINATE | FAIL', log)
                    self.assertIn(expected_error, log)
                    self.assertNotIn('TERMINATE | SUCCESS', log)
                finally:
                    if reader is not None:
                        reader.close()
                    if sock is not None:
                        sock.close()
                    if process is not None and process.poll() is None:
                        process.kill()
                        process.wait(timeout=5)

    def test_wrong_round_fails_without_deadlock(self):
        self.check_failure('bad_round', 'expected RESULT 0 0')

    def test_disconnect_fails_without_deadlock(self):
        self.check_failure('disconnect', 'peer disconnected')

    def test_receive_timeout_fails_without_deadlock(self):
        self.check_failure('timeout', 'timed out')


if __name__ == '__main__':
    unittest.main()
