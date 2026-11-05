"""Strict LF-framed TCP messages and reproducible ASCII board files."""
import hashlib
import socket
from datetime import datetime, timezone
from pathlib import Path

WIDTH, HEIGHT, ROUNDS = 160, 80, 3000


def board_bytes(rows):
    if len(rows) != HEIGHT:
        raise ValueError('board must have 80 rows')
    for row in rows:
        validate_row(row)
    return ('\n'.join(rows) + '\n').encode('ascii')


def validate_row(row):
    if len(row) != WIDTH or any(not 32 <= ord(c) <= 126 for c in row):
        raise ValueError('board row must contain exactly 160 printable ASCII characters')
    return row


def read_board(path):
    data = Path(path).read_bytes()
    rows = data.decode('ascii').split('\n')
    if len(rows) != HEIGHT + 1 or rows[-1] != '' or board_bytes(rows[:-1]) != data:
        raise ValueError(f'{path}: expected 80 x 160 ASCII with final LF (12880 bytes)')
    return rows[:-1]


def hash8(data):
    return hashlib.sha256(data).hexdigest()[:8]


class Wire:
    """One reader per socket. Preserve spaces; bound incomplete/oversize lines."""
    def __init__(self, sock):
        self.sock = sock
        self.buffer = bytearray()
        self.sent = self.received = 0
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

    def send(self, lines):
        data = ('\n'.join(lines) + '\n').encode('ascii')
        self.sock.sendall(data)
        self.sent += len(data)

    def line(self):
        while b'\n' not in self.buffer:
            if len(self.buffer) > 1024:
                raise ValueError('protocol line too long')
            chunk = self.sock.recv(65536)
            if not chunk:
                raise EOFError('peer disconnected')
            self.buffer.extend(chunk)
        end = self.buffer.index(10)
        if end > 1024:
            raise ValueError('protocol line too long')
        raw = bytes(self.buffer[:end])
        del self.buffer[:end + 1]
        self.received += end + 1
        return raw.decode('ascii')

    def rows(self, count):
        return [validate_row(self.line()) for _ in range(count)]


class Log:
    """UTC wall time for evidence; elapsed measurements use perf_counter."""
    def __init__(self, path, node):
        self.node = node
        self.file = Path(path).open('w', encoding='utf-8', newline='\n')

    def write(self, event, status, message, timestamp=None):
        # A Worker learns its log filename only after ASSIGN; preserve the
        # actual connection timestamp when replaying that earlier event.
        stamp = (timestamp or datetime.now(timezone.utc)).strftime('%H:%M:%S.%f')[:-3]
        self.file.write(f'[{stamp}] {self.node} | {event} | {status} | {message}\n')
        self.file.flush()

    def close(self):
        self.file.close()
