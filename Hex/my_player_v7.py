import heapq
from player_hex import PlayerHex
from seahorse.game.action import Action
from game_state_hex import GameStateHex
from seahorse.utils.custom_exceptions import MethodNotImplementedError

class MyPlayer(PlayerHex):
    """
    Player class Version 7: V6 (Panic Defense) + Center Priority + Advanced Blocking.
    Prioritizes the center early and uses 'Classic Blocks' (blocking at a distance) 
    to prevent the opponent from flowing around defensive pieces.
    """

    def __init__(self, piece_type: str, name: str = "MyPlayer"):
        super().__init__(piece_type, name)
        self.bridge_data = [
            ((-1, 2), ((0, 1), (-1, 1))),
            ((1, 1), ((0, 1), (1, 0))),
            ((2, -1), ((1, 0), (1, -1))),
            ((1, -2), ((0, -1), (1, -1))),
            ((-1, -1), ((0, -1), (-1, 0))),
            ((-2, 1), ((-1, 0), (-1, 1)))
        ]

    def compute_action(self, current_state: GameStateHex, remaining_time: float = 15*60, **kwargs) -> Action:
        _, best_action = self.alpha_beta(current_state, 2, float("-inf"), float("inf"), True)
        return best_action

    def alpha_beta(self, state: GameStateHex, depth: int, alpha: float, beta: float, maximizing_player: bool) -> tuple[float, Action]:
        if depth == 0 or state.is_done():
            return self.heuristic(state), None

        actions = list(state.generate_possible_stateful_actions())
        
        # --- MOVE ORDERING (CRITICALITY + BIAS) ---
        crit_map = self._get_criticality_map(state)
        def score_action(action):
            curr_env = state.get_rep().get_env()
            next_env = action.get_next_game_state().get_rep().get_env()
            for pos in next_env:
                if pos not in curr_env:
                    rows, cols = state.get_rep().get_dimensions()
                    cr, cc = rows // 2, cols // 2
                    dist_to_center = abs(pos[0] - cr) + abs(pos[1] - cc)
                    center_bias = max(0, 20 - state.get_step()) / (1 + dist_to_center)
                    return crit_map.get(pos, 0) + center_bias
            return 0
        actions.sort(key=score_action, reverse=True)

        best_action = None
        if maximizing_player:
            max_eval = float("-inf")
            for action in actions:
                next_state = action.get_next_game_state()
                eval_val, _ = self.alpha_beta(next_state, depth - 1, alpha, beta, False)
                if eval_val > max_eval:
                    max_eval = eval_val
                    best_action = action
                alpha = max(alpha, eval_val)
                if beta <= alpha: break
            return max_eval, best_action
        else:
            min_eval = float("inf")
            for action in actions:
                next_state = action.get_next_game_state()
                eval_val, _ = self.alpha_beta(next_state, depth - 1, alpha, beta, True)
                if eval_val < min_eval:
                    min_eval = eval_val
                    best_action = action
                beta = min(beta, eval_val)
                if beta <= alpha: break
            return min_eval, best_action

    def heuristic(self, state: GameStateHex) -> float:
        if state.is_done():
            scores = state.get_scores()
            my_id = self.get_id()
            my_score = scores.get(my_id, 0)
            opp_score = sum(scores.values()) - my_score
            return (my_score - opp_score) * 50000

        my_piece = self.get_piece_type()
        opp_piece = "B" if my_piece == "R" else "R"

        # 1. Base Dijkstra with Bridges
        d_moi = self._get_shortest_path_distance(state, my_piece)
        d_adv = self._get_shortest_path_distance(state, opp_piece)

        if d_moi == float("inf"): return -10000
        if d_adv == float("inf"): return 10000

        score = (d_adv - d_moi) * 100

        # 2. PANIC MODE: Border Defense
        panic_penalty = self._get_panic_bonus(state, opp_piece)
        
        # 3. CENTER PRIORITY (Early Game)
        center_bonus = self._get_center_bonus(state)

        # 4. ADVANCED BLOCKING (Classic Block)
        blocking_score = self._get_blocking_bonus(state, opp_piece)
        
        return score - panic_penalty + center_bonus + blocking_score

    def _get_blocking_bonus(self, state, opp_piece):
        """
        Implements the 'Classic Block' strategy.
        Rewards playing ahead of the opponent's chain (dist 2) 
        and penalizes ineffective adjacent blocking (dist 1).
        """
        board = state.get_rep()
        env = board.get_env()
        rows, cols = board.get_dimensions()
        bonus = 0

        # Identify opponent pieces closest to completing their path
        opp_points = [pos for pos, piece in env.items() if piece.get_type() == opp_piece]
        if not opp_points: return 0

        my_points = [pos for pos, piece in env.items() if piece.get_owner_id() == self.get_id()]
        
        for mp in my_points:
            min_dist_to_opp = min([abs(mp[0]-op[0]) + abs(mp[1]-op[1]) for op in opp_points])
            
            # Penalize adjacent blocks (too easy to flow around)
            if min_dist_to_opp == 1:
                bonus -= 50
            # Reward blocks at distance 2 or 3 (Classic Block)
            elif min_dist_to_opp == 2:
                bonus += 150
            elif min_dist_to_opp == 3:
                bonus += 80

        return bonus

    def _get_center_bonus(self, state):
        board = state.get_rep()
        env = board.get_env()
        rows, cols = board.get_dimensions()
        cr, cc = rows // 2, cols // 2
        bonus = 0
        step = state.get_step()
        multiplier = max(0, 150 - step * 6)
        if multiplier <= 0: return 0
        for (r, c), piece in env.items():
            dist_sq = (r - cr)**2 + (c - cc)**2
            if piece.get_owner_id() == self.get_id():
                bonus += multiplier / (1 + dist_sq)
            elif piece.get_type() == ("B" if self.get_piece_type() == "R" else "R"):
                bonus -= (multiplier * 0.8) / (1 + dist_sq)
        return bonus

    def _get_panic_bonus(self, state, opp_piece):
        board = state.get_rep()
        env = board.get_env()
        rows, cols = board.get_dimensions()
        penalty = 0
        for (r, c), piece in env.items():
            if piece.get_type() == opp_piece:
                if opp_piece == "R":
                    dist_to_top, dist_to_bot = r, (rows - 1) - r
                    if dist_to_top <= 1: penalty += 800
                    if dist_to_bot <= 1: penalty += 800
                else:
                    dist_to_left, dist_to_right = c, (cols - 1) - c
                    if dist_to_left <= 1: penalty += 800
                    if dist_to_right <= 1: penalty += 800
        return penalty

    def _get_criticality_map(self, state: GameStateHex) -> dict:
        board = state.get_rep()
        rows, cols = board.get_dimensions()
        d_top = self._dijkstra_from_side(state, "R", "START")
        d_bot = self._dijkstra_from_side(state, "R", "END")
        d_left = self._dijkstra_from_side(state, "B", "START")
        d_right = self._dijkstra_from_side(state, "B", "END")
        crit_map = {}
        for r in range(rows):
            for c in range(cols):
                if (r, c) not in board.get_env():
                    r_score = d_top.get((r, c), 99) + d_bot.get((r, c), 99)
                    b_score = d_left.get((r, c), 99) + d_right.get((r, c), 99)
                    crit_map[(r, c)] = -(r_score + b_score)
        return crit_map

    def _dijkstra_from_side(self, state, piece_type, side):
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

    def _get_shortest_path_distance(self, state, piece_type):
        board = state.get_rep()
        env = board.get_env()
        rows, cols = board.get_dimensions()
        pq, dist_map = [], {}
        if piece_type == "R":
            for j in range(cols):
                piece = env.get((0, j))
                d = 1 if piece is None else (0 if piece.get_type() == "R" else None)
                if d is not None: dist_map[(0, j)] = d; heapq.heappush(pq, (d, 0, j))
        else:
            for i in range(rows):
                piece = env.get((i, 0))
                d = 1 if piece is None else (0 if piece.get_type() == "B" else None)
                if d is not None: dist_map[(i, 0)] = d; heapq.heappush(pq, (d, i, 0))
        while pq:
            d, r, c = heapq.heappop(pq)
            if d > dist_map.get((r, c), float("inf")): continue
            if (piece_type == "R" and r == rows - 1) or (piece_type == "B" and c == cols - 1): return d
            for _, (_, (nr, nc)) in board.get_neighbours(r, c).items():
                if 0 <= nr < rows and 0 <= nc < cols:
                    np = env.get((nr, nc))
                    if np is None: weight = 1
                    elif np.get_type() == piece_type: weight = 0
                    else: continue
                    if d + weight < dist_map.get((nr, nc), float("inf")):
                        dist_map[(nr, nc)] = d + weight; heapq.heappush(pq, (d + weight, nr, nc))
            for (dr, dc), shared in self.bridge_data:
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols:
                    s1r, s1c, s2r, s2c = r+shared[0][0], c+shared[0][1], r+shared[1][0], c+shared[1][1]
                    if (0 <= s1r < rows and 0 <= s1c < cols and env.get((s1r, s1c)) is None and
                        0 <= s2r < rows and 0 <= s2c < cols and env.get((s2r, s2c)) is None):
                        np = env.get((nr, nc))
                        if np is None: weight = 1
                        elif np.get_type() == piece_type: weight = 0
                        else: continue
                        if d + weight < dist_map.get((nr, nc), float("inf")):
                            dist_map[(nr, nc)] = d + weight; heapq.heappush(pq, (d + weight, nr, nc))
        return float("inf")
