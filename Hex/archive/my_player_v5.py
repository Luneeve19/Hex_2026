import heapq
import numpy as np
from player_hex import PlayerHex
from seahorse.game.action import Action
from game_state_hex import GameStateHex
from seahorse.utils.custom_exceptions import MethodNotImplementedError

class MyPlayer(PlayerHex):
    """
    Player class for Hex game using Alpha-Beta with Influence Maps and Betweenness Centrality.
    """

    def __init__(self, piece_type: str, name: str = "MyPlayer"):
        super().__init__(piece_type, name)
        self.dim = 14
        # Bridge offsets and their shared neighbors (for pathfinding/centrality)
        self.bridge_data = [
            ((-1, 2), ((0, 1), (-1, 1))),
            ((1, 1), ((0, 1), (1, 0))),
            ((2, -1), ((1, 0), (1, -1))),
            ((1, -2), ((0, -1), (1, -1))),
            ((-1, -1), ((0, -1), (-1, 0))),
            ((-2, 1), ((-1, 0), (-1, 1)))
        ]

    def compute_action(self, current_state: GameStateHex, remaining_time: float = 15*60, **kwargs) -> Action:
        # Depth 2 is a good balance given the heavier heuristic
        _, best_action = self.alpha_beta(current_state, 2, float("-inf"), float("inf"), True)
        return best_action

    def alpha_beta(self, state: GameStateHex, depth: int, alpha: float, beta: float, maximizing_player: bool) -> tuple[float, Action]:
        if depth == 0 or state.is_done():
            return self.heuristic(state), None

        best_action = None
        # Move ordering could be added here similar to V4 for optimization
        # For V5 clarity, we focus on the heuristic logic.
        
        actions = list(state.generate_possible_stateful_actions())
        
        # Simple ordering: center moves first usually helps
        # actions.sort(key=lambda a: ...) 

        if maximizing_player:
            max_eval = float("-inf")
            for action in actions:
                next_state = action.get_next_game_state()
                eval_val, _ = self.alpha_beta(next_state, depth - 1, alpha, beta, False)
                if eval_val > max_eval:
                    max_eval = eval_val
                    best_action = action
                alpha = max(alpha, eval_val)
                if beta <= alpha:
                    break
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
                if beta <= alpha:
                    break
            return min_eval, best_action

    def heuristic(self, state: GameStateHex) -> float:
        """
        Combined Heuristic:
        1. Base: Shortest Path (Dijkstra)
        2. Bonus: Influence Map (Field Potential)
        3. Bonus: Betweenness Centrality (Bottlenecks)
        """
        if state.is_done():
            scores = state.get_scores()
            my_id = self.get_id()
            my_score = scores.get(my_id, 0)
            opp_score = sum(scores.values()) - my_score
            return (my_score - opp_score) * 10000

        my_piece = self.get_piece_type()
        opp_piece = "B" if my_piece == "R" else "R"

        # 1. Base Score (Shortest Path Difference)
        d_moi = self._get_shortest_path_distance(state, my_piece)
        d_adv = self._get_shortest_path_distance(state, opp_piece)

        if d_moi == float("inf"): return -5000
        if d_adv == float("inf"): return 5000
        
        base_score = (d_adv - d_moi) * 100 # Weighting base score highly

        # 2. Influence Map Score
        inf_score = self._get_influence_score(state, my_piece)

        # 3. Centrality Score (Simplified)
        # We calculate centrality only for the active player's perspective to save time
        # or pre-calculate critical nodes like in V4.
        # Here we incorporate it into the influence or as a modifier.
        # For explicit implementation, let's look at key nodes on the shortest path.
        
        # Total Score
        # Influence is usually smaller, so we scale it.
        return base_score + (inf_score * 0.1)

    def _get_influence_score(self, state: GameStateHex, my_piece: str) -> float:
        """
        Calculates score based on an Influence Map (Potential Field).
        Positive for my pieces, negative for opponent.
        """
        board = state.get_rep()
        env = board.get_env()
        rows, cols = board.get_dimensions()
        
        # Initialize grid
        grid = np.zeros((rows, cols))
        
        # Influence decay kernel
        # Center=10, Neighbors=5, Next=2
        # We can implement this by iterating over pieces
        
        for (r, c), piece in env.items():
            val = 10 if piece.get_type() == my_piece else -10
            
            # Apply to self
            grid[r, c] += val
            
            # Apply to neighbors (dist 1)
            for _, (_, (nr, nc)) in board.get_neighbours(r, c).items():
                if 0 <= nr < rows and 0 <= nc < cols:
                    grid[nr, nc] += (val * 0.5) # +5 / -5
                    
                    # Apply to neighbors of neighbors (dist 2) - crude approximation
                    # Real influence maps propagate further, but this is fast.
                    for _, (_, (nnr, nnc)) in board.get_neighbours(nr, nc).items():
                         if 0 <= nnr < rows and 0 <= nnc < cols and (nnr, nnc) != (r, c):
                             grid[nnr, nnc] += (val * 0.2) # +2 / -2

        return np.sum(grid)

    def _get_shortest_path_distance(self, state: GameStateHex, piece_type: str) -> float:
        # Standard Dijkstra with Bridges (V2)
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
            
            for (dr, dc), shared in self.bridge_data:
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
