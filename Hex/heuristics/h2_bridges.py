import heapq

BRIDGE_DATA = [
    ((-1, 2), ((0, 1), (-1, 1))),
    ((1, 1), ((0, 1), (1, 0))),
    ((2, -1), ((1, 0), (1, -1))),
    ((1, -2), ((0, -1), (1, -1))),
    ((-1, -1), ((0, -1), (-1, 0))),
    ((-2, 1), ((-1, 0), (-1, 1)))
]

def get_shortest_path_with_bridges(state, piece_type):
    board = state.get_rep()
    env = board.get_env()
    rows, cols = board.get_dimensions()
    pq = []
    dist_map = {}

    if piece_type == "R":
        for j in range(cols):
            piece = env.get((0, j))
            d = 1 if piece is None else (0 if piece.get_type() == "R" else None)
            if d is not None:
                dist_map[(0, j)] = d
                heapq.heappush(pq, (d, 0, j))
    else:
        for i in range(rows):
            piece = env.get((i, 0))
            d = 1 if piece is None else (0 if piece.get_type() == "B" else None)
            if d is not None:
                dist_map[(i, 0)] = d
                heapq.heappush(pq, (d, i, 0))

    while pq:
        d, r, c = heapq.heappop(pq)
        if d > dist_map.get((r, c), float("inf")): continue
        if (piece_type == "R" and r == rows - 1) or (piece_type == "B" and c == cols - 1):
            return d

        for _, (_, (nr, nc)) in board.get_neighbours(r, c).items():
            if 0 <= nr < rows and 0 <= nc < cols:
                np = env.get((nr, nc))
                if np is None: weight = 1
                elif np.get_type() == piece_type: weight = 0
                else: continue
                new_dist = d + weight
                if new_dist < dist_map.get((nr, nc), float("inf")):
                    dist_map[(nr, nc)] = new_dist
                    heapq.heappush(pq, (new_dist, nr, nc))
        
        for (dr, dc), shared in BRIDGE_DATA:
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols:
                s1r, s1c = r + shared[0][0], c + shared[0][1]
                s2r, s2c = r + shared[1][0], c + shared[1][1]
                if (0 <= s1r < rows and 0 <= s1c < cols and env.get((s1r, s1c)) is None and
                    0 <= s2r < rows and 0 <= s2c < cols and env.get((s2r, s2c)) is None):
                    np = env.get((nr, nc))
                    if np is None: weight = 1
                    elif np.get_type() == piece_type: weight = 0
                    else: continue
                    new_dist = d + weight
                    if new_dist < dist_map.get((nr, nc), float("inf")):
                        dist_map[(nr, nc)] = new_dist
                        heapq.heappush(pq, (new_dist, nr, nc))
    return float("inf")

def h2_bridges(state, player_piece):
    opp_piece = "B" if player_piece == "R" else "R"
    d_moi = get_shortest_path_with_bridges(state, player_piece)
    d_adv = get_shortest_path_with_bridges(state, opp_piece)
    if d_moi == float("inf"): return -500
    if d_adv == float("inf"): return 500
    return d_adv - d_moi
