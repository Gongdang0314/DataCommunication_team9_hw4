"""TCP star coordinator: Main + N persistent Handlers, one lock and two CVs."""
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
    n = args.n if args.n is not None else random.SystemRandom().randint(4, 8)
    canvases = [read_board(Path(args.canvas) / f'canvas{i}.txt') for i in range(3)]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if any(out.iterdir()):
        raise ValueError('output directory must be empty (preserve earlier evidence)')
    (out/'frames').mkdir()
    log = Log(out/'Assigner.txt', 'ASSIGNER')
    rh = (out/'RoundHash.txt').open('w', encoding='ascii', newline='\n')
    bounds = [80*k//n for k in range(n+1)]
    m = threading.Lock()
    done_cv, go_cv = threading.Condition(m), threading.Condition(m)
    state = dict(round=0, arrived=0, error=None)
    edges = [(canvases[0][bounds[k]], canvases[0][bounds[k+1]-1]) for k in range(n)]
    halo = [(edges[(k-1)%n][1], edges[(k+1)%n][0]) for k in range(n)]
    frame = list(canvases[0])
    arrivals, traffic = [0.0]*n, [0]*n
    wires, handlers, addresses = [], [], []
    history = []
    listener = socket.socket()
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.settimeout(args.timeout)

    def save(r, rows):
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
        wire = wires[k]
        try:
            for r in range(3000):
                with m:
                    if state['error']:
                        return
                    top, bottom = halo[k]
                before = wire.sent + wire.received
                wire.send([f'ROUND {r}', top, bottom])
                if wire.line() != f'RESULT {r} {k}':
                    raise ValueError(f'expected RESULT {r} {k}')
                first, last = wire.rows(2)
                rows = wire.rows(bounds[k+1]-bounds[k]) if (r+1)%10 == 0 else None
                if rows is not None and (rows[0] != first or rows[-1] != last):
                    raise ValueError('RESULT edges differ from its full band')
                with m:
                    edges[k] = (first, last)
                    if rows is not None:
                        frame[bounds[k]:bounds[k+1]] = rows
                    arrivals[k] = time.perf_counter()
                    traffic[k] = wire.sent + wire.received - before
                    state['arrived'] += 1
                    if state['arrived'] == n:
                        done_cv.notify()
                    while state['round'] == r and not state['error']:
                        go_cv.wait()
                    if state['error']:
                        return
            wire.send(['BYE'])
        except Exception as exc:
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
            ext1 = [canvases[1][y%80] for y in range(y0-1, y1+1)]
            ext2 = [canvases[2][y%80] for y in range(y0-1, y1+1)]
            wire.send([f'ASSIGN {k} {n} {y0} {y1} {args.team}'] + canvases[0][y0:y1] + ext1 + ext2)
            log.write('ASSIGN', 'SUCCESS', f'k={k} rows=[{y0},{y1}) h={y1-y0} sent_rows={3*(y1-y0)+4}')
        listener.close()
        # These are the only threads created by the Assigner.
        handlers = [threading.Thread(target=handler, args=(k,), name=f'Handler{k}') for k in range(n)]
        started = round_start = time.perf_counter()
        for thread in handlers:
            thread.start()
        for r in range(3000):
            with m:
                while state['arrived'] < n and not state['error']:
                    done_cv.wait()
                if state['error']:
                    raise RuntimeError(state['error'])
                end = time.perf_counter()
                history.append(dict(round=r, seconds=end-round_start,
                                    wait=max(arrivals)-min(arrivals),
                                    slowest=max(range(n), key=arrivals.__getitem__), bytes=sum(traffic)))
                for k in range(n):
                    halo[k] = (edges[(k-1)%n][1], edges[(k+1)%n][0])
                snapshot = list(frame) if (r+1)%10 == 0 else None
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
        # Wake handlers blocked in recv, then join before returning failure.
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
