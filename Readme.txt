G9 HW4 - ASCII Evolution (Python)

1. 조원
미입력: 조원 이름 / 학번 / 실제 수행한 역할 (조원이 작성 예정)

2. 배포 환경과 실행
조번호: 9. canvas의 조 이름: G9.
외부 서버: AWS EC2, Ubuntu 26.04 LTS, Python 3.14.4.
인스턴스 유형: t3.small, 리전 eu-north-1 (서버 IMDSv2 조회로 확인).
로컬: Windows, Python 3.13. Worker는 같은 로컬 PC에서 N개 프로세스로 실행.
통신 포트: TCP 9000. 로그 시각: UTC. 경과 시간 측정: time.perf_counter().
의존성: 시뮬레이션은 Python 표준 라이브러리만 사용. GIF 생성은 Pillow.
설치: python -m pip install -r requirements.txt
컴파일 단계 없음. Python 3.10 이상 필요.

서버에서:
  cd ~/hw4-g9-20261105
  python3 -u assigner.py --team 9 --port 9000 --canvas canvas --out runs/demo1 --timeout 600
READY에 출력된 N을 확인하고 로컬에서 (N=7인 예):
  python tools/run_workers.py --host 13.61.180.113 --port 9000 --n 7 --out runs/demo1/workers
기준값(로컬):
  python tools/run_local.py --n 1 --team 9 --port 9000 --out runs/my_n1
폴더는 매번 새 이름 사용. 제출용 원격 Assigner에는 --n을 지정하지 않는다.
두 원격 실행의 N은 서로 달라야 하며, 동일하게 나오면 다시 실행한다.
서버 결과를 내려받고 해당 로컬 workers 폴더와 같은 실행 폴더 아래에 합친다.

3. 프로그램 구성 및 메시지
assigner.py: Main 1개, 접속 시 한 번 만든 Handler N개. 도중 Thread 추가 생성 없음.
worker.py: Worker마다 별도 프로세스, Thread 하나. 자기 띠와 Halo 2줄, canvas1/2 조각만 유지.
common.py: TCP 수신 버퍼, 정확한 LF/ASCII 처리, 보드 파일, hash, 로그.
myrules.py: 이중 버퍼로 계산하는 칸 함수와 덧칠/변환.
tools: 실행 도우미, canvas/GIF 생성, 결과 검증. tests: 공식 정답 및 오류 주입 검사.

모든 메시지는 ASCII + LF. TCP는 메시지 경계를 보장하지 않으므로 줄 수신 버퍼 사용.
그림 줄에는 strip/trim 금지. 줄마다 정확히 160글자, ASCII 32~126 검증.
W->A HELLO
A->W ASSIGN k N y0 y1 team + canvas0 h줄 + canvas1 h+2줄 + canvas2 h+2줄
A->W ROUND r + top/bottom Halo 각 1줄
W->A RESULT r k + 새 첫/끝 줄 + (r+1)이 10의 배수이면 전체 띠 h줄
A->W BYE (RESULT 2999를 모두 받은 뒤)
잘못된 r/k, 단절, 시간 초과 시 FAIL 로그와 비정상 종료. 재접속/장애 복구는 범위 밖.

4. Thread / Lock / Condition 설계
Mutex m 하나로 round/arrived/edge/halo/frame 및 도착시각/통신량 공유 상태 보호.
done_cv와 go_cv는 같은 m에 연결. Handler는 결과 저장 후 arrived 증가.
마지막 Handler가 done_cv.notify, 각 Handler는 while round==r 조건으로 go_cv.wait.
Main은 while arrived<N으로 done_cv.wait, 모두 도착하면 다음 Halo 구성과 frame 복사.
round=r+1, arrived=0으로 바꾸고 go_cv.notify_all.
소켓 send/recv, 로그/그림 저장은 모두 Lock 밖에서 실행. 저장은 snapshot 사용.
Worker끼리 직접 통신하지 않으며 Assigner가 이웃의 첫/끝 줄을 중계.
띠 [80*k//N, 80*(k+1)//N), 상하좌우 Torus. Worker의 y는 원래 전체 판 좌표로 환산.
round1000/2000 파일은 덧칠 전 상태. 해당 ROUND 수신 후 Worker가 Halo 포함 덧칠/변환.

5. canvas 제작과 검사
tools/make_canvas.py의 직접 정의한 5x7 글꼴을 가로 두 칸씩 확대. 글자 높이 7줄.
canvas0: G9 / DATA COMM / TCP SOCKET / TEAM WORK
canvas1: G9 / ROUND SYNC / MUTEX LOCK / HALO LINK
canvas2: G9 / CYCLIC WAVE / BARRIER / PYTHON
문구와 위치는 파일마다 다르게 배치. 빈칸에 고정 난수 시드로 5% 확률의 '.' 배경 배치.
각 파일 80줄 x160글자, LF, 마지막 LF 포함 12880 bytes. G11 제출 그림 사용하지 않음.
check_canvas 결과: canvas0 점4.92% 획842, canvas1 점4.85% 획844, canvas2 점5.36% 획774.
  python tools/check_canvas.py canvas/canvas0.txt canvas/canvas1.txt canvas/canvas2.txt

6. 실측/검증
모든 값은 실제 summary.json/metrics.json과 workers/Worker{k}.json 및 로그를 근거로 작성했다.
상세 원자료 경로·실측표·분석: docs/VALIDATION.md
환경: 원격 AWS t3.small/eu-north-1/Ubuntu26.04/Python3.14.4, 로컬 Windows/Python3.13. 로그 UTC.
실행: n1(로컬 TCP N=1), remote1(원격 무작위 N=8), remote2(원격 무작위 N=7). 모두3000Round.

지표                                  n1(N=1)      remote1(N=8)    remote2(N=7)
전체 실행시간 (초): 12.709 / 939.983 / 955.998
처리량 (Round/초): 236.053 / 3.192 / 3.138
Round 평균 (ms): 4.230 / 313.310 / 318.649
Round 최대 (ms): 20.295 / 686.534 / 326.911
Barrier 평균 (ms): 0.000 / 11.368 / 19.329
Barrier 최대 (ms): 0.000 / 382.374 / 28.125
일반 Round 평균 (bytes): 668.260 / 5346.080 / 4677.820
전체 띠 Round 평균 (bytes): 13548.260 / 18226.080 / 17557.820

Worker 실측: 실행/W번호, 띠높이, 평균ms, 최대ms, 가장늦은횟수/3000
n1/W0: h=80, avg=3.913, max=19.294, slowest=3000/3000
remote1/W0: h=10, avg=1.270, max=5.677, slowest=0/3000
remote1/W1: h=10, avg=1.542, max=6.454, slowest=1/3000
remote1/W2: h=10, avg=1.562, max=5.819, slowest=0/3000
remote1/W3: h=10, avg=1.673, max=5.947, slowest=0/3000
remote1/W4: h=10, avg=1.366, max=6.091, slowest=357/3000
remote1/W5: h=10, avg=1.629, max=7.053, slowest=0/3000
remote1/W6: h=10, avg=1.715, max=6.647, slowest=1/3000
remote1/W7: h=10, avg=1.443, max=6.222, slowest=2641/3000
remote2/W0: h=11, avg=1.123, max=6.175, slowest=0/3000
remote2/W1: h=11, avg=1.076, max=5.542, slowest=0/3000
remote2/W2: h=12, avg=1.656, max=7.839, slowest=0/3000
remote2/W3: h=11, avg=1.533, max=6.733, slowest=0/3000
remote2/W4: h=12, avg=1.637, max=6.776, slowest=0/3000
remote2/W5: h=11, avg=1.036, max=5.954, slowest=2998/3000
remote2/W6: h=12, avg=1.556, max=7.355, slowest=2/3000

해석: 원격 평균 Round313~319ms에 비해 Worker 평균 계산1.0~1.7ms로 작다.
네트워크 왕복과 통신 대기가 큰 비중을 차지한다고 해석되며, 순수 RTT 별도 측정은 아니다.
N=7에서 12행 Worker의 계산량은 11행보다 대체로 크지만 최다 지연 W5는11행이다.
계산량 이외의 전송·스케줄링·PC부하가 도착 순서에 영향을 준다.
remote1/remote2는 일부 겹쳐 실행한 검증이므로 N에 따른 성능향상률을 주장하지 않는다.
통신량은 줄바꿈 포함 애플리케이션 바이트(TCP/IP헤더 제외). 10Round마다12880B 추가.
n1/remote1의 초기 코드 로그에는 100Round별 통신량이 없으나 metrics/최종summary에는 있다.
현재 소스는 BARRIER에도 구간 일반/전체띠 평균 통신량을 기록한다. 기존 로그를 수정하지 않았다.

정확성 확인:
- 단위/오류주입 테스트19개 모두PASS (규칙8, 프로토콜8, 결과검증3).
- G11 통신없는 reference 및 TCP N=7 모두 공식hash31/31 일치, 파일 재계산31/31 일치.
- G9 reference와 N=1, 로컬TCP N=4/5/6/8 모두31/31 일치.
- N=1/원격N=8/원격N=7: TOTAL 31/31 SAME -> PASS. 최종hash312bc0e2.
- 교수 verify_run.py: 세 실행 각각 형식31/31 및 기록hash=계산hash31/31 PASS.
- 각 실행 frame301개와 round31개, 해당 frame/round 일치, Worker 및 Assigner3000Round 완료.
- G9HW4.gif는 remote1(N=8)의 결과. 301장, 3794687bytes, 일반80ms/단계경계1000ms.
- GIF 첫 상태canvas0/마지막round3000, 디코딩 프레임 수와 지연시간 확인.

재검증 명령:
  python tools/verify_results.py runs/n1 runs/remote1 runs/remote2 --team 9 --out output/verification
  python tools/make_gif.py runs/remote1/frames output/G9HW4.gif --n 8 --team 9
  python tools/verify_run.py runs/remote1 runs/remote1/RoundHash.txt
  python -m unittest discover -s tests -v

조원 정보와 영상 링크는 추후 입력한다. 사용자 요청으로 ZIP 생성은 보류했으며 현재 ZIP은 만들지 않았다.

7. 한계 및 추가 사항
Worker 연결 복구/동적 증감 없음. Socket timeout 기본120초(서버 실행은600초 옵션).
무작위 N과 띠 계산, team/주소/포트/canvas 경로를 인자로 지정. 결과 폴더 덮어쓰기 거부.
알려진 정답 G11 fixture는 테스트 전용이며 제출 결과는 team9 canvas로 별도 생성.
검증 도구는 파일 일치와 기록을 검사하며, 실제 배포와 규칙 정확성은 원격 실행·공식 fixture 검사로 별도 확인.
사용 자료: 교수님 HW4description/HW4explanation/HW4_student_pack.
check_canvas.py/verify_run.py는 배포 원본, make_gif.py는 배포 예제 보강.
미입력: 조원 각자가 검토한 내용, 한계에 대한 의견, 배우거나 느낀 점.
