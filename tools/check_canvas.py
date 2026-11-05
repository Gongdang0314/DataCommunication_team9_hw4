# check_canvas.py — 사용법: python check_canvas.py canvas0.txt canvas1.txt canvas2.txt
import sys
for p in sys.argv[1:]:
    b = open(p, 'rb').read(); s = b.decode('ascii', errors='replace')   # ASCII 아닌 바이트 → 문자 NG
    rows = s.split('\n')[:-1]
    fmt = len(b) == 12880 and len(rows) == 80 and all(len(r) == 160 for r in rows) and '\r' not in s
    ok_chr = all(32 <= ord(c) <= 126 for c in s.replace('\n', ''))
    dot, sp = s.count('.'), s.count(' '); ink = len(s.replace('\n', '')) - dot - sp
    ratio = 100 * dot / max(dot + sp, 1)
    print(f"{p}: 형식 {'OK' if fmt else 'NG'}, 문자 {'OK' if ok_chr else 'NG'}, "
          f"점 {ratio:.2f}% {'OK' if 4 <= ratio <= 6 else 'NG'}, 글자 획 {ink}칸 {'OK' if ink >= 384 else 'NG'}")
# 샘플 G11 → canvas0.txt: 형식 OK, 문자 OK, 점 5.16% OK, 글자 획 576칸 OK
