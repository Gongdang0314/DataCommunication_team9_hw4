"""Launch N local Worker processes without visible console windows."""
import argparse
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def launch(host, port, n, out):
    out = Path(out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    if any(out.iterdir()):
        raise ValueError('worker output directory must be empty')
    processes, files = [], []
    try:
        for i in range(n):
            log = (out/f'process{i}.log').open('w', encoding='utf-8')
            files.append(log)
            processes.append(subprocess.Popen([sys.executable, str(ROOT/'worker.py'),
                '--host', host, '--port', str(port), '--out', str(out)],
                stdout=log, stderr=subprocess.STDOUT))
        codes = [p.wait() for p in processes]
        if any(codes):
            raise RuntimeError(f'Worker exit codes {codes}; see {out}/process*.log')
        print(f'PASS: {n} Worker processes completed', flush=True)
    finally:
        for p in processes:
            if p.poll() is None:
                p.terminate()
                p.wait()
        for f in files:
            f.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', required=True)
    parser.add_argument('--port', type=int, default=9000)
    parser.add_argument('--n', type=int, choices=[1,4,5,6,7,8], required=True)
    parser.add_argument('--out', required=True)
    a = parser.parse_args()
    launch(a.host, a.port, a.n, a.out)
