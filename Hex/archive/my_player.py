import heapq
import time
import random
from player_hex import PlayerHex
from seahorse.game.action import Action
from game_state_hex import GameStateHex

# Constantes pour les flags de la Table de Transposition
EXACT = 0
LOWERBOUND = 1
UPPERBOUND = 2

class MyPlayer(PlayerHex):
    """
    Version 5: "Zobrist Turbo"
    - Stratégie : Dijkstra avec Ponts (Bridges) + Iterative Deepening.
    - Ajout : Zobrist Hashing & Transposition Table pour un élagage massif.
    - Objectif : Atteindre une profondeur 4 ou 5 constante.
    """

    def __init__(self, piece_type: str, name: str = "MyPlayerTurbo"):
        super().__init__(piece_type, name)
        # Définition des ponts (Connexions virtuelles indéfendables)
        self.bridge_offsets = [
            ((-1, 2), [(0, 1), (-1, 1)]),
            ((1, 1),  [(0, 1), (1, 0)]),
            ((2, -1), [(1, 0), (1, -1)]),
            ((1, -2), [(0, -1), (1, -1)]),
            ((-1, -1),[(0, -1), (-1, 0)]),
            ((-2, 1), [(-1, 0), (-1, 1)])
        ]
        
        # Caches
        self.center_cache = {}
        
        # Attributs préfixés par '_' pour ne pas être exportés dans le JSON d'Abyss
        self._zobrist_table = {}
        self._transposition_table = {}

    def _init_caches(self, rows: int, cols: int):
        """Initialise le cache des centres et la table Zobrist une seule fois."""
        cr, cc = rows // 2, cols // 2
        for r in range(rows):
            for c in range(cols):
                # Distance euclidienne au carré
                self.center_cache[(r, c)] = (r - cr)**2 + (c - cc)**2
                # Zobrist random bitstrings (64-bit) pour chaque case et chaque couleur
                self._zobrist_table[(r, c, "R")] = random.getrandbits(64)
                self._zobrist_table[(r, c, "B")] = random.getrandbits(64)

    def _hash_state(self, state: GameStateHex) -> int:
        """Calcule le Zobrist Hash de l'état actuel du plateau."""
        h = 0
        env = state.get_rep().get_env()
        for (r, c), piece in env.items():
            if piece is not None:
                h ^= self._zobrist_table[(r, c, piece.get_type())]
        return h

    def compute_action(self, current_state: GameStateHex, remaining_time: float = 15*60, **kwargs) -> Action:
        """
        Iterative Deepening avec Table de Transposition.
        """
        # Initialisation des caches au premier tour
        if not self._zobrist_table:
            rows, cols = current_state.get_rep().get_dimensions()
            self._init_caches(rows, cols)

        start_time = time.time()
        # Allocation temps : 5% du temps restant ou 10s max (sécurité)
        time_limit = start_time + min(10, remaining_time * 0.05) 
        
        # Fallback de base
        best_action = list(current_state.generate_possible_stateful_actions())[0]
        
        try:
            # On tente d'aller le plus profond possible (1 -> 10)
            for depth in range(1, 10):
                if time.time() > time_limit:
                    break
                
                val, action = self.alpha_beta(
                    current_state, depth, float("-inf"), float("inf"), 
                    True, time_limit, is_root=True
                )
                if action:
                    best_action = action
                    
        except TimeoutError:
            pass # Temps écoulé, on utilise la meilleure action de l'itération précédente

        return best_action

    def alpha_beta(self, state: GameStateHex, depth: int, alpha: float, beta: float, 
                   maximizing_player: bool, time_limit: float, is_root: bool = False) -> tuple[float, Action]:
        
        if time.time() > time_limit:
            raise TimeoutError()

        state_hash = self._hash_state(state)
        
        # --- 1. LECTURE DE LA TABLE DE TRANSPOSITION ---
        tt_entry = self._transposition_table.get(state_hash)
        tt_action = None
        if tt_entry is not None:
            tt_depth, tt_flag, tt_val, tt_action = tt_entry
            
            # Si on a déjà exploré cette position à une profondeur suffisante ou supérieure
            if tt_depth >= depth:
                if tt_flag == EXACT:
                    return tt_val, tt_action
                elif tt_flag == LOWERBOUND:
                    alpha = max(alpha, tt_val)
                elif tt_flag == UPPERBOUND:
                    beta = min(beta, tt_val)
                
                if alpha >= beta:
                    return tt_val, tt_action

        # Condition d'arrêt
        if depth == 0 or state.is_done():
            val = self.heuristic(state)
            return val, None

        actions = list(state.generate_possible_stateful_actions())
        if not actions:
             return self.heuristic(state), None

        # --- 2. MOVE ORDERING (Tri des coups) ---
        # On priorise le meilleur coup trouvé dans la TT, puis on trie selon le centre
        curr_env = state.get_rep().get_env()
        
        def score_action(action):
            # Si c'est le coup de la Table de Transposition, on l'évalue EN PREMIER absolu
            if tt_action and action.get_next_game_state().get_rep().get_env() == tt_action.get_next_game_state().get_rep().get_env():
                return 10000 
            
            next_env = action.get_next_game_state().get_rep().get_env()
            for k in next_env:
                if k not in curr_env:
                    dist = self.center_cache.get(k, 100)
                    return -dist # Trier par distance au centre (plus proche = meilleur)
            return -1000
        
        actions.sort(key=score_action, reverse=True)

        best_action = actions[0]
        alpha_orig = alpha # Sauvegarde pour flagger la TT
        
        # --- 3. RECHERCHE MINIMAX ---
        if maximizing_player:
            max_eval = float("-inf")
            for action in actions:
                next_state = action.get_next_game_state()
                eval_val, _ = self.alpha_beta(next_state, depth - 1, alpha, beta, False, time_limit, False)
                
                if eval_val > max_eval:
                    max_eval = eval_val
                    best_action = action
                alpha = max(alpha, eval_val)
                if beta <= alpha: break
                
            # --- 4. ÉCRITURE DANS LA TABLE DE TRANSPOSITION ---
            flag = EXACT
            if max_eval <= alpha_orig:
                flag = UPPERBOUND
            elif max_eval >= beta:
                flag = LOWERBOUND
            self._transposition_table[state_hash] = (depth, flag, max_eval, best_action)
            
            return max_eval, best_action
            
        else:
            min_eval = float("inf")
            for action in actions:
                next_state = action.get_next_game_state()
                eval_val, _ = self.alpha_beta(next_state, depth - 1, alpha, beta, True, time_limit, False)
                
                if eval_val < min_eval:
                    min_eval = eval_val
                    best_action = action
                beta = min(beta, eval_val)
                if beta <= alpha: break
                
            flag = EXACT
            if min_eval <= alpha_orig:
                flag = UPPERBOUND
            elif min_eval >= beta:
                flag = LOWERBOUND
            self._transposition_table[state_hash] = (depth, flag, min_eval, best_action)
            
            return min_eval, best_action

    def heuristic(self, state: GameStateHex) -> float:
        """ Différence de Dijkstra. """
        if state.is_done():
            scores = state.get_scores()
            my_id = self.get_id()
            my_score = scores.get(my_id, 0)
            opp_score = sum(scores.values()) - my_score
            return (my_score - opp_score) * 100000

        my_piece = self.get_piece_type()
        opp_piece = "B" if my_piece == "R" else "R"

        d_moi = self._get_shortest_path_distance(state, my_piece)
        d_adv = self._get_shortest_path_distance(state, opp_piece)

        if d_moi >= 999: return -50000
        if d_adv >= 999: return 50000

        return (d_adv - d_moi) * 100

    def _get_shortest_path_distance(self, state, piece_type):
        """ Dijkstra simplifié avec Ponts et Templates de bord. """
        board = state.get_rep()
        env = board.get_env()
        rows, cols = board.get_dimensions()
        pq, dist_map = [], {}

        if piece_type == "R":
            start_row, target_row = 0, rows - 1
            for j in range(cols):
                p = env.get((start_row, j))
                d = 1 if p is None else (0 if p.get_type() == "R" else None)
                if d is not None: dist_map[(start_row, j)] = d; heapq.heappush(pq, (d, start_row, j))
        else:
            start_col, target_col = 0, cols - 1
            for i in range(rows):
                p = env.get((i, start_col))
                d = 1 if p is None else (0 if p.get_type() == "B" else None)
                if d is not None: dist_map[(i, start_col)] = d; heapq.heappush(pq, (d, i, start_col))

        while pq:
            d, r, c = heapq.heappop(pq)
            if d > dist_map.get((r, c), float("inf")): continue

            if piece_type == "R":
                if r == target_row: return d
                if r == rows - 2:
                    c1, c2 = env.get((r+1, c)), env.get((r+1, c-1))
                    valid_c1 = (c1 is None or c1.get_type() == "R")
                    valid_c2 = (c2 is None or c2.get_type() == "R")
                    if (0 <= c < cols and valid_c1) and (0 <= c-1 < cols and valid_c2): return d
            else: 
                if c == target_col: return d
                if c == cols - 2:
                    c1, c2 = env.get((r, c+1)), env.get((r-1, c+1))
                    valid_c1 = (c1 is None or c1.get_type() == "B")
                    valid_c2 = (c2 is None or c2.get_type() == "B")
                    if (0 <= r < rows and valid_c1) and (0 <= r-1 < rows and valid_c2): return d

            for _, (_, (nr, nc)) in board.get_neighbours(r, c).items():
                if 0 <= nr < rows and 0 <= nc < cols:
                    np = env.get((nr, nc))
                    if np is None: weight = 1
                    elif np.get_type() == piece_type: weight = 0
                    else: continue
                    
                    if d + weight < dist_map.get((nr, nc), float("inf")):
                        dist_map[(nr, nc)] = d + weight
                        heapq.heappush(pq, (d + weight, nr, nc))
            
            for (dr, dc), shared in self.bridge_offsets:
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols:
                    dest_p = env.get((nr, nc))
                    if dest_p is not None and dest_p.get_type() != piece_type: continue

                    safe = True
                    for (ir, ic) in shared:
                        mr, mc = r+ir, c+ic
                        if not (0 <= mr < rows and 0 <= mc < cols) or env.get((mr, mc)) is not None:
                            safe = False; break
                    
                    if safe:
                        weight = 0 if (dest_p is not None and dest_p.get_type() == piece_type) else 1
                        if d + weight < dist_map.get((nr, nc), float("inf")):
                            dist_map[(nr, nc)] = d + weight
                            heapq.heappush(pq, (d + weight, nr, nc))
                            
        return 999