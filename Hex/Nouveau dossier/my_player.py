import heapq
import time
from player_hex import PlayerHex
from seahorse.game.action import Action
from game_state_hex import GameStateHex

class MyPlayer(PlayerHex):
    """
    Version 5: "The Engine"
    - Stratégie : Dijkstra avec Ponts (Bridges) + Iterative Deepening.
    - Optimisations : Transposition Table (Mémorisation) + Killer Moves (Tri dynamique).
    - Objectif : Atteindre les profondeurs 4, 5 ou 6.
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
        
        # Caches et Optimisations
        self.center_cache = {}
        self.transposition_table = {} # Stocke les évaluations des plateaux déjà vus
        self.killer_moves = {}        # depth -> action_str (Stocke les coups qui provoquent des coupures)

    def compute_action(self, current_state: GameStateHex, remaining_time: float = 15*60, **kwargs) -> Action:
        """Iterative Deepening avec gestion du temps millimétrée."""
        if not self.center_cache:
            rows, cols = current_state.get_rep().get_dimensions()
            self._init_center_cache(rows, cols)

        start_time = time.time()
        
        # Allocation temps : 5% du temps restant, max 12s, min 1s
        time_limit = start_time + max(1.0, min(12.0, remaining_time * 0.05)) 
        
        actions = list(current_state.generate_possible_stateful_actions())
        if not actions:
            return None # Sécurité
            
        best_action = actions[0]
        
        try:
            # Iterative Deepening
            for depth in range(1, 10):
                if time.time() > time_limit:
                    break
                
                # On lance l'Alpha-Beta
                val, action = self.alpha_beta(
                    current_state, depth, float("-inf"), float("inf"), 
                    True, time_limit, is_root=True
                )
                
                if action:
                    best_action = action
                    
        except TimeoutError:
            pass # Le temps est écoulé, on retourne le meilleur coup de la profondeur précédente

        return best_action

    def _init_center_cache(self, rows, cols):
        """Pré-calcule la distance au centre pour le tri."""
        cr, cc = rows // 2, cols // 2
        for r in range(rows):
            for c in range(cols):
                self.center_cache[(r, c)] = (r - cr)**2 + (c - cc)**2

    def _get_board_hash(self, state: GameStateHex) -> tuple:
        """
        Crée une signature unique (hash) de l'état du plateau.
        Extrêmement rapide et permet de reconnaître si on a déjà évalué cette position.
        """
        env = state.get_rep().get_env()
        # On crée un tuple trié des pièces présentes: ((r, c), 'R'), ...
        # (L'utilisation d'un tuple le rend hashable pour le dictionnaire)
        board_state = tuple(sorted((k, v.get_type()) for k, v in env.items()))
        return board_state

    def alpha_beta(self, state: GameStateHex, depth: int, alpha: float, beta: float, 
                   maximizing_player: bool, time_limit: float, is_root: bool = False) -> tuple[float, Action]:
        
        if time.time() > time_limit:
            raise TimeoutError()

        # --- 1. TRANSPOSITION TABLE (Lecture) ---
        board_hash = self._get_board_hash(state)
        if board_hash in self.transposition_table:
            tt_depth, tt_score, tt_flag, tt_action = self.transposition_table[board_hash]
            
            # Si on a déjà cherché ce plateau à une profondeur égale ou supérieure
            if tt_depth >= depth:
                if tt_flag == 'EXACT':
                    return tt_score, tt_action
                elif tt_flag == 'LOWERBOUND':
                    alpha = max(alpha, tt_score)
                elif tt_flag == 'UPPERBOUND':
                    beta = min(beta, tt_score)
                    
                if alpha >= beta:
                    return tt_score, tt_action

        # --- 2. CONDITIONS D'ARRÊT ---
        if depth == 0 or state.is_done():
            score = self.heuristic(state)
            # On sauvegarde dans la TT
            self.transposition_table[board_hash] = (depth, score, 'EXACT', None)
            return score, None

        actions = list(state.generate_possible_stateful_actions())
        if not actions:
             return self.heuristic(state), None

        # --- 3. MOVE ORDERING (Tri des coups) ---
        # Récupération du Killer Move pour cette profondeur
        killer_move_str = self.killer_moves.get(depth, None)
        curr_env = state.get_rep().get_env()

        def score_action(action):
            # Identifier la case jouée par cette action
            next_env = action.get_next_game_state().get_rep().get_env()
            move_coord = None
            for k in next_env:
                if k not in curr_env:
                    move_coord = k
                    break
            
            score = 0
            if move_coord:
                # 1. Priorité absolue au Killer Move
                if str(move_coord) == killer_move_str:
                    score += 10000 
                # 2. Priorité secondaire au centre
                score -= self.center_cache.get(move_coord, 100)
            return score
            
        actions.sort(key=score_action, reverse=True)

        # --- 4. EXPLORATION DE L'ARBRE ---
        best_action = actions[0]
        original_alpha = alpha

        if maximizing_player:
            max_eval = float("-inf")
            for action in actions:
                next_state = action.get_next_game_state()
                eval_val, _ = self.alpha_beta(next_state, depth - 1, alpha, beta, False, time_limit, False)
                
                if eval_val > max_eval:
                    max_eval = eval_val
                    best_action = action
                
                alpha = max(alpha, eval_val)
                if beta <= alpha:
                    # KILLER MOVE REPERÉ ! On le stocke pour les branches parallèles
                    next_env = action.get_next_game_state().get_rep().get_env()
                    for k in next_env:
                        if k not in curr_env:
                            self.killer_moves[depth] = str(k)
                            break
                    break # Cut-off
                    
        else:
            max_eval = float("inf") # En fait c'est min_eval ici, gardons max_eval par simplicité de nom de variable retournée
            for action in actions:
                next_state = action.get_next_game_state()
                eval_val, _ = self.alpha_beta(next_state, depth - 1, alpha, beta, True, time_limit, False)
                
                if eval_val < max_eval:
                    max_eval = eval_val
                    best_action = action
                    
                beta = min(beta, eval_val)
                if beta <= alpha:
                    # KILLER MOVE REPERÉ !
                    next_env = action.get_next_game_state().get_rep().get_env()
                    for k in next_env:
                        if k not in curr_env:
                            self.killer_moves[depth] = str(k)
                            break
                    break # Cut-off

        # --- 5. TRANSPOSITION TABLE (Écriture) ---
        tt_flag = 'EXACT'
        if max_eval <= original_alpha:
            tt_flag = 'UPPERBOUND'
        elif max_eval >= beta:
            tt_flag = 'LOWERBOUND'
            
        self.transposition_table[board_hash] = (depth, max_eval, tt_flag, best_action)

        return max_eval, best_action

    def heuristic(self, state: GameStateHex) -> float:
        """
        L'intelligence pure : Différence de Dijkstra.
        """
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
        """
        Dijkstra A* simplifié + Ponts + TEMPLATES DE BORD.
        """
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
                    if (0 <= c < cols and valid_c1) and (0 <= c-1 < cols and valid_c2):
                        return d
            else:
                if c == target_col: return d
                if c == cols - 2:
                    c1, c2 = env.get((r, c+1)), env.get((r-1, c+1))
                    valid_c1 = (c1 is None or c1.get_type() == "B")
                    valid_c2 = (c2 is None or c2.get_type() == "B")
                    if (0 <= r < rows and valid_c1) and (0 <= r-1 < rows and valid_c2):
                        return d

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