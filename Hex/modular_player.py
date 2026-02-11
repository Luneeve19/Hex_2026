import sys
import os
# Add the current directory to sys.path to allow imports from heuristics/
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from player_hex import PlayerHex
from seahorse.game.action import Action
from game_state_hex import GameStateHex

# Import modular heuristics
from heuristics.h1_dijkstra import h1_two_distance
from heuristics.h2_bridges import h2_bridges
from heuristics.h3_circuit import h3_circuit_resistance
from heuristics.h4_criticality import get_criticality_map
from heuristics.h5_influence import h5_influence_map

class MyPlayer(PlayerHex):
    """
    A Plug & Play Hex Player.
    Change the enabled heuristics in evaluate() and move ordering in compute_action().
    """

    def __init__(self, piece_type: str, name: str = "ModularPlayer"):
        super().__init__(piece_type, name)
        # CONFIGURATION matching V4
        self.depth = 2
        self.use_move_ordering = True
        self.active_heuristics = {
            "h2": True,   # Bridges (V2/V4 Heuristic)
        }

    def compute_action(self, current_state: GameStateHex, remaining_time: float = 15*60, **kwargs) -> Action:
        _, best_action = self.alpha_beta(current_state, self.depth, float("-inf"), float("inf"), True)
        return best_action

    def alpha_beta(self, state: GameStateHex, depth: int, alpha: float, beta: float, maximizing_player: bool) -> tuple[float, Action]:
        if depth == 0 or state.is_done():
            return self.evaluate(state), None

        actions = list(state.generate_possible_stateful_actions())

        # Move Ordering (Criticality from V4)
        if self.use_move_ordering and depth == self.depth:
            crit_map = get_criticality_map(state)
            def score_move(a):
                curr = state.get_rep().get_env()
                nxt = a.get_next_game_state().get_rep().get_env()
                for p in nxt:
                    if p not in curr: return crit_map.get(p, 0)
                return 0
            actions.sort(key=score_move, reverse=True)

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

    def evaluate(self, state: GameStateHex) -> float:
        """
        Plug & Play Heuristic Combinator.
        """
        if state.is_done():
            scores = state.get_scores()
            my_score = scores.get(self.get_id(), 0)
            opp_score = sum(scores.values()) - my_score
            return (my_score - opp_score) * 10000

        total_score = 0
        p = self.get_piece_type()

        # Combine active heuristics
        if self.active_heuristics.get("h1"):
            total_score += h1_two_distance(state, p) * 100
        
        if self.active_heuristics.get("h2"):
            total_score += h2_bridges(state, p) * 100

        if self.active_heuristics.get("h3"):
            total_score += h3_circuit_resistance(state, p) * 50

        if self.active_heuristics.get("h5"):
            total_score += h5_influence_map(state, p) * 0.1

        return total_score
