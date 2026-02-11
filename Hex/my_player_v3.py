import heapq
import numpy as np
from player_hex import PlayerHex
from seahorse.game.action import Action
from game_state_hex import GameStateHex
from seahorse.utils.custom_exceptions import MethodNotImplementedError

class MyPlayer(PlayerHex):
    """
    Player class for Hex game using Circuit Resistance Heuristic.
    """

    def __init__(self, piece_type: str, name: str = "MyPlayer"):
        super().__init__(piece_type, name)
        self.dim = 14
        self._node_count = self.dim * self.dim + 2
        self.SOURCE = self.dim * self.dim
        self.SINK = self.dim * self.dim + 1

    def compute_action(self, current_state: GameStateHex, remaining_time: float = 15*60, **kwargs) -> Action:
        # Depth 1 is safer for the complex resistance calculation, 
        # but let's try 2 if the matrix solving is fast enough.
        _, best_action = self.alpha_beta(current_state, 1, float("-inf"), float("inf"), True)
        return best_action

    def alpha_beta(self, state: GameStateHex, depth: int, alpha: float, beta: float, maximizing_player: bool) -> tuple[float, Action]:
        if depth == 0 or state.is_done():
            return self.heuristic(state), None

        best_action = None
        if maximizing_player:
            max_eval = float("-inf")
            for action in state.generate_possible_stateful_actions():
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
            for action in state.generate_possible_stateful_actions():
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
        if state.is_done():
            scores = state.get_scores()
            my_id = self.get_id()
            my_score = scores.get(my_id, 0)
            opp_score = sum(scores.values()) - my_score
            return (my_score - opp_score) * 1000

        my_piece = self.get_piece_type()
        opp_piece = "B" if my_piece == "R" else "R"

        r_moi = self._get_equivalent_resistance(state, my_piece)
        r_adv = self._get_equivalent_resistance(state, opp_piece)

        # We want to maximize R_adv / R_moi
        # Since R can be very small, we use log or just the ratio
        # Avoid division by zero
        if r_moi < 1e-6: return 800
        if r_adv < 1e-6: return -800
        
        return r_adv / r_moi

    def _get_equivalent_resistance(self, state: GameStateHex, piece_type: str) -> float:
        board = state.get_rep()
        env = board.get_env()
        dim = board.get_dimensions()[0]
        
        # Resistance values
        R_PIECE = 0.01
        R_EMPTY = 1.0
        R_OPPONENT = 1e6

        # Map nodes
        node_res = np.full(dim * dim, R_EMPTY)
        for pos, piece in env.items():
            r, c = pos
            if piece.get_type() == piece_type:
                node_res[r * dim + c] = R_PIECE
            else:
                node_res[r * dim + c] = R_OPPONENT

        # Laplacian Matrix L
        L = np.zeros((self._node_count, self._node_count))

        def add_edge(i, j, cond):
            L[i, i] += cond
            L[j, j] += cond
            L[i, j] -= cond
            L[j, i] -= cond

        # Internal edges
        for r in range(dim):
            for c in range(dim):
                u = r * dim + c
                # Only check neighbors with index > u to avoid double counting
                for _, (_, (nr, nc)) in board.get_neighbours(r, c).items():
                    v = nr * dim + nc
                    if 0 <= nr < dim and 0 <= nc < dim and v > u:
                        # Edge resistance = average of node resistances
                        cond = 1.0 / ((node_res[u] + node_res[v]) / 2.0)
                        add_edge(u, v, cond)

        # Boundary connections
        if piece_type == "R": # Top to Bottom
            for j in range(dim):
                u = 0 * dim + j
                v = (dim - 1) * dim + j
                add_edge(self.SOURCE, u, 1.0 / (node_res[u] / 2.0))
                add_edge(v, self.SINK, 1.0 / (node_res[v] / 2.0))
        else: # Blue: Left to Right
            for i in range(dim):
                u = i * dim + 0
                v = i * dim + (dim - 1)
                add_edge(self.SOURCE, u, 1.0 / (node_res[u] / 2.0))
                add_edge(v, self.SINK, 1.0 / (node_res[v] / 2.0))

        # Solve L * phi = I
        # We set phi[SINK] = 0 and remove its row/col
        reduced_L = np.delete(L, self.SINK, axis=0)
        reduced_L = np.delete(reduced_L, self.SINK, axis=1)
        
        I = np.zeros(self._node_count - 1)
        I[self.SOURCE] = 1.0 # Inject 1A at Source
        
        try:
            phi = np.linalg.solve(reduced_L, I)
            r_eq = phi[self.SOURCE] # R_eq = (phi[SOURCE] - phi[SINK]) / I_total
            return r_eq
        except np.linalg.LinAlgError:
            return 1e6 # Disconnected
