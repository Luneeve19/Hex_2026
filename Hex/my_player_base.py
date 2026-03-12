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

    
    def _evaluate_state(self, state: GameStateHex) -> float:
        """
        Heuristic evaluation function for the game state.

        Args:
            state (GameState): The game state to evaluate.
        Returns:
            float: The heuristic value of the state.
        """

        # run dijkstra to find the minimum path for player to win

        my_distance = self._dijkstra(state, self.piece_type)

        # run dijkstra to find the minimum path for opponent to win

        opponent_piece = "B" if self.piece_type == "R" else "R"
        opponent_distance = self._dijkstra(state, opponent_piece)

        # return the difference between the two paths as the heuristic value

        return opponent_distance - my_distance

    def _dijkstra(self, state: GameStateHex, player_piece: str) -> int:
        """
        Dijkstra's algorithm to find the shortest path for a player to win.

        Args:
            state (GameState): The game state to evaluate.
            player_piece (str): The piece type of the player ("R" or "B").
        
        Returns:
            int: The length of the shortest path for the player to win.
        """

        # implement
        board = state.get_rep()
        env = board.get_env()
        rows, cols = board.get_dimensions()

        console.log(f"Running Dijkstra for player {player_piece} on a {rows}x{cols} board")

        return 0
    
    def _alpha_beta(self, state: GameStateHex, depth: int, alpha: float, beta: float, maximizing_player: bool, time_limit: float) -> tuple[float, Action]:
        """
        Minimax algorithm with alpha-beta pruning to find the best action.

        Args:
            state (GameState): The current game state.
            depth (int): The maximum depth of the search tree.
            alpha (float): The best value that the maximizing player can guarantee at the current level or above.
            beta (float): The best value that the minimizing player can guarantee at the current level or above.
            maximizing_player (bool): True if the current player is the maximizing player, False otherwise.
            time_limit (float): The remaining time for the player to make a move.

        Returns:
            tuple[float, Action]: A tuple containing the heuristic value of the best action and the best action itself.
        """

        # implement
        if depth == 0 or state.is_done(): # Check your engine's specific 'game over' method
            return self._evaluate_state(state), None
        
        possible_actions = state.get_possible()

