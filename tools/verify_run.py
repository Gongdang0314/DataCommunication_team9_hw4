# verify_run.py — 사용법: python verify_run.py run1 RoundHash_run1.txt   (round 파일 폴더, 그 실행의 RoundHash)
import sys, os, hashlib
folder, rh = sys.argv[1], sys.argv[2]
rec = dict(l.split()[:2] for l in open(rh) if len(l.split()) >= 2 and not l.startswith('#'))
ok1 = ok3 = 0
for r in range(0, 3001, 100):
    name = f"round{r:04d}.txt"; path = os.path.join(folder, name)
    if not os.path.exists(path): print(name, "없음"); continue
    b = open(path, "rb").read(); rows = b.split(b"\n")
    ok1 += len(b) == 12880 and len(rows) == 81 and rows[80] == b"" and all(len(x) == 160 for x in rows[:80])
    ok3 += rec.get(name) == hashlib.sha256(b).hexdigest()[:8]
print(f"(1) 형식 {ok1}/31   (3) 기록 hash = 계산 hash {ok3}/31   -> " + ("PASS" if ok1 == ok3 == 31 else "FAIL"))
