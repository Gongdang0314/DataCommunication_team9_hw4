"""G9 Worker: one process, one thread, only its own band and two halo rows.

Assigner에 TCP로 접속해서 자기가 맡은 띠(band)만 계산하고 결과를 돌려보낸다.
프로세스 하나, 스레드 하나 — 다른 Worker와 직접 통신하지 않고 Assigner를 거친다.
"""
import argparse
import json
import socket
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from common import Log, Wire
from myrules import band, repaint, rule1_cell, rule2_cell, rule3_cell, to_brian, to_cyclic


def run(args):
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    sock = socket.create_connection((args.host, args.port), timeout=args.timeout)
    connected_at = datetime.now(timezone.utc)
    log = None
    try:
        wire = Wire(sock)
        wire.send(['HELLO'])
        command = wire.line().split()
        if len(command) != 6 or command[0] != 'ASSIGN':
            raise ValueError('expected ASSIGN k N y0 y1 team')
        k, n, y0, y1, team = map(int, command[1:])
        # Assigner가 결정한 N을 신뢰 — 하드코딩 집합 대신 범위만 검증
        # (교수가 N=2,3 등으로 테스트해도 거부하지 않도록)
        if not (1 <= n <= 80 and 0 <= k < n and
                y0 == 80*k//n and y1 == 80*(k+1)//n and team > 0):
            raise ValueError('invalid band assignment')
        h = y1 - y0  # 이 Worker가 담당하는 실제 행 수
        log = Log(out / f'Worker{k}.txt', f'WORKER{k}')
        log.write('CONNECT', 'SUCCESS', f'host={args.host} port={args.port} timezone=UTC',
                  timestamp=connected_at)
        log.write('ASSIGN', 'SUCCESS', f'k={k} N={n} rows=[{y0},{y1}) h={h} team={team}')
        # 작업판 구조: [위Halo 1줄] + [자기 띠 h줄] + [아래Halo 1줄]
        # 초기 Halo는 빈 줄로 채움 — 첫 ROUND에서 Assigner가 보내줄 것
        w = [list(' ' * 160)] + [list(row) for row in wire.rows(h)] + [list(' '*160)]
        # canvas1, canvas2는 Halo 포함 h+2줄을 받음 (repaint 때 경계도 덧칠해야 하므로)
        c1 = [list(row) for row in wire.rows(h+2)]
        c2 = [list(row) for row in wire.rows(h+2)]
        elapsed = []
        for r in range(3000):
            if wire.line() != f'ROUND {r}':
                raise ValueError(f'expected ROUND {r}')
            # Assigner가 보내준 새 Halo 2줄(위, 아래)로 교체
            w[0], w[-1] = [list(row) for row in wire.rows(2)]
            started = time.perf_counter()
            # r=1000: Rule1→Rule2 전환. 캔버스1 덧칠 후 Brian 상태로 변환
            # r=2000: Rule2→Rule3 전환. 캔버스2 덧칠 후 Cyclic 초기화
            # 덧칠은 Halo까지 포함해야 경계 칸 계산이 올바르다
            if r == 1000:
                repaint(w, c1)
                to_brian(w)
                log.write('REPAINT', 'INFO', 'r=1000 canvas1 + brian, including halo')
            elif r == 2000:
                repaint(w, c2)
                # (y0-1)%80 = 위 Halo의 전체 보드 y좌표
                to_cyclic(w, (y0-1) % 80, team)
                log.write('REPAINT', 'INFO', f'r=2000 canvas2 + cyclic team={team}, including halo')
            # r//1000으로 현재 구간의 규칙을 선택: 0→rule1, 1→rule2, 2→rule3
            middle = band(w, (rule1_cell, rule2_cell, rule3_cell)[r//1000])
            w = [w[0]] + middle + [w[-1]]
            # 매 라운드: 첫 줄, 끝 줄 전송 (Halo 교환용)
            # 10라운드마다: 전체 띠도 추가 전송 (프레임 저장용)
            lines = [f'RESULT {r} {k}', ''.join(w[1]), ''.join(w[h])]
            if (r+1) % 10 == 0:
                lines.extend(''.join(row) for row in w[1:h+1])
            wire.send(lines)
            elapsed.append(time.perf_counter() - started)
            if (r+1) % 100 == 0:
                recent = elapsed[-100:]
                log.write('ROUND', 'INFO', f'r={r-99}..{r} avg_compute_ms={sum(recent)/100*1000:.3f} max_compute_ms={max(recent)*1000:.3f}')
                log.write('RESULT', 'SUCCESS', f'r={r} k={k} sent rounds={r+1}')
        if wire.line() != 'BYE':
            raise ValueError('expected BYE after 3000 rounds')
        summary = dict(k=k, n=n, team=team, height=h, rounds=3000,
                       avg_compute_ms=sum(elapsed)/len(elapsed)*1000,
                       max_compute_ms=max(elapsed)*1000)
        (out / f'Worker{k}.json').write_text(json.dumps(summary, indent=2)+'\n', encoding='utf-8')
        log.write('TERMINATE', 'SUCCESS', f'BYE rounds=3000 avg_compute_ms={summary["avg_compute_ms"]:.3f}')
    except Exception as exc:
        if log:
            log.write('TERMINATE', 'FAIL', str(exc))
        raise
    finally:
        sock.close()
        if log:
            log.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', required=True)
    parser.add_argument('--port', type=int, default=9000)
    parser.add_argument('--out', default='runs/workers')
    parser.add_argument('--timeout', type=float, default=120)
    try:
        run(parser.parse_args())
    except Exception as exc:
        print(f'Worker FAIL: {exc}', file=sys.stderr)
        sys.exit(1)
