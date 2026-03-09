import heapq
from player_hex import PlayerHex
from seahorse.game.action import Action
from game_state_hex import GameStateHex
from seahorse.utils.custom_exceptions import MethodNotImplementedError

class MyPlayer(PlayerHex):
    """
    Player class for Hex game

    Attributes:
        piece_type (str): piece type of the player "R" for the first player and "B" for the second player
    """

    def __init__(self, piece_type: str, name: str = "MyPlayer"):
        """
        Initialize the PlayerHex instance.

        Args:
            piece_type (str): Type of the player's game piece
            name (str, optional): Name of the player (default is "bob")
        """
        super().__init__(piece_type, name)

    def compute_action(self, current_state: GameStateHex, remaining_time: float = 15*60, **kwargs) -> Action:
        """
        Use the minimax algorithm to choose the best action based on the heuristic evaluation of game states.

        Args:
            current_state (GameState): The current game state.

        Returns:
            Action: The best action as determined by minimax.
        """
        _, best_action = self.alpha_beta(current_state, 2, float("-inf"), float("inf"), True)
        return best_action

    def alpha_beta(self, state: GameStateHex, depth: int, alpha: float, beta: float, maximizing_player: bool) -> tuple[float, Action]:
        """
        Alpha-Beta pruning algorithm.
        """
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
        """
        Heuristic evaluation using the Two-Distance (Dijkstra) strategy.
        Score = Distance_Opponent - Distance_Me
        """
        if state.is_done():
            scores = state.get_scores()
            my_id = self.get_id()
            my_score = scores.get(my_id, 0)
            opp_score = sum(scores.values()) - my_score
            return (my_score - opp_score) * 1000

        my_piece = self.get_piece_type()
        opp_piece = "B" if my_piece == "R" else "R"

        d_moi = self._get_shortest_path_distance(state, my_piece)
        d_adv = self._get_shortest_path_distance(state, opp_piece)

        # Handle cases where a path is completely blocked
        if d_moi == float("inf"): return -500
        if d_adv == float("inf"): return 500

        return d_adv - d_moi

    def _get_shortest_path_distance(self, state: GameStateHex, piece_type: str) -> float:
        """
        Dijkstra algorithm to find the minimum number of stones needed to complete a path.
        Empty cells weigh 1, own stones weigh 0, opponent stones are obstacles.
        """
        board = state.get_rep()
        env = board.get_env()
        rows, cols = board.get_dimensions()
        
        pq = [] # (distance, row, col)
        dist_map = {}

        # Initialization
        if piece_type == "R": # Red: Top to Bottom
            for j in range(cols):
                piece = env.get((0, j))
                if piece is None:
                    d = 1
                elif piece.get_type() == "R":
                    d = 0
                else:
                    continue
                dist_map[(0, j)] = d
                heapq.heappush(pq, (d, 0, j))
        else: # Blue: Left to Right
            for i in range(rows):
                piece = env.get((i, 0))
                if piece is None:
                    d = 1
                elif piece.get_type() == "B":
                    d = 0
                else:
                    continue
                dist_map[(i, 0)] = d
                heapq.heappush(pq, (d, i, 0))

        while pq:
            d, r, c = heapq.heappop(pq)

            if d > dist_map.get((r, c), float("inf")):
                continue

            # Target reached
            if (piece_type == "R" and r == rows - 1) or (piece_type == "B" and c == cols - 1):
                return d

            # Explore neighbors
            for _, (_, (nr, nc)) in board.get_neighbours(r, c).items():
                if 0 <= nr < rows and 0 <= nc < cols:
                    neighbor_piece = env.get((nr, nc))
                    if neighbor_piece is None:
                        weight = 1
                    elif neighbor_piece.get_type() == piece_type:
                        weight = 0
                    else:
                        continue # Obstacle

                    new_dist = d + weight
                    if new_dist < dist_map.get((nr, nc), float("inf")):
                        dist_map[(nr, nc)] = new_dist
                        heapq.heappush(pq, (new_dist, nr, nc))

        return float("inf")
