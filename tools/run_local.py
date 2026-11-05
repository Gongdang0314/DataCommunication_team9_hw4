"""Reproducible local TCP smoke/integration run; never submission remote evidence."""
import argparse
from pathlib import Path
import subprocess
import sys
from run_workers import launch

ROOT = Path(__file__).resolve().parents[1]

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--n', type=int, choices=[1,4,5,6,7,8], required=True)
    parser.add_argument('--team', type=int, default=9)
    parser.add_argument('--port', type=int, default=9000)
    parser.add_argument('--canvas', default=str(ROOT/'canvas'))
    parser.add_argument('--out', required=True)
    a = parser.parse_args()
    out = Path(a.out).resolve()
    cmd = [sys.executable, str(ROOT/'assigner.py'), '--host', '127.0.0.1',
           '--port', str(a.port), '--team', str(a.team), '--canvas', a.canvas,
           '--out', str(out), '--n', str(a.n)]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        ready = process.stdout.readline()
        print(ready, end='', flush=True)
        if not ready.startswith('READY'):
            raise RuntimeError('Assigner failed to start: '+process.stdout.read())
        launch('127.0.0.1', a.port, a.n, out/'workers')
        print(process.stdout.read(), end='', flush=True)
        if process.wait() != 0:
            raise RuntimeError('Assigner failed')
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait()
