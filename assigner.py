"""TCP star coordinator: Main + N persistent Handlers, one lock and two CVs.

별(Star) 토폴로지: Worker끼리는 통신하지 않고 모두 Assigner를 거친다.
Main 스레드가 Barrier를 관리하고, Handler 스레드 N개가 각 Worker와 1:1 통신.
동기화: Mutex 1개 + Condition Variable 2개(done_cv, go_cv).
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import random
import socket
import sys
import threading
import time

from common import Log, Wire, board_bytes, hash8, read_board


def run(args):
    # --n을 생략하면 4~8 중 랜덤 선택 (과제 요구: 제출 실행은 랜덤)
    n = args.n if args.n is not None else random.SystemRandom().randint(4, 8)
    canvases = [read_board(Path(args.canvas) / f'canvas{i}.txt') for i in range(3)]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if any(out.iterdir()):
        raise ValueError('output directory must be empty (preserve earlier evidence)')
    (out/'frames').mkdir()
    log = Log(out/'Assigner.txt', 'ASSIGNER')
    rh = (out/'RoundHash.txt').open('w', encoding='ascii', newline='\n')
    # bounds[k]는 Worker k의 시작 행, bounds[k+1]은 끝 행(exclusive)
    # 정수 나눗셈으로 행을 최대한 균등하게 분배 (예: 80행÷6 = 13,13,14,13,14,13)
    bounds = [80*k//n for k in range(n+1)]
    # Mutex 하나를 done_cv와 go_cv가 공유 — wait()은 Lock을 풀고, 깨어나면 다시 잡음
    m = threading.Lock()
    done_cv, go_cv = threading.Condition(m), threading.Condition(m)
    state = dict(round=0, arrived=0, error=None)
    # edges[k] = (Worker k의 첫 행, 끝 행) — Halo 교환의 원본
    edges = [(canvases[0][bounds[k]], canvases[0][bounds[k+1]-1]) for k in range(n)]
    # halo[k] = (위 이웃의 끝 행, 아래 이웃의 첫 행) — 토러스 연결
    # k=0의 위 이웃은 k=N-1, k=N-1의 아래 이웃은 k=0 (원형 wrap)
    halo = [(edges[(k-1)%n][1], edges[(k+1)%n][0]) for k in range(n)]
    frame = list(canvases[0])
    arrivals, traffic = [0.0]*n, [0]*n
    wires, handlers, addresses = [], [], []
    history = []
    listener = socket.socket()
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.settimeout(args.timeout)

    def save(r, rows):
        """프레임 저장(10라운드마다) + 라운드 파일·해시 저장(100라운드마다)."""
        data = board_bytes(rows)
        (out/'frames'/f'frame{r:04d}.txt').write_bytes(data)
        if r % 100 == 0:
            name = f'round{r:04d}.txt'
            (out/name).write_bytes(data)
            digest = hash8(data)
            rh.write(f'{name} {digest}\n')
            rh.flush()
            log.write('SAVE', 'SUCCESS', f'{name} 12880B hash={digest}')

    def handler(k):
        """Handler k: Worker k와 1:1로 Halo 전송 → 결과 수신 → Barrier 대기를 반복."""
        wire = wires[k]
        try:
            for r in range(3000):
                # ── 1단계: Lock 안에서 이번 라운드의 Halo를 읽어 둔다 ──
                with m:
                    if state['error']:
                        return
                    top, bottom = halo[k]
                # ── 2단계: 네트워크 송수신은 Lock 밖에서 (Lock 잡고 recv하면 교착) ──
                before = wire.sent + wire.received
                wire.send([f'ROUND {r}', top, bottom])
                if wire.line() != f'RESULT {r} {k}':
                    raise ValueError(f'expected RESULT {r} {k}')
                first, last = wire.rows(2)
                rows = wire.rows(bounds[k+1]-bounds[k]) if (r+1)%10 == 0 else None
                if rows is not None and (rows[0] != first or rows[-1] != last):
                    raise ValueError('RESULT edges differ from its full band')
                # ── 3단계: Lock 안에서 공유 상태 갱신 + Barrier ──
                with m:
                    edges[k] = (first, last)
                    if rows is not None:
                        frame[bounds[k]:bounds[k+1]] = rows
                    arrivals[k] = time.perf_counter()
                    traffic[k] = wire.sent + wire.received - before
                    state['arrived'] += 1
                    # 마지막 도착이면 Main을 깨운다
                    if state['arrived'] == n:
                        done_cv.notify()
                    # Main이 다음 라운드를 열 때까지 대기
                    # while: spurious wakeup 방지 — 깨어나도 조건을 다시 확인
                    while state['round'] == r and not state['error']:
                        go_cv.wait()
                    if state['error']:
                        return
            wire.send(['BYE'])
        except Exception as exc:
            # 에러 발생 시 다른 스레드들도 깨워서 종료시킨다
            with m:
                if not state['error']:
                    state['error'] = f'Worker{k}: {type(exc).__name__}: {exc}'
                done_cv.notify()
                go_cv.notify_all()

    try:
        listener.bind((args.host, args.port))
        listener.listen(n)
        metadata = dict(team=args.team, n=n, random_n=args.n is None,
                        bands=bounds, timezone='UTC', port=args.port)
        (out/'run.json').write_text(json.dumps(metadata, indent=2)+'\n', encoding='utf-8')
        log.write('INIT', 'SUCCESS', f'N={n} bands={bounds} team={args.team} random_n={args.n is None} listen={args.host}:{args.port} timezone=UTC')
        save(0, frame)
        print(f'READY N={n} TEAM={args.team} port={args.port}', flush=True)
        for k in range(n):
            sock, addr = listener.accept()
            sock.settimeout(args.timeout)
            wire = Wire(sock)
            wires.append(wire)
            addresses.append(addr[0])
            if wire.line() != 'HELLO':
                raise ValueError('expected HELLO')
            log.write('CONNECT', 'SUCCESS', f'k={k} peer={addr[0]}:{addr[1]} ({k+1}/{n})')
        for k, wire in enumerate(wires):
            y0, y1 = bounds[k:k+2]
            # canvas1·2는 Halo 포함(y0-1 ~ y1)이므로 y%80으로 토러스 wrap
            ext1 = [canvases[1][y%80] for y in range(y0-1, y1+1)]
            ext2 = [canvases[2][y%80] for y in range(y0-1, y1+1)]
            # ASSIGN 명령 + canvas0 h줄 + canvas1 h+2줄 + canvas2 h+2줄을 한 번에 전송
            wire.send([f'ASSIGN {k} {n} {y0} {y1} {args.team}'] + canvases[0][y0:y1] + ext1 + ext2)
            log.write('ASSIGN', 'SUCCESS', f'k={k} rows=[{y0},{y1}) h={y1-y0} sent_rows={3*(y1-y0)+4}')
        listener.close()
        # These are the only threads created by the Assigner.
        handlers = [threading.Thread(target=handler, args=(k,), name=f'Handler{k}') for k in range(n)]
        started = round_start = time.perf_counter()
        for thread in handlers:
            thread.start()
        # ── Main 루프: 3000라운드 Barrier 관리 ──
        for r in range(3000):
            with m:
                # N개 결과가 모두 도착할 때까지 대기
                while state['arrived'] < n and not state['error']:
                    done_cv.wait()
                if state['error']:
                    raise RuntimeError(state['error'])
                end = time.perf_counter()
                history.append(dict(round=r, seconds=end-round_start,
                                    wait=max(arrivals)-min(arrivals),
                                    slowest=max(range(n), key=arrivals.__getitem__), bytes=sum(traffic)))
                # 새 edges로부터 다음 라운드의 Halo를 조립
                for k in range(n):
                    halo[k] = (edges[(k-1)%n][1], edges[(k+1)%n][0])
                snapshot = list(frame) if (r+1)%10 == 0 else None
                # 다음 라운드 시작: arrived 초기화 후 Handler들을 깨움
                state['arrived'] = 0
                state['round'] = r+1
                round_start = time.perf_counter()
                go_cv.notify_all()
            # All filesystem writes and log writes occur outside m.
            if snapshot is not None:
                save(r+1, snapshot)
            if (r+1)%100 == 0:
                block = history[-100:]
                slowest, count = Counter(x['slowest'] for x in block).most_common(1)[0]
                normal_bytes = sum(x['bytes'] for x in block if (x['round']+1)%10) / 90
                full_bytes = sum(x['bytes'] for x in block if (x['round']+1)%10 == 0) / 10
                log.write('ROUND', 'INFO', f'r={r-99}..{r} complete')
                log.write('RESULT', 'SUCCESS', f'r={r-99}..{r} received={100*n} verified r,k,rows')
                log.write('BARRIER', 'INFO', f'r={r-99}..{r} avg_round_ms={sum(x["seconds"] for x in block)*10:.3f} max_round_ms={max(x["seconds"] for x in block)*1000:.3f} avg_wait_ms={sum(x["wait"] for x in block)*10:.3f} max_wait_ms={max(x["wait"] for x in block)*1000:.3f} slowest=W{slowest}({count}/100) normal_bytes_avg={normal_bytes:.3f} full_bytes_avg={full_bytes:.3f}')
                print(f'PROGRESS G{args.team} N={n} round={r+1}/3000 elapsed={end-started:.3f}s', flush=True)
            if r+1 in (1000, 2000):
                log.write('REPAINT', 'INFO', f'r={r+1} workers apply canvas{(r+1)//1000} + conversion including halos; saved board is before repaint')
        for thread in handlers:
            thread.join()
        if state['error']:
            raise RuntimeError(state['error'])
        total = end - started
        summary = dict(**metadata, rounds=3000, elapsed_seconds=total, rounds_per_second=3000/total,
                       avg_round_ms=sum(x['seconds'] for x in history)/3,
                       max_round_ms=max(x['seconds'] for x in history)*1000,
                       avg_wait_ms=sum(x['wait'] for x in history)/3,
                       max_wait_ms=max(x['wait'] for x in history)*1000,
                       slowest_counts=dict(Counter(x['slowest'] for x in history)),
                       normal_bytes_avg=sum(x['bytes'] for x in history if (x['round']+1)%10)/2700,
                       full_bytes_avg=sum(x['bytes'] for x in history if (x['round']+1)%10 == 0)/300,
                       worker_addresses=addresses)
        (out/'summary.json').write_text(json.dumps(summary, indent=2)+'\n', encoding='utf-8')
        (out/'metrics.json').write_text(json.dumps(history)+'\n', encoding='utf-8')
        log.write('TERMINATE', 'SUCCESS', json.dumps(summary, separators=(',', ':')))
        print(f'PASS G{args.team} N={n} 3000 rounds {total:.3f}s', flush=True)
    except Exception as exc:
        with m:
            state['error'] = str(exc)
            go_cv.notify_all()
            done_cv.notify_all()
        # recv()에서 블로킹된 Handler를 깨우려면 소켓을 shutdown해야 한다
        # close()만 하면 다른 스레드의 recv()가 바로 안 깨어날 수 있음
        for wire in wires:
            try:
                wire.sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
        for thread in handlers:
            if thread.ident is not None:
                thread.join()
        log.write('TERMINATE', 'FAIL', str(exc))
        raise
    finally:
        listener.close()
        for wire in wires:
            wire.sock.close()
        rh.close()
        log.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', default='0.0.0.0')
    parser.add_argument('--port', type=int, default=9000)
    parser.add_argument('--team', type=int, required=True)
    parser.add_argument('--canvas', default='canvas')
    parser.add_argument('--out', required=True)
    parser.add_argument('--n', type=int, choices=[1, 4, 5, 6, 7, 8], help='development/baseline only; omit for submission')
    parser.add_argument('--timeout', type=float, default=120)
    args = parser.parse_args()
    if args.team <= 0:
        parser.error('--team must be positive')
    try:
        run(args)
    except Exception as exc:
        print(f'Assigner FAIL: {exc}', file=sys.stderr)
        sys.exit(1)
