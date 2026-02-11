import heapq

def _dijkstra_from_side(state, piece_type, side):
    board = state.get_rep()
    env = board.get_env()
    rows, cols = board.get_dimensions()
    pq, dist = [], {}
    if piece_type == "R":
        row = 0 if side == "START" else rows - 1
        for j in range(cols):
            p = env.get((row, j))
            d = 1 if p is None else (0 if p.get_type() == "R" else None)
            if d is not None: dist[(row, j)] = d; heapq.heappush(pq, (d, row, j))
    else:
        col = 0 if side == "START" else cols - 1
        for i in range(rows):
            p = env.get((i, col))
            d = 1 if p is None else (0 if p.get_type() == "B" else None)
            if d is not None: dist[(i, col)] = d; heapq.heappush(pq, (d, i, col))
    while pq:
        d, r, c = heapq.heappop(pq)
        if d > dist.get((r, c), float("inf")): continue
        for _, (_, (nr, nc)) in board.get_neighbours(r, c).items():
            if 0 <= nr < rows and 0 <= nc < cols:
                p = env.get((nr, nc))
                if p is None: weight = 1
                elif p.get_type() == piece_type: weight = 0
                else: continue
                if d + weight < dist.get((nr, nc), float("inf")):
                    dist[(nr, nc)] = d + weight; heapq.heappush(pq, (d + weight, nr, nc))
    return dist

def get_criticality_map(state):
    board = state.get_rep()
    rows, cols = board.get_dimensions()
    d_top = _dijkstra_from_side(state, "R", "START")
    d_bot = _dijkstra_from_side(state, "R", "END")
    d_left = _dijkstra_from_side(state, "B", "START")
    d_right = _dijkstra_from_side(state, "B", "END")
    crit_map = {}
    for r in range(rows):
        for c in range(cols):
            if (r, c) not in board.get_env():
                r_score = d_top.get((r, c), 99) + d_bot.get((r, c), 99)
                b_score = d_left.get((r, c), 99) + d_right.get((r, c), 99)
                crit_map[(r, c)] = -(r_score + b_score)
    return crit_map
