# G9 HW4 실측 및 검증 기록

작성일: 2026-11-05 (KST). 프로그램 로그 시각은 **UTC**, 소요시간은 `time.perf_counter()` 기준이다.
이 기록은 저장된 실행 파일 및 측정 JSON을 근거로 한다. 조원 이름·학번·역할과 영상 링크는 아직 입력하지 않았으며, ZIP 생성은 사용자의 요청에 따라 보류했다.

## 실행 환경과 근거

- Assigner: AWS EC2 **t3.small**, **eu-north-1**, Ubuntu **26.04 LTS**, Python **3.14.4**. 인스턴스 유형과 리전은 서버 IMDSv2 조회로 확인했다.
- Worker: 같은 Windows PC의 Python **3.13**, N개 프로세스. 원격 과제 통신 포트는 TCP **9000**.
- 기준값: 같은 프로그램을 로컬 TCP, N=1로 실행했다. 통신 없는 reference 프로그램을 제출 기준값 대신 사용하지 않았다.
- `runs/n1`, `runs/remote1`, `runs/remote2`의 `run.json`, `summary.json`, `metrics.json`, `Assigner.txt`, `workers/Worker{k}.json` 및 `.txt`가 실행별 원자료다.
- `remote1`과 `remote2`는 일부 시간이 겹쳐 실행되었다. 동시 실행 부하를 통제하지 않았으므로 N의 순수 성능 효과를 비교하는 벤치마크가 아니다.

## 정확성 검증

| 검사 | 근거 | 확인 내용 |
|---|---|---|
| 단위·오류 주입 테스트 **19/19 PASS** | `tests/test_rules.py` 8개, `test_protocol.py` 8개, `test_verify_results.py` 3개 | 공식 규칙 답안, 덧칠/변환, Halo, 이중 버퍼, 조번호·원래 y, TCP 조각 수신과 공백, 단절/timeout/잘못된 Round, 손상 증거 거부 |
| G11 통신 없는 전체 계산 | `output/reference_g11_verified/RoundHash.txt` | 공식 G11 hash 31개와 31/31 일치; 저장 파일에서 다시 계산한 hash도 31/31 일치 |
| G11 TCP N=7 | `runs/g11_tcp7/RoundHash.txt` | 공식 G11 hash 31개와 31/31 일치; 저장 파일 재계산도 31/31 일치 |
| G9 전체 계산과 TCP N=1 | `output/reference_g9`, `runs/n1` | 31/31 일치; 각 저장 파일 hash 재계산 일치 |
| G9 로컬 TCP N=4,5,6,8 | `runs/local4`, `local5`, `local6`, `local8` | 모든 실행이 N=1과 31/31 일치; 각 저장 파일 hash 재계산도 31/31 일치 |
| G9 원격 TCP N=8 및 N=7 | `runs/remote1`, `runs/remote2` | N=1과 모든 31개 hash 일치; 최종 검증 PASS, N은 무작위 8/7 |

작은 공식 테스트와 G11 공개 정답 비교는 **규칙 정확성**을, 다른 N의 실행 결과 비교는 **분할·Halo·Barrier의 동일 결과**를 확인한다. 메타데이터나 hash 일치만으로 원격 배포가 증명되는 것은 아니므로 실제 원격 실행 장면과 배포 정보를 별도로 제시한다.

재현 명령:

```powershell
python -m unittest discover -s tests -v
python tools/verify_results.py runs/n1 runs/remote1 runs/remote2 --team 9 --out output/verification
```

두 번째 명령은 31개의 round 파일 형식/ASCII/LF/기록 hash, 세 실행의 동일 hash, N=1 및 서로 다른 무작위 N, 301개 frame, 일치하는 frame/round, 3,000 Round 완료 로그와 Worker 기록을 검사한다. 실제 최종 결과는 **TOTAL 31/31 SAME -> PASS**이며 `output/verification/hash_result.txt`와 `verification.json`에 기록했다. 최종 hash는 세 실행 모두 **312bc0e2**다. 교수 제공 `verify_run.py`도 세 실행 각각 형식 31/31, 기록/계산 hash 31/31 PASS였다.

단위 테스트는 19개 모두 통과했다(검증 시 5.200초). `output/G9HW4.gif`는 `remote1` N=8의 301개 frame에서 생성했으며 실제 GIF 디코딩으로 301장과 지연시간을 확인했다. 파일 크기는 3,794,687바이트(약 3.79 MB)다. 첫 상태는 canvas0, 마지막 상태는 round3000과 연결된다.

## 성능 실측

세 실행 모두 3,000 Round를 완료했다. 다음 값은 각 실행의 실제 JSON에서 읽고 소수점 셋째 자리로 반올림했다.

| 지표 | 로컬 N=1 | 원격1 N=8 | 원격2 N=7 |
|---|---:|---:|---:|
| 전체 실행시간 (초) | 12.709 | 939.983 | 955.998 |
| 처리량 (Round/초) | 236.053 | 3.192 | 3.138 |
| Round 평균 (ms) | 4.230 | 313.310 | 318.649 |
| Round 최대 (ms) | 20.295 | 686.534 | 326.911 |
| Barrier 평균 (ms) | 0.000 | 11.368 | 19.329 |
| Barrier 최대 (ms) | 0.000 | 382.374 | 28.125 |
| 일반 Round 평균 (bytes) | 668.260 | 5346.080 | 4677.820 |
| 전체 띠 Round 평균 (bytes) | 13548.260 | 18226.080 | 17557.820 |

Worker별 실측은 `runs/<실행>/workers/Worker{k}.json`, 마지막 열은 Assigner의 `slowest_counts`에서 읽었다. 모든 Worker는 3,000 Round를 완료했다.

| 실행 | Worker | 띠 높이 | 평균 계산 (ms) | 최대 계산 (ms) | 가장 늦은 횟수 / 3000 |
|---|---|---:|---:|---:|---:|
| n1 (N=1) | W0 | 80 | 3.913 | 19.294 | 3000 |
| remote1 (N=8) | W0 | 10 | 1.270 | 5.677 | 0 |
| remote1 (N=8) | W1 | 10 | 1.542 | 6.454 | 1 |
| remote1 (N=8) | W2 | 10 | 1.562 | 5.819 | 0 |
| remote1 (N=8) | W3 | 10 | 1.673 | 5.947 | 0 |
| remote1 (N=8) | W4 | 10 | 1.366 | 6.091 | 357 |
| remote1 (N=8) | W5 | 10 | 1.629 | 7.053 | 0 |
| remote1 (N=8) | W6 | 10 | 1.715 | 6.647 | 1 |
| remote1 (N=8) | W7 | 10 | 1.443 | 6.222 | 2641 |
| remote2 (N=7) | W0 | 11 | 1.123 | 6.175 | 0 |
| remote2 (N=7) | W1 | 11 | 1.076 | 5.542 | 0 |
| remote2 (N=7) | W2 | 12 | 1.656 | 7.839 | 0 |
| remote2 (N=7) | W3 | 11 | 1.533 | 6.733 | 0 |
| remote2 (N=7) | W4 | 12 | 1.637 | 6.776 | 0 |
| remote2 (N=7) | W5 | 11 | 1.036 | 5.954 | 2998 |
| remote2 (N=7) | W6 | 12 | 1.556 | 7.355 | 2 |

## 측정 해석과 한계

- Round 시간에는 네트워크 왕복, Worker 계산, 대기·스케줄링이 함께 들어간다. Worker 계산시간은 수신 완료 후부터 RESULT 송신 완료까지이며 네트워크 전체 왕복과 같은 지표가 아니다.
- Barrier 대기시간은 각 Round에서 **마지막 RESULT 도착 − 첫 RESULT 도착**이다. N=1은 두 시각이 같으므로 0이다.
- `slowest_counts`는 3,000 Round 중 각 Worker가 가장 늦게 도착한 횟수다. 한 Worker가 늦는 원인을 띠 높이 하나로 단정할 수 없다.
- `normal_bytes_avg`는 일반 2,700 Round, `full_bytes_avg`는 전체 띠를 추가하는 300 Round의 평균이다. 둘의 차이는 전체 80×160 그림과 LF 80개에 해당하는 **12,880바이트**다. TCP/IP 헤더 바이트는 포함하지 않는다.
- 원격 Round 평균은 약 **313~319ms**인 반면 Worker 평균 계산은 약 **1.0~1.7ms**다. 이 큰 차이는 원격 네트워크 왕복 및 통신 대기가 실행시간의 큰 비중을 차지함을 시사한다. 순수 RTT를 별도로 분리 측정한 결과는 아니다.
- N=7의 12행 Worker 평균은 1.56~1.66ms이며, 11행 Worker 평균은 1.04~1.53ms다. 계산량과 띠 높이의 관계는 보이지만 가장 늦게 도착한 W5는 11행이다. 도착 순서는 계산시간 외에 전송·스케줄링의 영향도 받는다.
- 두 원격 실행이 겹쳤고, 로컬 기준값도 다른 시점에 측정되었다. 따라서 이 표로 N=7 또는 N=8의 속도 향상률을 주장하지 않는다.
- `n1` 및 `remote1`은 100-Round BARRIER 로그에 통신량 필드가 추가되기 전 코드로 실행했다. 각 Round의 `metrics.json`과 최종 `summary.json`/TERMINATE에는 실제 전송량이 있다. 현재 코드는 100-Round BARRIER에도 일반/전체 띠 평균 바이트를 기록한다. 기존 로그를 나중에 덧붙여 고치지는 않았다.

## 제출 전 남은 일

- 조원 이름·학번·실제 역할 및 개인별 느낀 점 입력.
- `docs/DEMO_GUIDE.md`에 따라 실제 원격 실행 두 회를 포함한 약 5분 영상 촬영 및 공유 권한 확인.
- `download.txt`에 실제 다운로드 링크 입력.
- ZIP은 아직 만들지 않는다. 사용자가 요청하면 최종 자료를 확인하고 패키징한다.
