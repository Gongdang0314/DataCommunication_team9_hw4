# G9 · 데이터통신 HW4 — ASCII Evolution

Python TCP 소켓으로 160×80 ASCII 그림을 3,000 Round 진화시키는 과제입니다.
**제출용 조번호는 9이며, 그림·GIF·결과도 G9입니다.** G11은 교수님 정답과 비교하는 테스트에만 사용합니다.

## 먼저 실행하기

저장소 폴더에서 PowerShell/터미널로 실행합니다. Python 3.10 이상을 사용하세요.
시뮬레이션은 표준 라이브러리만 사용하고, GIF/미리보기 생성에만 Pillow가 필요합니다.

```powershell
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python tools/check_canvas.py canvas/canvas0.txt canvas/canvas1.txt canvas/canvas2.txt
python tools/run_local.py --n 1 --team 9 --port 9000 --out runs/my_n1
```

출력 폴더는 매 실행 **새 이름**을 쓰세요. 기존 결과를 덮어쓰지 않도록 프로그램이 거부합니다.
위 명령은 실제 Assigner + Worker 1개를 실행하는 기준값 생성입니다.

## 코드 읽는 순서

| 파일 | 역할 |
|---|---|
| `tools/make_canvas.py` | G9와 문구를 직접 정의한 5×7 글꼴로 그리기, 고정 난수로 점 배치 |
| `myrules.py` | Rule1/2/3, 덧칠과 단계 변환. 통신과 독립적으로 검증 |
| `common.py` | TCP 줄 수신 버퍼, ASCII/LF 파일, hash, UTC 로그 |
| `worker.py` | 자기 띠와 Halo만 가지고 계산하고 RESULT 전송 |
| `assigner.py` | 균등 분할, 경계 중계, Mutex + CV 2개로 Round Barrier |
| `tools/run_workers.py` | 로컬 Worker N개 프로세스 실행 및 종료 확인 |
| `tools/verify_results.py` | 세 실행의 31개 hash·파일·로그·301 frame 검증 |
| `tools/make_gif.py` | 실제 분산 실행 frame에서 G9 GIF 생성 |

설명은 [코드 이해하기](docs/EXPLAIN_CODE.md), 시연 준비는 [영상 촬영 순서](docs/DEMO_GUIDE.md),
전체 조건은 [체크리스트](docs/IMPLEMENTATION_CHECKLIST.md)를 참고하세요.

## 원격 실행

외부 서버에서 (Assigner는 제출용 실행에서 `--n`을 지정하지 않습니다):

```bash
cd ~/hw4-g9-20261105
python3 -u assigner.py --team 9 --port 9000 --canvas canvas --out runs/demo1 --timeout 600
```

`READY N=... TEAM=9 port=9000`의 N을 확인한 다음 로컬에서 다음을 실행합니다.
아래의 7은 예시이며 **서버가 실제로 뽑은 N**으로 바꿔야 합니다.

```powershell
python tools/run_workers.py --host 13.61.180.113 --port 9000 --n 7 --out runs/demo1/workers
```

두 번째 실행은 새 폴더 `demo2`로 시작합니다. 무작위 N이 첫 번째와 같으면 그 시도는 제외하고 다시 실행합니다.
Worker끼리는 연결하지 않습니다. 기준 N=1은 로컬에서 가능하지만 제출용 두 분산 실행은 원격 서버에서 수행합니다.
서버 결과 폴더를 로컬로 복사하고 해당 실행의 `workers/` 로그 폴더와 합칩니다.
키 파일은 저장소 바깥 Downloads에 두며 Git과 제출 ZIP에 포함하지 않습니다.

## 검증과 GIF

```powershell
python tools/verify_results.py runs/n1 runs/remote1 runs/remote2 --team 9 --out output/verification
python tools/make_gif.py runs/remote1/frames output/G9HW4.gif --n 8 --team 9
```

경로와 GIF의 N은 실제 사용할 실행에 맞춥니다. 결과의 `TOTAL 31/31 SAME -> PASS`를 확인합니다.
`tools/verify_run.py`는 교수님 배포 원본 도구이며 각 실행을 추가 확인할 때 사용할 수 있습니다.

```powershell
python tools/verify_run.py runs/remote1 runs/remote1/RoundHash.txt
```

## 개발 검증

교수님 G11 정답을 그대로 보관한 `tests/fixtures`는 G9 제출 그림과 구분되어 있습니다.
네트워크 없이 규칙을 확인하려면 다음을 실행합니다.

```powershell
python tools/reference.py --canvas tests/fixtures/G11_sample --team 11 --out output/reference_check --expected tests/fixtures/G11_sample/RoundHash_N1.txt
```

전체 판 reference는 규칙 검사용이며 제출용 N=1 Assigner+Worker 실행을 대신하지 않습니다.
단위 테스트는 공식 정답·Halo 좌표·변환뿐 아니라 TCP 분할/합쳐진 수신, 연결 단절,
잘못된 RESULT, timeout, 손상된 검증 파일을 검사합니다.

## 제출 전

- 조원 이름·학번·역할은 `Readme.txt`에 직접 채웁니다.
- 실제 시연 영상을 촬영하고 다운로드 가능한 링크를 `download.txt`에 넣습니다.
- 성능 결과와 검증 상태는 `docs/VALIDATION.md`를 확인합니다.
- `runs/`, `output/`, `dist/`는 대량 결과이므로 Git에서 제외합니다. 소스와 canvas, 테스트는 추적 대상입니다.
- `.gitattributes`가 LF를 유지합니다. canvas를 편집기로 바꿀 때 줄 끝·공백을 변경하지 않도록 주의하세요.
- 과제의 최종 제출 파일은 `G9HW4.zip`이며, `_DRAFT` ZIP은 미완성 제출 준비본입니다.

## 자료 출처

공식 기준: 교수님 `HW4description.pdf`, 설명 자료 `HW4explanation.pdf` 및 `HW4_student_pack`.
`tools/check_canvas.py`, `tools/verify_run.py`는 배포 원본이고 GIF 도구는 배포 예제를 바탕으로 검증과 G9 표기를 보강했습니다.
테스트 fixture는 배포 정답 자료입니다. 구현과 문서는 조원이 검토하고 실제 동작을 이해한 뒤 제출해야 합니다.
