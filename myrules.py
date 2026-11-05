"""HW4 evolution rules shared by the Worker and the official rule-test kit.

A work board has a top halo, h owned rows, and a bottom halo. Cell functions
wrap columns only: vertical neighbours are read from the supplied halo rows.
The input is never updated while calculating a round (double buffering).

세 규칙 모두 "현재 상태 읽기 → 새 상태 쓰기"를 분리(이중 버퍼)해야
계산 순서가 결과에 영향을 주지 않는다.
"""

# Rule3(Cyclic Ripple)에서 사용하는 10단계 문자 램프
# 공백(' ')도 레벨 0으로 참여한다
RAMP = " .:-=+*#%@"
# 각 문자의 다음 단계를 미리 딕셔너리로 만들어 두면 매번 인덱스 계산 안 해도 됨
_NEXT = {char: RAMP[(level + 1) % len(RAMP)] for level, char in enumerate(RAMP)}


def _neighbours(w, i, x):
    """8방향(무어) 이웃을 반환. 좌우는 열 wrap, 상하는 Halo 행에서 읽는다."""
    width = len(w[0])
    left, right = (x - 1) % width, (x + 1) % width
    above, row, below = w[i - 1], w[i], w[i + 1]
    return (above[left], above[x], above[right], row[left], row[right],
            below[left], below[x], below[right])


def rule1_cell(w, i, x):
    """Text Life B3/S23: 탄생은 이웃 3개, 생존은 이웃 2~3개.

    탄생 시 문자 결정: 이웃 셋 중 다수결(2:1)이면 그 문자,
    셋 다 다르면 ASCII 코드가 가장 작은 문자를 선택.
    """
    alive = [char for char in _neighbours(w, i, x) if char != " "]
    current = w[i][x]
    if current != " ":
        return current if len(alive) in (2, 3) else " "
    if len(alive) != 3:
        return " "
    # 탄생하는 셀의 문자: 다수결 → 동률이면 min
    a, b, c = alive
    if a == b or a == c:
        return a
    if b == c:
        return b
    return min(a, b, c)


def rule2_cell(w, i, x):
    """Brian's Brain: 발화(@) → 불응(+) → 빈칸( ) 의 3상태 순환.

    빈칸일 때 이웃 중 발화 상태가 정확히 2개면 새로 발화한다.
    8이웃(무어 이웃)을 사용한다.
    """
    current = w[i][x]
    if current == "@":        # 발화 → 불응기
        return "+"
    if current == "+":        # 불응기 → 빈칸
        return " "
    return "@" if _neighbours(w, i, x).count("@") == 2 else " "


def rule3_cell(w, i, x):
    """Cyclic Ripple: 상하좌우 4이웃(폰 노이만 이웃)만 본다.

    현재 문자의 "다음 단계" 문자가 4이웃 중 하나라도 있으면
    다음 단계로 올라가고, 없으면 현재 유지.
    Rule1·2와 달리 대각선을 보지 않는 것이 핵심 차이.
    """
    current = w[i][x]
    successor = _NEXT[current]
    width = len(w[0])
    # 상·하·좌·우 중 하나라도 successor면 전이
    if (w[i - 1][x] == successor or w[i + 1][x] == successor
            or w[i][(x - 1) % width] == successor
            or w[i][(x + 1) % width] == successor):
        return successor
    return current


def band(w, cell):
    """Calculate owned rows only, returning a fresh board without halo rows.

    성능 참고: bytearray 변환(int 비교)을 시도했으나, CPython의 단일 문자
    인터닝과 리스트 컴프리헨션 최적화 덕분에 현재의 list-of-str이 더 빠름.
    (bytearray(generator) 구성 비용 > 리스트 컴프리헨션, 실측 17초→30초 역전)
    """
    return [[cell(w, i, x) for x in range(len(w[0]))]
            for i in range(1, len(w) - 1)]


def whole(board, cell):
    """단일 프로세스용 전체 보드 계산. 맨 아래를 위 Halo, 맨 위를 아래 Halo로 연결(토러스)."""
    return band([board[-1]] + board + [board[0]], cell)


def rule1(board):
    return whole(board, rule1_cell)


def rule2(board):
    return whole(board, rule2_cell)


def rule3(board):
    return whole(board, rule3_cell)


def repaint(w, c):
    """캔버스의 획(공백·점 제외)을 작업판 위에 덮어쓴다.

    Halo 행도 함께 덧칠해야 경계 칸이 내부 칸과 같은 초기 상태를 갖는다.
    Worker에서 w는 [위Halo + 자기띠 + 아래Halo], c도 같은 크기(h+2줄).
    """
    for row, paint in zip(w, c):
        for x, char in enumerate(paint):
            if char not in " .":
                row[x] = char


def to_brian(w):
    """r=1000 덧칠 후 호출: 공백이 아닌 모든 칸을 발화('@')로 통일.

    Brian's Brain은 @, +, 공백의 3상태만 쓰기 때문에
    기존 Rule1 문자들을 그대로 두면 규칙이 동작하지 않는다.
    """
    for row in w:
        for x, char in enumerate(row):
            if char != " ":
                row[x] = "@"


def to_cyclic(w, ytop, team):
    """r=2000 덧칠 후 호출: 빈칸을 RAMP 문자로 채워 Cyclic Ripple 초기 상태를 만든다.

    ytop은 작업판 첫 행(위 Halo)의 전체 보드 y좌표.
    수식 (7*x + 3*y + x*y%11 + team) % 10 으로 위치·팀마다 다른 패턴 생성.
    이미 RAMP에 있는 문자는 그대로 유지 → 캔버스 획이 초기 파동 원점이 된다.
    team 값이 다르면 결과가 달라지므로 반드시 올바른 team을 넣어야 한다.
    """
    for i, row in enumerate(w):
        y = (ytop + i) % 80   # 로컬 인덱스 → 전체 보드의 y좌표
        for x, char in enumerate(row):
            if char == " " or char not in RAMP:
                row[x] = RAMP[(7 * x + 3 * y + (x * y % 11) + team) % 10]
