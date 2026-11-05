# G9 HW4 시연 영상 준비

이 문서는 **촬영 안내서**다. 영상이 촬영·업로드되었다는 의미가 아니다.
최종 영상은 약 5분, 이름은 `G9HW4.mp4`, 다운로드 가능한 링크는 `download.txt`에 넣는다.

## 촬영 전 준비

- 화면은 로컬 PowerShell, 원격 SSH 터미널, G9 그림 미리보기, GIF, 검증 결과를 준비한다.
- 발표자/조원 이름과 학번은 팀에서 확인하여 Readme에 채운다.
- Assigner는 외부 서버, Worker는 로컬 PC임을 화면과 설명으로 구분한다.
- 원격 서버의 과제 TCP 포트는 **9000**이다. SSH 접속 자체는 기본 **22**번 포트다.
- `.pem` 내용이나 클라우드 인증 정보가 화면에 나오지 않게 한다. 키는 Downloads에 두고 저장소에 복사하지 않는다.
- 재촬영은 새 `demo1`, `demo2` 출력 폴더를 사용한다. 기존 실행 폴더는 덮어쓰지 않는다.
- 성능 비교를 보여 주려면 두 실행을 **하나씩 순서대로** 진행한다. 동시에 실행한 결과로 N에 따른 성능 향상을 주장하지 않는다.

## 약 5분 구성

| 영상 구간 | 보여 줄 화면 | 설명 핵심 |
|---|---|---|
| 0:00~0:45 | canvas0/1/2 미리보기와 검사 출력 | 세 그림 모두 G9, 서로 다른 문구/위치, 80×160, LF, 점 비율과 획 조건 |
| 0:45~1:10 | 구조와 주요 코드 | 외부 Assigner, 로컬 N개 Worker, TCP Star, Halo와 Barrier |
| 1:10~2:10 | 실제 원격 실행 1 시작/진행/종료 | Assigner에서 무작위 N 표시 → 그 수만큼 로컬 Worker → 3,000 Round → 종료 |
| 2:10~3:10 | 실제 원격 실행 2 시작/진행/종료 | 첫 실행과 다른 무작위 N임을 확인하고 같은 절차 수행 |
| 3:10~3:50 | G9 GIF 재생 | 초기 그림, Rule1→Rule2→Rule3 변화, Round 및 Worker 띠 표시 |
| 3:50~4:35 | RoundHash 및 hash_result, 검증 명령 | N=1과 두 분산 실행의 31개 hash 및 최종 hash가 일치 |
| 4:35~5:00 | 로그/실측표/소스 위치 | Barrier·계산시간·통신량의 의미, 실제 결과와 구현 설명 |

전체 실행이 오래 걸리면 **실제 실행을 녹화한 뒤 대기 구간만 배속/편집**하고 화면에 배속 또는 경과 시간 생략을 표시한다. 시작의 N, Worker 접속, 진행, 3,000 Round 완료, 실제 hash 확인 장면은 남긴다. 아직 끝나지 않은 실행을 완료된 것처럼 편집하지 않는다.

## 실행 명령 예시

아래 명령은 로컬 저장소 폴더를 현재 디렉터리로 두고 사용한다. 이름에 `demo1`을 사용한 기록이 이미 있으면 `demo3`처럼 새 이름을 선택한다.

### 1. 그림 검사

```powershell
python tools/check_canvas.py canvas/canvas0.txt canvas/canvas1.txt canvas/canvas2.txt
```

자동 검사 출력과 `output/previews/canvas0.png`~`canvas2.png`를 함께 보여 준다. 큰 G9, 문구 두 개 이상, 서로 다른 위치는 사람이 눈으로 설명한다. 그림을 변경했다면 서버의 canvas도 갱신하고 기준값부터 모든 결과를 다시 만든다.

### 2. 원격 Assigner 시작

PowerShell에서 키 경로만 변수로 지정한다. 파일의 내용을 출력하지 않는다.

```powershell
$sshKey = "$env:USERPROFILE\Downloads\HaEeee.pem"
ssh -i $sshKey ubuntu@13.61.180.113
```

SSH로 접속한 **서버 터미널**에서 실행한다.

```bash
cd /home/ubuntu/hw4-g9-20261105
python3 assigner.py --port 9000 --team 9 --canvas canvas --out runs/demo1
```

**Assigner에는 `--n`을 넣지 않는다.** `READY N=... TEAM=9 port=9000`에 나온 실제 N을 확인한다. 실행 인자를 사용해 N을 억지로 다르게 만들면 제출용 무작위 조건을 만족하지 않는다.

### 3. 로컬 Worker 실행

별도의 **로컬 PowerShell**에서 원격 화면에 나온 N을 입력한다.

```powershell
$workerCount = [int](Read-Host "원격 READY에 표시된 N")
python tools/run_workers.py --host 13.61.180.113 --port 9000 --n $workerCount --out runs/demo1_workers
```

여기서 Worker 실행기의 `--n`은 **원격이 정한 수만큼 프로세스를 시작하는 옵션**이다. 각 Worker의 번호와 담당 띠는 여전히 ASSIGN으로 받는다.

원격의 `PROGRESS ... round=100/3000` 및 최종 `PASS ... 3000 rounds`와 로컬의 Worker 완료 메시지를 보여 준다. 각 Worker 로그의 ASSIGN/TERMINATE도 확인한다.

### 4. 두 번째 실행

첫 실행이 완료된 후 같은 서버 명령의 출력 폴더만 `runs/demo2`로 바꾼다. Worker 폴더도 `runs/demo2_workers`로 바꾼다. 두 번째 무작위 N이 첫 N과 같으면 해당 실행을 완료한 뒤 새 출력 폴더로 다시 실행한다. 서로 다른 N의 완료 기록 두 개를 영상과 검증에 사용한다.

### 5. 원격 결과 가져오기

로컬 PowerShell에서 실행한다. 아래 로컬 `runs/demo1`, `runs/demo2`가 없는 상태에서 시작한다.

```powershell
scp -i $sshKey -r ubuntu@13.61.180.113:/home/ubuntu/hw4-g9-20261105/runs/demo1 runs/
scp -i $sshKey -r ubuntu@13.61.180.113:/home/ubuntu/hw4-g9-20261105/runs/demo2 runs/
Copy-Item -LiteralPath runs/demo1_workers -Destination runs/demo1/workers -Recurse
Copy-Item -LiteralPath runs/demo2_workers -Destination runs/demo2/workers -Recurse
```

N이 같아서 추가 실행을 했다면 위 명령의 폴더 이름도 실제로 선택한 실행에 맞춘다.

### 6. hash 확인과 GIF 생성

`runs/n1`은 **같은 G9 canvas로 Assigner+Worker 1개를 실제 실행한 기준값 폴더**여야 한다. `tools/reference.py`의 통신 없는 결과를 대신 넣지 않는다.

```powershell
python tools/verify_results.py runs/n1 runs/demo1 runs/demo2 --team 9 --out output/demo_verification
Get-Content output/demo_verification/hash_result.txt
```

제출 hash_result.txt와 영상의 두 실행이 다르다면, 각각의 `RoundHash.txt`에서 31개 hash가 제출 표의 값과 같음을 보여 준다. 서로 다른 N을 썼어도 같은 canvas와 team이면 결과는 같아야 한다.

```powershell
$gifN = [int](Read-Host "demo1의 N")
python tools/make_gif.py runs/demo1/frames output/G9HW4_demo.gif --n $gifN --team 9
```

생성 완료의 `verified 301 frames`를 확인하고 GIF를 브라우저에서 열어 재생한다. 제출 GIF·round 파일·로그는 최종 선택한 **동일 원격 실행**에서 가져와야 한다.

## 업로드 후 확인

- 다운로드 가능한 영상 링크를 `download.txt`에 적는다. URL만으로 접근 가능한지 별도 계정 또는 비로그인 창에서 확인한다.
- 링크 대상 파일이 최종 `G9HW4.mp4`인지, 음성/글자/재생이 정상인지 확인한다.
- 공식 명세는 영상 속 실행이 제출 hash_result를 만든 실행과 달라도 허용하지만, 영상의 N 둘은 서로 다르고 4~8이어야 하며 hash 결과는 제출값과 같아야 한다.
