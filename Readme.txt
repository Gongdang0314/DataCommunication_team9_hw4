================================================================================
HW#4 - ASCII Evolution (TCP 분산 셀룰러 오토마톤)
9조
================================================================================

1. 조원
================================================================================


   김대영 (20223087)
  - 역할: 미작성
   김민재 (20223089)
  - 역할: 미작성
   황태웅 (20223152)
  - 역할: 미작성

2. 프로그램 개요
================================================================================


  160 x 80 크기의 ASCII 그림을 3,000 Round 동안 진화시키는 프로그램이다. 외부 서버의
  Assigner 하나가 그림을 가로 띠 N개로 나누어 로컬 PC의 Worker N개에 배정하고, Worker는
  자기 띠만 계산한다. 띠 경계에 필요한 이웃 줄(Halo)은 Assigner가 매 Round 중계한다.

  - 그림 크기: 가로 160칸, 세로 80줄, 상하좌우가 이어진 Torus
  - 전체 Round: 3,000 (Round 번호 0~2999)
  - Round 0~999: Rule1 Text Life (B3/S23, 글자 물려받기)
  - Round 1000~1999: Rule2 Brian's Brain (@ -> + -> 공백)
  - Round 2000~2999: Rule3 Cyclic Ripple (RAMP " .:-=+*#%@", 상하좌우 4이웃)
  - Round 1000, 2000 직전: canvas1, canvas2 덧칠 후 다음 규칙의 상태로 변환
  - Worker 수 N: 제출용 실행은 매번 4~8 중 무작위, 기준 실행은 N=1
  - 완료 조건: N=1과 서로 다른 N의 분산 실행 2회에서 31개 round 파일 hash가 모두 같아야 함

  프로그램 구성은 다음과 같다.

  assigner.py: Worker 접속과 띠 배정, Halo 중계, Round Barrier, 결과 저장과 hash 기록
  worker.py: 자기 띠와 Halo 2줄만 가지고 계산, 덧칠/변환, RESULT 전송
  myrules.py: Rule1/2/3 칸 함수, 띠 계산, 덧칠과 단계 변환 (통신과 독립)
  common.py: TCP 줄 단위 수신 버퍼, ASCII/LF 보드 파일, hash, UTC 로그
  tools/run_workers.py: 로컬 Worker N개 프로세스 실행 및 종료 코드 확인
  tools/run_local.py: Assigner와 Worker를 한 PC에서 함께 실행 (기준값 N=1 생성용)
  tools/make_canvas.py: G9 canvas 3장 생성 / tools/check_canvas.py: canvas 형식 검사
  tools/verify_results.py: 세 실행의 31개 hash, 파일, 로그, frame 301장 검증
  tools/make_gif.py: 분산 실행 frame으로 G9HW4.gif 생성
  tools/package_submission.py: 검증을 거친 뒤 G9HW4.zip 생성
  tools/reference.py: 통신 없이 판 전체를 계산하는 규칙 확인용 프로그램
  tests/: 규칙, 프로토콜, 결과 검증 단위 테스트와 교수님 G11 정답 fixture
  AllDefinedLogs.txt: 로그 명세 / download.txt: 시연 영상 주소

3. 실행 환경 및 준비 사항
================================================================================


  시뮬레이션은 Python 표준 라이브러리만 사용한다. GIF 생성과 ZIP 패키징에만 Pillow가
  필요하다. Python 3.10 이상에서 실행하며 컴파일 단계는 없다.

    python -m pip install -r requirements.txt

  원격 호스트: AWS EC2 t3.small, eu-north-1, Ubuntu 26.04 LTS, Python 3.14.4
               (인스턴스 유형과 리전은 서버의 IMDSv2 조회로 확인)
  로컬 PC: Windows, Python 3.13. Worker N개를 같은 PC에서 프로세스로 실행
  EC2 공인 IP: 13.61.180.113
  SSH 접속 계정: ubuntu
  서버 작업 폴더: ~/hw4-g9-20261105
  Assigner 연결: 13.61.180.113:9000 (TCP)
  로그 시각: UTC / 경과 시간 측정: time.perf_counter()

  실행 전에 다음 사항을 확인한다.

  - Python 실행 여부: python --version
  - EC2의 현재 공인 IP와 SSH 접속 가능 여부
  - EC2 보안 그룹에서 TCP 9000번 포트가 실행 PC에 열려 있는지
  - 이전 실행이 9000번 포트를 사용하고 있지 않은지

  모든 명령은 assigner.py, worker.py가 있는 프로젝트 폴더에서 실행한다. 아래 Windows
  예시는 python, EC2 예시는 python3를 사용한다.

4. EC2 준비 및 소스 전송
================================================================================


  로컬 PC에서만 실행할 경우 이 부분을 건너뛰고 7항의 명령을 사용하면 된다.

  EC2 보안 그룹에는 SSH용 TCP 22번과 Assigner용 TCP 9000번 포트를 연다. Worker끼리는
  직접 연결하지 않으므로 다른 포트는 열 필요가 없다.

  SSH 키 파일은 저장소와 제출 ZIP에 넣지 않고 로컬 Downloads 폴더에 둔다. 로컬
  PowerShell에서 다음 값을 설정한다. 새 창을 열면 변수도 다시 설정한다.

    $Ec2Key = "$env:USERPROFILE\Downloads\HaEeee.pem"
    $Ec2Ip = "13.61.180.113"
    Test-Path "$Ec2Key"

  Assigner 실행에 필요한 파일을 EC2에 전송한다. canvas 폴더도 함께 보낸다.

    ssh -i "$Ec2Key" "ubuntu@$Ec2Ip" "mkdir -p ~/hw4-g9-20261105/canvas"
    scp -i "$Ec2Key" ./assigner.py ./common.py ./myrules.py ./worker.py "ubuntu@${Ec2Ip}:~/hw4-g9-20261105/"
    scp -i "$Ec2Key" ./canvas/canvas0.txt ./canvas/canvas1.txt ./canvas/canvas2.txt "ubuntu@${Ec2Ip}:~/hw4-g9-20261105/canvas/"

  코드나 canvas를 수정한 뒤에는 EC2에도 다시 전송한다. 로컬 Worker와 EC2 Assigner는
  같은 버전으로 실행한다. canvas는 LF 줄 끝을 유지해야 하므로 메모장으로 저장하지 않는다.

5. 명령행 인자
================================================================================


Assigner (assigner.py)

  --host: 연결을 받을 주소. 기본값 0.0.0.0
  --port: 연결을 받을 TCP 포트. 기본값 9000
  --team: 조번호. 필수 (제출용은 9)
  --canvas: canvas0~2.txt가 있는 폴더. 기본값 canvas
  --out: 결과 저장 폴더. 필수. 비어 있지 않은 폴더는 거부한다
  --n: Worker 수 고정 (1, 4~8). 개발/기준 실행용이며 제출용 실행에서는 지정하지 않는다
  --timeout: 접속 대기와 소켓 수신 제한 시간(초). 기본값 120

Worker (worker.py)

  --host: Assigner IP. 필수
  --port: Assigner 포트. 기본값 9000
  --out: Worker 로그 저장 폴더. 기본값 runs/workers
  --timeout: 소켓 제한 시간(초). 기본값 120

  Worker 번호 k, N, 띠 범위, 조번호는 Assigner의 ASSIGN으로 받으므로 인자로 넣지 않는다.

Worker 실행 도우미 (tools/run_workers.py)

  --host, --port: Assigner 주소
  --n: 실행할 Worker 수. Assigner가 READY에 출력한 N과 같아야 한다
  --out: Worker 로그 폴더. 비어 있어야 한다

  Worker를 N개 각각 실행하면 앞에 띄운 Worker가 기다리다 timeout될 수 있으므로,
  run_workers.py로 한 번에 실행한다.

6. 프로그램 실행 (EC2 + 로컬 PC)
================================================================================


  출력 폴더는 매 실행 새 이름을 쓴다. 이전 결과를 덮어쓰지 않도록 프로그램이 거부한다.

6-1. Assigner 실행

  먼저 로컬 PowerShell에서 EC2에 접속한다.

    ssh -i "$Ec2Key" "ubuntu@$Ec2Ip"

  EC2 터미널에서 실행한다. 제출용 실행에는 --n을 넣지 않는다.

    cd ~/hw4-g9-20261105
    python3 -u assigner.py --team 9 --port 9000 --canvas canvas --out runs/demo1 --timeout 600

  다음 줄이 출력되면 Worker 접속을 기다리는 상태이다. N은 4~8 중 무작위로 정해진다.

    READY N=7 TEAM=9 port=9000

6-2. Worker 실행

  새 로컬 PowerShell 창에서 프로젝트 폴더로 이동한 뒤, READY에 나온 N을 그대로 넣는다.
  아래 7은 예시이다.

    $Ec2Ip = "13.61.180.113"
    Test-NetConnection $Ec2Ip -Port 9000
    python tools/run_workers.py --host $Ec2Ip --port 9000 --n 7 --out runs/demo1/workers

  Worker N개가 접속하면 Assigner가 접속 순서대로 Worker 번호 0~N-1을 배정하고 계산을
  시작한다. 100 Round마다 Assigner 터미널에 PROGRESS가 출력된다.

6-3. 완료 확인

  Assigner 터미널에서 다음 출력을 확인한다.

    PROGRESS G9 N=7 round=3000/3000 elapsed=...s
    PASS G9 N=7 3000 rounds ...s

  로컬에서는 "PASS: 7 Worker processes completed"가 출력된다. 정상 완료 시 종료 코드는
  0이며, 프로토콜 오류, 연결 끊김, 시간 초과가 생기면 FAIL 로그를 남기고 종료 코드 1로
  끝난다.

6-4. 두 번째 실행과 결과 모으기

  두 번째 실행은 새 폴더(runs/demo2)로 같은 절차를 반복한다. 무작위 N이 첫 번째 실행과
  같게 나오면 그 실행은 제외하고 다시 실행한다.

  서버 결과 폴더를 로컬로 내려받아 같은 실행의 workers/ 폴더와 합친다.

    scp -i "$Ec2Key" -r "ubuntu@${Ec2Ip}:~/hw4-g9-20261105/runs/demo1/*" ./runs/demo1/

  성능 비교를 위해 두 원격 실행은 동시에 돌리지 않고 하나씩 순서대로 실행한다.

7. 로컬 실행 및 테스트
================================================================================


7-1. 기준값 N=1 실행

  Assigner와 Worker 1개를 로컬 TCP로 함께 실행한다.

    python tools/run_local.py --n 1 --team 9 --port 9000 --out runs/n1

  run_local.py는 Worker가 끝난 뒤 Assigner 출력을 한꺼번에 보여 준다. 실행 중에는
  출력이 멈춘 것처럼 보일 수 있으나 정상이다.

7-2. 단위 테스트

    python -m unittest discover -s tests -v

  19개 테스트를 통과한다 (규칙 8개, 프로토콜 8개, 결과 검증 3개). 교수님 키트의 작은
  규칙 정답, 덧칠과 변환, Halo 좌표, 이중 버퍼, TCP 메시지가 잘리거나 합쳐져 오는 경우,
  연결 끊김, timeout, 잘못된 RESULT, 손상된 결과 파일 거부를 확인한다.

7-3. 교수님 G11 샘플로 정답 확인

  통신 없이 판 전체를 계산해 공식 hash와 비교한다.

    python tools/reference.py --canvas tests/fixtures/G11_sample --team 11 --out output/reference_check --expected tests/fixtures/G11_sample/RoundHash_N1.txt

  실제 분산 실행으로도 확인할 수 있다. 결과의 RoundHash.txt를 공식
  tests/fixtures/G11_sample/RoundHash_N1.txt와 비교한다.

    python tools/run_local.py --n 6 --team 11 --port 9000 --canvas tests/fixtures/G11_sample --out runs/g11_n6

  reference.py는 규칙 확인용이며 제출용 N=1 Assigner + Worker 실행을 대신하지 않는다.

7-4. canvas 검사

    python tools/check_canvas.py canvas/canvas0.txt canvas/canvas1.txt canvas/canvas2.txt

8. 주요 구현 내용
================================================================================


8-1. 띠 분할과 Halo

  Worker k는 [80*k//N, 80*(k+1)//N) 행을 맡는다. 예를 들어 N=6이면 띠 높이는
  13, 13, 14, 13, 13, 14줄이다.

  Worker의 작업판은 [위 Halo 1줄] + [자기 띠 h줄] + [아래 Halo 1줄]이다. 칸 함수는 좌우만
  감싸고(wrap) 위아래 이웃은 Halo 줄에서 읽는다. Worker 0의 위 이웃은 Worker N-1의 마지막
  줄, Worker N-1의 아래 이웃은 Worker 0의 첫 줄이므로 세로 방향도 Torus가 된다.

  Worker끼리는 직접 연결하지 않는다. 각 Worker는 매 Round 자기 띠의 새 첫 줄과 끝 줄을
  Assigner에 보내고, Assigner가 이를 이웃 Worker의 다음 Round Halo로 전달한다(Star 구조).

8-2. 진화 규칙

  세 규칙 모두 현재 판을 읽기만 하고 새 판에 결과를 쓰는 이중 버퍼로 계산한다. 계산
  순서가 결과에 영향을 주지 않는다.

  Rule1 Text Life: 8이웃 중 공백이 아닌 칸을 산 칸으로 본다. 산 칸은 이웃 2~3개면 유지,
  빈칸은 이웃이 정확히 3개면 탄생한다. 탄생 글자는 세 부모 중 많은 글자, 셋 다 다르면
  ASCII 코드가 가장 작은 글자이다.

  Rule2 Brian's Brain: @는 +로, +는 공백으로 바뀐다. 공백은 8이웃 중 @가 정확히 2개면
  @가 된다.

  Rule3 Cyclic Ripple: RAMP " .:-=+*#%@"의 다음 단계 글자가 상하좌우 4이웃 중 하나라도
  있으면 한 단계 올라간다. 대각선은 보지 않는다.

8-3. 덧칠과 단계 변환

  round1000.txt, round2000.txt는 덧칠 전 상태이다. Worker는 ROUND 1000(2000)을 받은 뒤
  계산 전에 덧칠과 변환을 적용한다.

  - 덧칠: canvas의 글자 중 공백과 '.'이 아닌 것만 작업판에 덮어쓴다
  - Round 1000: canvas1 덧칠 후 공백이 아닌 모든 칸을 @로 바꾼다
  - Round 2000: canvas2 덧칠 후 RAMP에 없는 칸(공백 포함)을
    RAMP[(7x + 3y + (x*y mod 11) + team) mod 10]으로 바꾼다

  덧칠과 변환은 Halo 줄에도 적용한다. 그래야 경계 칸이 이웃 Worker가 가진 실제 상태와
  같은 값을 보고 계산한다. 이를 위해 ASSIGN 때 canvas1, canvas2는 Halo를 포함한 h+2줄씩
  보낸다. 변환의 y는 Worker 안의 행 번호가 아니라 원래 전체 판의 행 번호로 환산한다.

8-4. Thread, Lock, Condition 설계

  Assigner에는 Main Thread 1개와 Worker별 Handler Thread N개가 있다. Handler는 Worker가
  모두 접속한 뒤 한 번만 만들고 실행 도중 Thread를 새로 만들지 않는다. Worker는 프로세스마다
  Thread 하나로 동작한다.

  Mutex m 하나로 round, arrived, edges, halo, frame과 도착 시각, 통신량을 보호한다.
  Condition 두 개(done_cv, go_cv)는 같은 m에 연결한다.

  - Handler: Halo를 읽어 ROUND 전송 -> RESULT 수신 -> m 안에서 결과 저장, arrived 증가
  - 마지막으로 도착한 Handler가 done_cv.notify()로 Main을 깨운다
  - Handler는 while round == r 조건으로 go_cv.wait()
  - Main: while arrived < N 조건으로 done_cv.wait(). 모두 도착하면 다음 Halo를 만들고
    round = r+1, arrived = 0으로 바꾼 뒤 go_cv.notify_all()

  wait()는 while 조건으로 감싸 깨어난 뒤에도 조건을 다시 확인한다. 소켓 send/recv와
  파일·로그 저장은 모두 Lock 밖에서 한다. 그림 저장은 Lock 안에서 frame을 복사한
  snapshot으로 한다. 따라서 모든 Worker의 RESULT r이 도착하기 전에는 ROUND r+1이 나가지
  않는다.

  Handler 하나에서 오류가 나면 공유 error 상태를 설정하고 두 Condition을 모두 깨운다.
  Main은 모든 소켓을 shutdown해 recv에서 기다리는 Handler도 깨운 뒤 FAIL 로그를 남기고
  종료한다.

8-5. 통신 형식

  모든 메시지는 ASCII 문자열이며 줄 끝은 LF이다. TCP는 메시지 경계를 보장하지 않으므로
  수신 버퍼에 쌓은 뒤 LF 단위로 잘라 처리한다. 그림 줄의 앞뒤 공백도 그림의 일부이므로
  strip하지 않고, 줄마다 정확히 160글자, ASCII 32~126인지 검사한다. 작은 메시지가
  지연되지 않도록 TCP_NODELAY를 켰다.

    W->A  HELLO
    A->W  ASSIGN k N y0 y1 team
          + canvas0 h줄 + canvas1 h+2줄 + canvas2 h+2줄
    A->W  ROUND r + 위 Halo 1줄 + 아래 Halo 1줄
    W->A  RESULT r k + 새 첫 줄 + 새 끝 줄
          ((r+1)이 10의 배수이면 띠 전체 h줄을 덧붙임)
    A->W  BYE  (모든 Worker의 RESULT 2999를 받은 뒤)

  Assigner는 RESULT의 r, k와 줄 형식을 검사하고, 띠 전체가 오면 첫/끝 줄이 같은지도
  확인한다. 잘못된 메시지, 연결 끊김, 시간 초과는 FAIL로 기록하고 비정상 종료한다.

8-6. 결과 저장

  10 Round마다 frames/frameXXXX.txt(301장), 100 Round마다 roundXXXX.txt(31개)를 저장한다.
  파일은 80줄 x 160글자, 각 줄 끝 LF, 정확히 12,880바이트이다. round 파일의 SHA-256 앞
  8자리를 RoundHash.txt에 기록한다.

9. canvas 제작
================================================================================


  tools/make_canvas.py에서 직접 정의한 5x7 글꼴을 가로 두 칸씩 키워 그렸다. 글자 높이는
  7줄이다. 빈칸에는 고정 난수 seed로 약 5% 확률의 '.' 배경을 넣었다.

  canvas0: G9 / DATA COMM / TCP SOCKET / TEAM WORK
  canvas1: G9 / ROUND SYNC / MUTEX LOCK / HALO LINK
  canvas2: G9 / CYCLIC WAVE / BARRIER / PYTHON

  문구와 위치는 세 파일마다 다르게 배치했다. check_canvas 결과는 다음과 같다.

  canvas0: 형식 OK, 문자 OK, 점 4.92%, 글자 획 842칸
  canvas1: 형식 OK, 문자 OK, 점 4.85%, 글자 획 844칸
  canvas2: 형식 OK, 문자 OK, 점 5.36%, 글자 획 774칸

10. 로그 확인 및 실행 결과
================================================================================


  실행 폴더마다 다음 파일이 생긴다. Assigner 쪽 파일은 서버에, workers/ 폴더는 로컬에
  생기므로 6-4항처럼 합친다.

  Assigner.txt: Assigner 로그
  workers/Worker0.txt ~ Worker(N-1).txt: Worker 로그
  RoundHash.txt, round0000.txt ~ round3000.txt, frames/: 결과 그림과 hash
  run.json, summary.json, metrics.json, workers/Worker{k}.json: 실행 설정과 실측값

  로그 형식은 [HH:MM:SS.mmm] NODE | EVENT | STATUS | message이고 시각은 UTC이다.
  로그에서는 다음 내용을 확인한다. 자세한 정의는 AllDefinedLogs.txt에 있다.

  - INIT, CONNECT, ASSIGN: 무작위 N, 띠 경계, Worker 접속과 배정
  - SAVE: round 파일 저장과 hash
  - BARRIER: 100 Round 구간의 Round 시간, 대기 시간, 가장 늦은 Worker, 통신량
  - REPAINT: Round 1000/2000 덧칠과 변환
  - TERMINATE: 최종 실측 요약(성공) 또는 실패 원인

  측정값의 의미는 다음과 같다.

  - Round 시간: Main이 Round를 시작한 시각부터 N개 RESULT가 모두 도착할 때까지
  - Barrier 대기: 같은 Round에서 가장 늦은 RESULT 도착 - 가장 빠른 RESULT 도착
  - Worker 계산: Worker가 ROUND를 받은 뒤 RESULT를 보낼 때까지
  - 통신량: 줄바꿈을 포함한 ROUND/RESULT 메시지 바이트 (TCP/IP 헤더 제외)

11. 발견한 문제와 수정 내용
================================================================================


Worker 접속 기록 시각이 늦게 찍히는 문제

  Worker는 ASSIGN을 받아야 자기 번호 k를 알 수 있으므로, 그 전에는 Worker{k}.txt 파일을
  만들 수 없다. 그대로 기록하면 CONNECT가 ASSIGN을 받은 시각으로 찍힌다. 실제 접속
  시각을 저장해 두었다가 파일을 연 뒤 그 시각으로 CONNECT를 기록하도록 했다.

Worker의 N 검증이 너무 엄격한 문제

  Worker가 N을 정해진 값 몇 개로만 허용하고 있어, 다른 N으로 시험하면 Worker가 배정을
  거부할 수 있었다. Worker는 Assigner가 정한 N을 따르고, N이 1~80 범위인지와 띠 범위가
  [80*k//N, 80*(k+1)//N)과 일치하는지만 확인하도록 바꿨다.

Windows에서 round 파일 검사에 RoundHash.txt가 섞이는 문제

  Windows의 파일 이름 검색은 대소문자를 구분하지 않아 round*.txt에 RoundHash.txt도
  포함되었다. 검증 도구에서 이름이 소문자 round로 시작하는 파일만 골라 31개인지
  확인하도록 수정했다.

Windows 콘솔에서 검증 결과 출력이 실패하는 문제

  출력을 파일로 돌리면 콘솔 인코딩이 cp949가 되어, 경로에 표현할 수 없는 문자가 있으면
  검증이 성공했는데도 출력 단계에서 오류가 났다. 출력할 수 없는 문자는 대체해서
  출력하도록 했다.

계산 속도 개선 시도

  칸 계산을 bytearray와 정수 비교로 바꿔 보았으나, 실측 결과 오히려 느려졌다(약 17초 ->
  30초). 현재의 문자열 리스트 방식을 유지했다.

최종 점검 (2026-11-08)

  단위 테스트 19개가 통과했다. 교수님 G11 샘플 canvas로 실제 Assigner와 Worker를 N=1,
  6, 8로 실행해, 세 실행 모두 31개 hash가 공식 RoundHash_N1.txt와 일치하는 것을 다시
  확인했다. G9 canvas 3장도 check_canvas 검사를 통과했다.

12. 실행 중 문제가 생긴 경우
================================================================================


Assigner에 연결되지 않을 때

  Assigner가 먼저 실행되었는지, IP와 포트가 맞는지 확인한다. EC2를 다시 시작했다면
  공인 IP가 바뀌었을 수 있다. 보안 그룹의 TCP 9000번 규칙도 확인한다.

Address already in use가 나올 때

  이전 Assigner가 아직 9000번 포트를 사용하고 있는지 확인한다.

output directory must be empty가 나올 때

  이전 결과를 지키기 위해 비어 있지 않은 폴더는 거부한다. 새 폴더 이름을 지정한다.

Worker가 timeout으로 종료될 때

  Worker 수가 READY의 N과 같은지 확인한다. Worker가 N개보다 적으면 Assigner가 ASSIGN을
  보내지 않으므로 먼저 접속한 Worker가 기다리다 종료된다.

hash가 다르게 나올 때

  서버와 로컬의 canvas, 코드가 같은 버전인지 확인한다. canvas가 CRLF로 저장되면 읽을 때
  거부된다. --team 값이 9인지도 확인한다(Round 2000 변환에 사용).

  Worker 연결이 끊긴 뒤 다시 접속하거나 Worker 수를 실행 중에 바꾸는 기능은 구현하지
  않았다. 이 경우 실행을 실패로 끝내고 새 폴더로 다시 실행한다.

13. 제출 파일과 원격 실행 결과
================================================================================

13-1. 제출 파일

  G9HW4.zip은 tools/package_submission.py로 만든다. 세 실행의 검증과 GIF 확인을 통과해야
  ZIP이 만들어진다. Readme.txt와 download.txt에 미작성 항목이 남아 있으면 --final
  모드는 ZIP을 만들지 않는다.

    python tools/package_submission.py runs/n1 runs/remote1 runs/remote2 --final

  assigner.py, worker.py, myrules.py, common.py: 실행 소스
  tools/, tests/: 실행 도우미, 검증 도구, 테스트
  canvas0.txt ~ canvas2.txt (canvas/에도 같은 파일): G9 입력 그림
  round0000.txt ~ round3000.txt, Assigner.txt, Worker{k}.txt: 원격 실행 1의 결과와 로그
  hash_result.txt: N=1과 두 원격 실행의 31개 hash 비교 결과
  G9HW4.gif: 원격 실행 1의 frame 301장으로 만든 GIF
  evidence/n1, evidence/run1, evidence/run2: 세 실행의 전체 결과
  Readme.txt, AllDefinedLogs.txt, download.txt, docs/, MANIFEST.sha256

  SSH 키 파일은 제출 ZIP에 넣지 않는다.

  시연 영상 주소: download.txt 참조

13-2. 실행 목록

  n1: 로컬 TCP, N=1 (기준값)
  remote1: 원격 Assigner, 무작위 N=8
  remote2: 원격 Assigner, 무작위 N=7

  세 실행 모두 3,000 Round를 완료했다. remote1과 remote2는 실행 시간이 일부 겹쳤으므로
  아래 표를 N에 따른 속도 향상 비교로 해석하지 않는다.

13-3. 전체 결과

  표 1. 실행별 실측값
  지표                        | n1 (N=1)  | remote1 (N=8) | remote2 (N=7)
  전체 실행 시간 (초)         |    12.709 |       939.983 |       955.998
  처리량 (Round/초)           |   236.053 |         3.192 |         3.138
  Round 평균 (ms)             |     4.230 |       313.310 |       318.649
  Round 최대 (ms)             |    20.295 |       686.534 |       326.911
  Barrier 대기 평균 (ms)      |     0.000 |        11.368 |        19.329
  Barrier 대기 최대 (ms)      |     0.000 |       382.374 |        28.125
  일반 Round 통신량 (bytes)   |   668.260 |      5346.080 |      4677.820
  띠 전체 Round 통신량 (bytes)| 13548.260 |     18226.080 |     17557.820

  표 2. Worker별 실측값
  실행    | Worker | 띠 높이 | 평균 계산 (ms) | 최대 계산 (ms) | 가장 늦은 횟수
  n1      | W0     |      80 |          3.913 |         19.294 |   3000 / 3000
  remote1 | W0     |      10 |          1.270 |          5.677 |      0 / 3000
  remote1 | W1     |      10 |          1.542 |          6.454 |      1 / 3000
  remote1 | W2     |      10 |          1.562 |          5.819 |      0 / 3000
  remote1 | W3     |      10 |          1.673 |          5.947 |      0 / 3000
  remote1 | W4     |      10 |          1.366 |          6.091 |    357 / 3000
  remote1 | W5     |      10 |          1.629 |          7.053 |      0 / 3000
  remote1 | W6     |      10 |          1.715 |          6.647 |      1 / 3000
  remote1 | W7     |      10 |          1.443 |          6.222 |   2641 / 3000
  remote2 | W0     |      11 |          1.123 |          6.175 |      0 / 3000
  remote2 | W1     |      11 |          1.076 |          5.542 |      0 / 3000
  remote2 | W2     |      12 |          1.656 |          7.839 |      0 / 3000
  remote2 | W3     |      11 |          1.533 |          6.733 |      0 / 3000
  remote2 | W4     |      12 |          1.637 |          6.776 |      0 / 3000
  remote2 | W5     |      11 |          1.036 |          5.954 |   2998 / 3000
  remote2 | W6     |      12 |          1.556 |          7.355 |      2 / 3000

13-4. 결과 해석

  원격 실행의 Round 평균은 약 313~319ms인데 Worker의 평균 계산 시간은 1.0~1.7ms이다.
  Round 시간의 대부분은 계산이 아니라 한국의 로컬 PC와 eu-north-1 서버 사이의 네트워크
  왕복과 대기로 보인다. 다만 순수 RTT를 따로 측정한 것은 아니다.

  N=7에서 12줄을 맡은 Worker의 평균 계산(1.56~1.66ms)은 11줄 Worker(1.04~1.53ms)보다
  대체로 길었다. 그러나 가장 자주 늦게 도착한 Worker는 11줄인 W5였다. 도착 순서는 계산량
  외에 전송과 스케줄링, PC 부하의 영향도 받는다.

  일반 Round와 띠 전체를 보내는 Round의 통신량 차이는 12,880바이트로, 그림 전체
  80 x 160글자와 LF 80개에 해당한다.

13-5. 정합성 확인 방법과 결과

    python tools/verify_results.py runs/n1 runs/remote1 runs/remote2 --team 9 --out output/verification

  1) 세 실행의 round 파일 31개가 모두 80 x 160, ASCII, LF, 12,880바이트인지 확인했다.
  2) 각 RoundHash.txt의 기록 hash와 파일에서 다시 계산한 hash가 31/31 일치했다.
  3) N=1, N=8, N=7 세 실행의 31개 hash가 모두 같았다: TOTAL 31/31 SAME -> PASS.
     최종 round3000 hash는 세 실행 모두 312bc0e2이다.
  4) 두 원격 실행의 N이 무작위(random_n=True)이고 서로 다른 것을 확인했다.
  5) 실행마다 frame 301장이 있고, 100 Round 단위 frame이 round 파일과 같았다.
  6) Assigner와 모든 Worker 로그에 3,000 Round 완료와 TERMINATE SUCCESS가 있었다.
  7) 교수님 배포 verify_run.py로도 세 실행 각각 형식 31/31, 기록 hash = 계산 hash
     31/31 PASS를 확인했다.
  8) G9HW4.gif는 remote1(N=8)의 frame 301장으로 만들었다. 실제 디코딩으로 301장과
     지연 시간(일반 80ms, 단계 경계 1초)을 확인했다.

  hash 일치는 결과가 같다는 것을 보여 줄 뿐 원격 배포 자체를 증명하지는 않는다. 원격
  실행 장면은 시연 영상에서 따로 보여 준다.

14. 제출 전 확인 사항
================================================================================


  아래 항목을 모두 처리한 뒤 이 항목을 지우고 --final로 ZIP을 만든다.

  1) 1항 조원 역할의 '미작성'을 실제 역할로 바꾼다. '미작성'이 남아 있으면
     package_submission.py --final이 ZIP을 만들지 않는다.
  2) download.txt에 시연 영상(G9HW4.mp4)의 다운로드 가능한 링크를 넣고, 로그인하지 않은
     상태에서도 재생/다운로드되는지 확인한다.
  3) 13항의 실측값은 runs/n1, runs/remote1, runs/remote2 실행 결과이다. 현재 로컬
     저장소에는 runs/ 폴더가 없으므로, 보관한 결과 폴더를 runs/ 아래에 복원하거나
     다시 실행한다. ZIP 생성에 이 세 폴더가 필요하다.
  4) remote1과 remote2는 실행 시간이 일부 겹쳤다. 원격 실행을 하나씩 순서대로 다시
     하면 13-2~13-5항의 N, 표, 해석, 최종 hash를 새 결과로 바꾼다.
  5) SSH 키 파일은 저장소와 ZIP에 넣지 않는다. Readme에는 키를 Downloads에 두고 쓰는
     방법만 적었다.
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
