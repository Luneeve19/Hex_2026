import time
import numpy as np
from collections import deque
from player_hex import PlayerHex
from seahorse.game.action import Action
from game_state_hex import GameStateHex

class MyPlayer(PlayerHex):
    """
    Agent "Tesla's Bridge V2 - Overclocked".
    Optimisations: Fast-Grid, BFS Pruning, Transposition Table, Numpy Vectorization.
    """

    def __init__(self, piece_type: str, name: str = "TeslaOverclocked"):
        super().__init__(piece_type, name)
        
        self.C_EMPTY = 1.0
        self.C_SUPER = 1000.0
        self.C_BRIDGE = 500.0
        
        self.adj_cache = {}
        self.center_cache = {}
        self.eval_cache = {} # Transposition Table
        
        self.bridge_offsets = [
            ((-1, 2), [(0, 1), (-1, 1)]),
            ((1, 1),  [(0, 1), (1, 0)]),
            ((2, -1), [(1, 0), (1, -1)]),
            ((1, -2), [(0, -1), (1, -1)]),
            ((-1, -1),[(0, -1), (-1, 0)]),
            ((-2, 1), [(-1, 0), (-1, 1)])
        ]

    def _init_caches(self, rows: int, cols: int):
        cr, cc = rows // 2, cols // 2
        for r in range(rows):
            for c in range(cols):
                self.center_cache[(r, c)] = (r - cr)**2 + (c - cc)**2
                
                neighbors = []
                for dr, dc in [(-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0)]:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < rows and 0 <= nc < cols:
                        neighbors.append((nr, nc))
                self.adj_cache[(r, c)] = neighbors

    def compute_action(self, current_state: GameStateHex, remaining_time: float = 15*60, **kwargs) -> Action:
        rows, cols = current_state.get_rep().get_dimensions()
        if not self.adj_cache:
            self._init_caches(rows, cols)

        # On vide le cache à chaque nouveau tour pour ne pas exploser la RAM
        self.eval_cache.clear()

        start_time = time.time()
        # On donne un peu plus de temps si on a du budget, sinon 10s max
        time_limit = start_time + min(10.0, max(2.0, remaining_time * 0.05))
        
        actions = list(current_state.generate_possible_stateful_actions())
        if not actions:
            raise ValueError("Aucune action possible")

        # Move ordering initial (très rapide)
        curr_env = current_state.get_rep().get_env()
        def root_sort(action):
            next_env = action.get_next_game_state().get_rep().get_env()
            for k in next_env:
                if k not in curr_env:
                    return self.center_cache.get(k, 100)
            return 1000
        actions.sort(key=root_sort) # Plus petit au plus grand

        best_action = actions[0]

        try:
            # Objectif : Profondeur 3 ou 4 avec les nouvelles optimisations
            for depth in range(1, 6): 
                if time.time() > time_limit: break
                
                val, action = self.alpha_beta(
                    current_state, depth, float("-inf"), float("inf"), 
                    True, time_limit
                )
                if action:
                    best_action = action
                    
        except TimeoutError:
            pass 

        return best_action

    def alpha_beta(self, state: GameStateHex, depth: int, alpha: float, beta: float, 
                   maximizing_player: bool, time_limit: float) -> tuple[float, Action]:
        if time.time() > time_limit:
            raise TimeoutError()

        if depth == 0 or state.is_done():
            return self.hybrid_heuristic(state), None

        actions = list(state.generate_possible_stateful_actions())
        if not actions: return self.hybrid_heuristic(state), None

        best_action = actions[0]

        if maximizing_player:
            max_eval = float("-inf")
            for action in actions:
                eval_val, _ = self.alpha_beta(action.get_next_game_state(), depth - 1, alpha, beta, False, time_limit)
                if eval_val > max_eval:
                    max_eval = eval_val; best_action = action
                alpha = max(alpha, eval_val)
                if beta <= alpha: break
            return max_eval, best_action
        else:
            min_eval = float("inf")
            for action in actions:
                eval_val, _ = self.alpha_beta(action.get_next_game_state(), depth - 1, alpha, beta, True, time_limit)
                if eval_val < min_eval:
                    min_eval = eval_val; best_action = action
                beta = min(beta, eval_val)
                if beta <= alpha: break
            return min_eval, best_action

    def hybrid_heuristic(self, state: GameStateHex) -> float:
        """Heuristique optimisée avec Cache et Grille Rapide."""
        if state.is_done():
            scores = state.get_scores()
            return float("inf") if scores.get(self.get_id(), 0) > 0 else float("-inf")

        board = state.get_rep()
        rows, cols = board.get_dimensions()
        my_piece = self.get_piece_type()
        opp_piece = "B" if my_piece == "R" else "R"

        # 1. CRÉATION DE LA GRILLE RAPIDE (1 = Moi, -1 = Adv, 0 = Vide)
        # C'est LA clé de l'optimisation. On lit env.get() UNE SEULE fois.
        grid = np.zeros((rows, cols), dtype=np.int8)
        env = board.get_env()
        for r in range(rows):
            for c in range(cols):
                p = env.get((r, c))
                if p is not None:
                    grid[r, c] = 1 if p.get_type() == my_piece else -1

        # 2. TRANSPOSITION TABLE
        grid_hash = grid.tobytes()
        if grid_hash in self.eval_cache:
            return self.eval_cache[grid_hash]

        # 3. LE BOUCLIER BFS (Fast-Fail)
        # Vérifie instantanément si on est coupé avant de lancer la matrice
        if not self._is_path_possible(grid, 1, rows, cols, my_piece):
            self.eval_cache[grid_hash] = -50000.0
            return -50000.0
        if not self._is_path_possible(grid, -1, rows, cols, opp_piece):
            self.eval_cache[grid_hash] = 50000.0
            return 50000.0

        # 4. L'INTELLIGENCE MATRICIELLE (Seulement si le jeu est encore ouvert)
        my_conductance = self._calculate_fast_conductance(grid, 1, rows, cols, my_piece)
        opp_conductance = self._calculate_fast_conductance(grid, -1, rows, cols, opp_piece)

        score = my_conductance - opp_conductance
        self.eval_cache[grid_hash] = score
        return score

    def _is_path_possible(self, grid: np.ndarray, player_val: int, rows: int, cols: int, piece_type: str) -> bool:
        """Un BFS ultra-rapide pour savoir si un chemin est physiquement possible."""
        visited = np.zeros((rows, cols), dtype=bool)
        queue = deque()

        if piece_type == "R": # Haut vers Bas
            for c in range(cols):
                if grid[0, c] != -player_val: # Si pas ennemi
                    queue.append((0, c))
                    visited[0, c] = True
        else: # Gauche vers Droite
            for r in range(rows):
                if grid[r, 0] != -player_val:
                    queue.append((r, 0))
                    visited[r, 0] = True

        while queue:
            r, c = queue.popleft()
            
            # Condition de victoire atteinte
            if piece_type == "R" and r == rows - 1: return True
            if piece_type == "B" and c == cols - 1: return True

            for nr, nc in self.adj_cache[(r, c)]:
                if not visited[nr, nc] and grid[nr, nc] != -player_val:
                    visited[nr, nc] = True
                    queue.append((nr, nc))
                    
        return False

    def _calculate_fast_conductance(self, grid: np.ndarray, player_val: int, rows: int, cols: int, piece_type: str) -> float:
        """Calcul matriciel utilisant la grille NumPy rapide au lieu de env.get()"""
        valid_nodes = []
        node_to_idx = {}
        idx = 0

        for r in range(rows):
            for c in range(cols):
                if grid[r, c] != -player_val: # Si c'est vide ou à nous
                    valid_nodes.append((r, c))
                    node_to_idx[(r, c)] = idx
                    idx += 1

        n_nodes = len(valid_nodes)
        if n_nodes == 0: return 0.0

        L = np.zeros((n_nodes, n_nodes), dtype=np.float64)

        for i, (r, c) in enumerate(valid_nodes):
            is_my_piece = (grid[r, c] == player_val)

            # Voisins standards
            for nr, nc in self.adj_cache[(r, c)]:
                if (nr, nc) in node_to_idx:
                    j = node_to_idx[(nr, nc)]
                    is_neighbor_my_piece = (grid[nr, nc] == player_val)
                    c_val = self.C_SUPER if (is_my_piece or is_neighbor_my_piece) else self.C_EMPTY
                    
                    L[i, j] -= c_val
                    L[i, i] += c_val

            # Ponts (Connexions virtuelles)
            if is_my_piece:
                for (dr, dc), shared in self.bridge_offsets:
                    nr, nc = r + dr, c + dc
                    if (nr, nc) in node_to_idx:
                        dest_val = grid[nr, nc]
                        if dest_val != -player_val: # Vide ou Ami
                            safe = True
                            for (ir, ic) in shared:
                                mr, mc = r+ir, c+ic
                                if not (0 <= mr < rows and 0 <= mc < cols) or grid[mr, mc] != 0:
                                    safe = False; break
                            
                            if safe:
                                j = node_to_idx[(nr, nc)]
                                L[i, j] -= self.C_BRIDGE
                                L[i, i] += self.C_BRIDGE

        b = np.zeros(n_nodes, dtype=np.float64)
        if piece_type == "R":
            source_nodes = [node_to_idx[(0, c)] for c in range(cols) if (0, c) in node_to_idx]
            sink_nodes = [node_to_idx[(rows - 1, c)] for c in range(cols) if (rows - 1, c) in node_to_idx]
        else:
            source_nodes = [node_to_idx[(r, 0)] for r in range(rows) if (r, 0) in node_to_idx]
            sink_nodes = [node_to_idx[(r, cols - 1)] for r in range(rows) if (r, cols - 1) in node_to_idx]

        if not source_nodes or not sink_nodes: return 0.0

        for idx_s in source_nodes:
            L[idx_s, :] = 0.0; L[idx_s, idx_s] = 1.0; b[idx_s] = 1.0 
        for idx_t in sink_nodes:
            L[idx_t, :] = 0.0; L[idx_t, idx_t] = 1.0; b[idx_t] = 0.0 

        try:
            V = np.linalg.solve(L, b)
        except np.linalg.LinAlgError:
            return 0.0

        total_current = 0.0
        for idx_s in source_nodes:
            r, c = valid_nodes[idx_s]
            is_source_piece = (grid[r, c] == player_val)

            for nr, nc in self.adj_cache[(r, c)]:
                if (nr, nc) in node_to_idx:
                    idx_n = node_to_idx[(nr, nc)]
                    if idx_n not in source_nodes:
                        is_neighbor_piece = (grid[nr, nc] == player_val)
                        c_val = self.C_SUPER if (is_source_piece or is_neighbor_piece) else self.C_EMPTY
                        total_current += c_val * (1.0 - V[idx_n])

        return total_current