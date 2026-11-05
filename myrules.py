"""HW4 evolution rules shared by the Worker and the official rule-test kit.

A work board has a top halo, h owned rows, and a bottom halo. Cell functions
wrap columns only: vertical neighbours are read from the supplied halo rows.
The input is never updated while calculating a round (double buffering).
"""

RAMP = " .:-=+*#%@"
_NEXT = {char: RAMP[(level + 1) % len(RAMP)] for level, char in enumerate(RAMP)}


def _neighbours(w, i, x):
    width = len(w[0])
    left, right = (x - 1) % width, (x + 1) % width
    above, row, below = w[i - 1], w[i], w[i + 1]
    return (above[left], above[x], above[right], row[left], row[right],
            below[left], below[x], below[right])


def rule1_cell(w, i, x):
    """Text Life B3/S23; births inherit majority character, then ASCII minimum."""
    alive = [char for char in _neighbours(w, i, x) if char != " "]
    current = w[i][x]
    if current != " ":
        return current if len(alive) in (2, 3) else " "
    if len(alive) != 3:
        return " "
    a, b, c = alive
    if a == b or a == c:
        return a
    if b == c:
        return b
    return min(a, b, c)


def rule2_cell(w, i, x):
    """Brian's Brain: firing -> refractory -> empty; two firing neighbours birth."""
    current = w[i][x]
    if current == "@":
        return "+"
    if current == "+":
        return " "
    return "@" if _neighbours(w, i, x).count("@") == 2 else " "


def rule3_cell(w, i, x):
    """Cyclic Ripple uses only four orthogonal neighbours, including halos."""
    current = w[i][x]
    successor = _NEXT[current]
    width = len(w[0])
    if (w[i - 1][x] == successor or w[i + 1][x] == successor
            or w[i][(x - 1) % width] == successor
            or w[i][(x + 1) % width] == successor):
        return successor
    return current


def band(w, cell):
    """Calculate owned rows only, returning a fresh board without halo rows."""
    return [[cell(w, i, x) for x in range(len(w[0]))]
            for i in range(1, len(w) - 1)]


def whole(board, cell):
    """Reference whole-board calculation: add toroidal top and bottom halos."""
    return band([board[-1]] + board + [board[0]], cell)


def rule1(board):
    return whole(board, rule1_cell)


def rule2(board):
    return whole(board, rule2_cell)


def rule3(board):
    return whole(board, rule3_cell)


def repaint(w, c):
    """Overlay canvas strokes on ALL work rows, including both halos."""
    for row, paint in zip(w, c):
        for x, char in enumerate(paint):
            if char not in " .":
                row[x] = char


def to_brian(w):
    """After repaint at r=1000, all non-space cells become firing cells."""
    for row in w:
        for x, char in enumerate(row):
            if char != " ":
                row[x] = "@"


def to_cyclic(w, ytop, team):
    """Convert at r=2000 using global row coordinates, not local band indices.

    ytop is the original row of work-board row 0 (the TOP HALO). Existing
    non-space RAMP characters keep their level; spaces are converted too.
    """
    for i, row in enumerate(w):
        y = (ytop + i) % 80
        for x, char in enumerate(row):
            if char == " " or char not in RAMP:
                row[x] = RAMP[(7 * x + 3 * y + (x * y % 11) + team) % 10]
