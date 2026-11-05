"""Strict LF-framed TCP messages and reproducible ASCII board files.

Assigner와 Worker가 공통으로 쓰는 TCP 프로토콜 유틸리티.
메시지 경계를 LF(\n)로 구분하고, 보드 파일도 동일한 LF 규격을 따른다.
"""
import hashlib
import socket
from datetime import datetime, timezone
from pathlib import Path

# 보드 크기와 총 라운드 수 — 과제 명세 고정값
WIDTH, HEIGHT, ROUNDS = 160, 80, 3000


def board_bytes(rows):
    """80행 × 160열 보드를 LF로 이은 12,880바이트 ASCII로 변환.

    Windows CRLF나 trailing space가 섞이면 해시가 달라지므로
    반드시 이 함수로 통일해서 저장해야 한다.
    """
    if len(rows) != HEIGHT:
        raise ValueError('board must have 80 rows')
    for row in rows:
        validate_row(row)
    return ('\n'.join(rows) + '\n').encode('ascii')


def validate_row(row):
    """한 줄이 정확히 160자의 출력 가능 ASCII인지 검증.

    오른쪽 공백도 그림의 일부이므로 strip()하면 안 된다.
    """
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
    """소켓 1개에 대한 LF 기반 메시지 읽기/쓰기.

    TCP는 스트림이라 recv() 한 번에 메시지 하나가 온다는 보장이 없다.
    예를 들어 "ROUND 0\n<halo1>\n<halo2>\n"이 한 번에 올 수도,
    "ROUND 0\n<halo"까지만 오고 나머지가 다음 recv()에 올 수도 있다.
    그래서 내부 버퍼에 쌓아두고 LF를 찾아 한 줄씩 잘라 쓴다.
    """
    def __init__(self, sock):
        self.sock = sock
        self.buffer = bytearray()
        self.sent = self.received = 0
        # Nagle 알고리즘을 끄면 작은 패킷도 즉시 전송 → 라운드 동기화 지연 감소
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

    def send(self, lines):
        """여러 줄을 LF로 이어 한 번에 전송. sendall()은 끝까지 보내줌."""
        data = ('\n'.join(lines) + '\n').encode('ascii')
        self.sock.sendall(data)
        self.sent += len(data)

    def line(self):
        """버퍼에서 LF까지 한 줄을 잘라 반환. LF가 없으면 recv()를 더 한다.

        보드 행(160자)은 LF 포함 161바이트 — 1024 제한에 안 걸린다.
        프로토콜 명령("ROUND 0" 등)은 훨씬 짧다.
        """
        while b'\n' not in self.buffer:
            if len(self.buffer) > 1024:
                raise ValueError('protocol line too long')
            chunk = self.sock.recv(65536)
            if not chunk:
                raise EOFError('peer disconnected')
            self.buffer.extend(chunk)
        end = self.buffer.index(10)  # 10 = LF의 ASCII 코드
        if end > 1024:
            raise ValueError('protocol line too long')
        raw = bytes(self.buffer[:end])
        del self.buffer[:end + 1]   # 읽은 줄 + LF를 버퍼에서 제거
        self.received += end + 1
        return raw.decode('ascii')

    def rows(self, count):
        return [validate_row(self.line()) for _ in range(count)]


class Log:
    """UTC 시각을 기록하는 로그. 증거용 시각은 wall clock, 성능 측정은 perf_counter."""
    def __init__(self, path, node):
        self.node = node
        # newline='\n' → Windows에서도 CRLF가 아닌 LF만 기록
        self.file = Path(path).open('w', encoding='utf-8', newline='\n')

    def write(self, event, status, message, timestamp=None):
        # A Worker learns its log filename only after ASSIGN; preserve the
        # actual connection timestamp when replaying that earlier event.
        stamp = (timestamp or datetime.now(timezone.utc)).strftime('%H:%M:%S.%f')[:-3]
        self.file.write(f'[{stamp}] {self.node} | {event} | {status} | {message}\n')
        self.file.flush()

    def close(self):
        self.file.close()
