# 코드를 설명하기 위한 G9 HW4 읽기 순서

프로그램은 **그림을 나누어 계산하는 Worker**와 **경계를 전달하고 보조를 맞추는 Assigner**로 나뉜다. 분산 실행이 정확하다는 뜻은 Worker 수가 달라도 같은 초기 그림에서 같은 상태를 얻는다는 뜻이다.

## 먼저 볼 파일

| 파일/함수 | 하는 일 | 직접 설명할 내용 |
|---|---|---|
| `tools/make_canvas.py`: `make_canvas`, `encode_and_check` | G9 그림과 점 배경 생성·규격 검사 | 왜 세 장인지, G9와 서로 다른 문구/배치, LF |
| `myrules.py`: `rule1_cell`~`rule3_cell`, `band` | 한 칸의 다음 상태와 띠 전체 계산 | 이중 버퍼, 8이웃/4이웃, 문자 선택 |
| `common.py`: `Wire` | TCP에서 LF 기준 메시지 읽기/쓰기 | recv 한 번이 메시지 한 개가 아님 |
| `worker.py`: `run` | ASSIGN 수신 → ROUND 계산 → RESULT 송신 | 자기 띠와 Halo만으로 계산 |
| `assigner.py`: `run` 안의 `handler`와 Main 루프 | Halo 중계, 결과 취합, Barrier, 파일 저장 | Main/Handler 역할, Mutex/CV |
| `tools/verify_results.py`: `verify_run`, `verify_all` | 파일/로그 검증 및 세 실행 hash 비교 | 무엇을 검증하고 무엇을 증명하지 않는지 |
| `tools/make_gif.py`: `read_frames`, `phase`, `make_gif` | 301개 상태를 GIF로 표현 | 덧칠 전 경계 상태, 실제 프레임 수 검사 |

## 1. 전체 그림을 왜 다 보내지 않나

전체는 80행 × 160열이다. Worker k는 `[80*k//N, 80*(k+1)//N)` 행을 맡는다. 예를 들어 N=6의 Worker1은 `[13,26)`, 즉 원래 행 13~25의 13줄을 담당한다.

행 13의 이웃을 계산하려면 행 12가, 행 25를 계산하려면 행 26이 필요하다. 그래서 작업판은 **위 Halo 1줄 + 자기 띠 h줄 + 아래 Halo 1줄**이다. Worker는 가운데 h줄만 계산한다. 행 0 위는 행 79, 행 79 아래는 행 0이다. 이 연결을 Assigner가 만든다. Worker끼리 연결하지 않는다.

`myrules.band()`는 모든 새 칸을 별도의 리스트로 계산한다. 이미 계산한 새 값을 다음 칸의 입력으로 사용하지 않으므로 계산 순서가 결과에 영향을 주지 않는다.

## 2. TCP 메시지 흐름

```text
Worker → Assigner: HELLO
Assigner → Worker: ASSIGN k N y0 y1 team
                   canvas0 h줄, canvas1 h+2줄, canvas2 h+2줄
Assigner → Worker: ROUND r
                   top 1줄, bottom 1줄
Worker → Assigner: RESULT r k
                   새 첫 줄, 새 끝 줄
                   (r+1이 10의 배수이면 자기 띠 h줄 추가)
Assigner → Worker: BYE (3000 Round 완료)
```

그림의 한 줄은 **공백도 포함하여 정확히 160글자**다. 오른쪽 빈칸까지 그림의 일부이므로 `.strip()`으로 없애면 안 된다. `Wire.line()`은 LF까지만 분리하고 나머지 바이트는 수신 버퍼에 남긴다. 한 `recv()`에 명령 일부만 올 수도, 여러 줄이 한꺼번에 올 수도 있다. `Wire.rows()`는 길이와 출력 가능한 ASCII인지 검사한다. 송신은 모든 줄을 LF로 연결하여 `sendall()`로 끝까지 보낸다.

## 3. Barrier가 필요한 이유와 순서

Round r+1의 Halo는 다른 Worker의 Round r 결과다. 빠른 Worker가 혼자 다음 계산을 시작하면 오래된 이웃을 읽을 수 있다.

1. **Handler k**는 Mutex 안에서 자기 Halo를 복사하고 Lock 밖에서 `ROUND r`를 전송한다.
2. `RESULT r k`를 받고 r/k/줄 형식을 검사한다. Mutex 안에서 첫·끝 줄과 필요 시 전체 띠, 도착 시각을 공유 상태에 반영한다.
3. `arrived`를 1 늘린다. 마지막 결과이면 `done_cv.notify()`로 Main을 깨운다. Handler는 `go_cv`에서 다음 Round를 기다린다.
4. **Main**은 `while arrived < N` 조건으로 기다린다. 전원이 도착하면 이웃의 새 첫·끝 줄로 다음 Halo를 만들고, 저장할 그림은 복사한다.
5. Main이 `arrived=0`, `round=r+1`로 바꾸고 `go_cv.notify_all()`로 Handler들을 깨운다. Lock을 해제한 뒤 그림 복사본을 파일로 저장한다.

두 Condition은 **같은 Mutex 하나**를 사용한다. `wait()`는 기다리는 동안 Lock을 풀고, 깨어날 때 다시 잡는다. `while`을 쓰는 이유는 깨어났다는 사실만으로 조건이 만족됐다고 단정할 수 없기 때문이다. 네트워크 송수신과 파일 쓰기는 공유 상태 Lock 밖에서 한다.

Assigner의 Thread는 Main 1개 + 접속 후 한 번 만든 Handler N개다. Worker는 각각 별도 프로세스이며 하나의 Thread로 수신→계산→송신을 반복한다.

## 4. Round 번호와 저장 상태를 구분하기

`S(r)`는 **Round r 계산 직전의 상태**다. `RESULT r`는 `S(r+1)`의 결과다.

```text
canvas0 = S(0) → Round 0 계산 → S(1)
RESULT 999 취합 → S(1000) 저장 → canvas1 덧칠/변환 → Round 1000 계산
RESULT 1999 취합 → S(2000) 저장 → canvas2 덧칠/변환 → Round 2000 계산
RESULT 2999 취합 → S(3000) 저장 → BYE
```

따라서 `round1000.txt`와 `round2000.txt`는 **덧칠 전 그림**이다. 덧칠은 Worker가 해당 ROUND 명령과 Halo를 받은 뒤 작업판 전체에 한다. Halo도 바뀌어야 경계 칸과 내부 칸이 같은 규칙을 따른다. `make_gif.phase()`도 이 저장 상태를 기준으로 제목을 붙인다.

Rule3 변환의 y는 작업판 행 번호 i가 아니라 **전체 그림의 원래 y**다. `worker.py`는 위 Halo의 원래 행 `(y0-1)%80`을 전달하고, `to_cyclic()`은 `(ytop+i)%80`을 사용한다. 여기에 `team=9`가 들어간다. 조 이름 그림만 G9로 바꾸고 team을 11로 두면 다른 결과가 나온다.

## 5. hash와 테스트가 증명하는 범위

`common.board_bytes()`는 각 160글자 뒤에 LF를 넣어 정확히 12,880바이트를 만든다. hash는 이 **파일 전체 바이트**의 SHA-256 앞 8자리다. Windows CRLF, 공백 삭제, 마지막 LF 누락도 hash를 바꾼다.

- 작은 공식 테스트 및 G11 공식 31개 hash 비교: 계산 규칙 자체가 명세와 맞는지 점검.
- G9의 실제 N=1 TCP 실행과 두 분산 실행 비교: 띠 분할·Halo·Barrier가 전체 계산과 같은 결과인지 점검.
- `verify_results.py`: 31개 round, 301개 frame, 파일 형식, 기록 hash와 재계산 값, 실행 N/team, Worker 완료 로그를 검사.
- 원격 서버 화면/배포 정보/시연 영상: **실제로 원격에서 돌렸다는 별도 증거**. 로컬 파일의 `random_n` 같은 메타데이터만으로 원격 실행을 증명하지는 못함.

`tools/reference.py`는 통신 없는 개발용 계산이다. 정식 N=1 기준은 `assigner.py --n 1`과 Worker 한 개를 연결해서 얻는다.

## 6. 실측 지표를 설명하기

- Round 시간: Main이 그 Round를 시작한 뒤 N개 결과를 모두 받아 깨어날 때까지.
- Barrier 대기: 같은 Round의 마지막 RESULT 도착 시각 − 첫 RESULT 도착 시각.
- Worker 계산시간: 전체 ROUND/Halo 수신 후부터 계산·RESULT 송신 완료까지.
- 전송량: 명령과 그림, LF까지 포함한 TCP 애플리케이션 메시지 바이트. 10번째 Round에는 띠 전체를 추가하므로 커진다.
- 전체 처리량: 3,000 ÷ 전체 실행 초. 네트워크 지연과 PC 부하도 영향을 주므로 N이 많다고 항상 빨라지지는 않는다.

실측값은 `summary.json`, `metrics.json`, `Worker{k}.json`과 로그에서 읽는다. 서로 겹쳐 실행한 실험은 부하가 달라지므로 그것만으로 N의 성능 효과를 단정하지 않는다.
