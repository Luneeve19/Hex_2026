import heapq
import time
from player_hex import PlayerHex
from seahorse.game.action import Action
from game_state_hex import GameStateHex

class MyPlayer(PlayerHex):
    """
    Agent "Master Edge & Dualité".
    - Minimax + Alpha-Bêta.
    - Dijkstra avec Ponts et Mémorisation de Chemin.
    - Gabarits de Bord (Edge Templates II et III).
    - Tri par Intersection (Dualité) à la racine pour booster l'élagage.
    """

    def __init__(self, piece_type: str, name: str = "DualAgent"):
        super().__init__(piece_type, name)
        
        self.bridge_offsets = [
            ((-1, 2),  [(0, 1), (-1, 1)]),
            ((1, 1),   [(0, 1), (1, 0)]),
            ((2, -1),  [(1, 0), (1, -1)]),
            ((1, -2),  [(0, -1), (1, -1)]),
            ((-1, -1), [(0, -1), (-1, 0)]),
            ((-2, 1),  [(-1, 0), (-1, 1)])
        ]
        self.center_cache = {}

    def _init_center_cache(self, rows: int, cols: int):
        cr, cc = rows // 2, cols // 2
        for r in range(rows):
            for c in range(cols):
                self.center_cache[(r, c)] = (r - cr)**2 + (c - cc)**2

    def compute_action(self, current_state: GameStateHex, remaining_time: float = 15*60, **kwargs) -> Action:
        start_time = time.time()
        time_limit = start_time + 5.0 
        
        rows, cols = current_state.get_rep().get_dimensions()
        if not self.center_cache:
            self._init_center_cache(rows, cols)
            
        actions = list(current_state.generate_possible_stateful_actions())
        if not actions:
            raise ValueError("Aucune action possible")

        # --- DÉBUT DU MOVE ORDERING PAR INTERSECTION (DUALITÉ) ---
        my_piece = self.get_piece_type()
        opp_piece = "B" if my_piece == "R" else "R"

        # 1. On calcule les chemins critiques des deux joueurs à la racine
        _, my_path = self.dijkstra_with_path(current_state, my_piece)
        _, opp_path = self.dijkstra_with_path(current_state, opp_piece)

        # On transforme les listes en sets pour une recherche ultra-rapide O(1)
        my_path_set = set(my_path)
        opp_path_set = set(opp_path)
        intersection_set = my_path_set.intersection(opp_path_set)

        curr_env = current_state.get_rep().get_env()

        def score_action(action):
            """
            Donne un score à un coup pour le trier avant Minimax.
            - Priorité Absolue : Intersection des deux chemins critiques (Coup duel parfait).
            - Haute Priorité : Apparaît sur un des deux chemins critiques.
            - Priorité Basse : Coup central (Ouverture/Renfort).
            """
            next_env = action.get_next_game_state().get_rep().get_env()
            played_pos = None
            
            # Trouver la case jouée (celle qui est dans next_env mais pas dans curr_env)
            for k in next_env:
                if k not in curr_env:
                    played_pos = k
                    break
            
            if played_pos is None:
                return -1000

            score = 0
            # Coup Duel Parfait : Bloque l'adversaire et prolonge notre chemin
            if played_pos in intersection_set:
                score += 10000
            # Coup Tactique Majeur : Sur un des chemins critiques
            elif played_pos in my_path_set or played_pos in opp_path_set:
                score += 5000
                
            # Bonus de centralité (important pour le début de partie et les égalités de score)
            score -= self.center_cache.get(played_pos, 100)
            return score
            
        actions.sort(key=score_action, reverse=True)
        # --- FIN DU MOVE ORDERING ---

        best_action = actions[0]
        
        try:
            for depth in range(1, 4):
                if time.time() > time_limit:
                    break
                
                val, action = self.alpha_beta(
                    current_state, depth, float("-inf"), float("inf"), 
                    True, time_limit, actions
                )
                if action:
                    best_action = action
                    
        except TimeoutError:
            pass

        return best_action

    def alpha_beta(self, state: GameStateHex, depth: int, alpha: float, beta: float, 
                   maximizing_player: bool, time_limit: float, sorted_actions: list = None) -> tuple[float, Action]:
        
        if time.time() > time_limit:
            raise TimeoutError()

        if depth == 0 or state.is_done():
            return self.heuristic(state), None

        actions = sorted_actions if sorted_actions else list(state.generate_possible_stateful_actions())
        best_action = actions[0] if actions else None

        if maximizing_player:
            max_eval = float("-inf")
            for action in actions:
                eval_val, _ = self.alpha_beta(action.get_next_game_state(), depth - 1, alpha, beta, False, time_limit)
                if eval_val > max_eval:
                    max_eval = eval_val
                    best_action = action
                alpha = max(alpha, eval_val)
                if beta <= alpha: break
            return max_eval, best_action
        else:
            min_eval = float("inf")
            for action in actions:
                eval_val, _ = self.alpha_beta(action.get_next_game_state(), depth - 1, alpha, beta, True, time_limit)
                if eval_val < min_eval:
                    min_eval = eval_val
                    best_action = action
                beta = min(beta, eval_val)
                if beta <= alpha: break
            return min_eval, best_action

    def heuristic(self, state: GameStateHex) -> float:
        """
        L'heuristique reste rapide : on ne demande que la distance (pas le chemin)
        aux feuilles de l'arbre pour gagner du temps.
        """
        if state.is_done():
            return float("inf") if state.get_scores().get(self.get_id(), 0) > 0 else float("-inf")

        my_piece = self.get_piece_type()
        opp_piece = "B" if my_piece == "R" else "R"

        my_dist, _ = self.dijkstra_with_path(state, my_piece)
        opp_dist, _ = self.dijkstra_with_path(state, opp_piece)

        if my_dist >= 999: return -50000
        if opp_dist >= 999: return 50000

        return opp_dist - my_dist

    def _is_safe_for_template(self, env: dict, r: int, c: int, piece_type: str, rows: int, cols: int) -> bool:
        if 0 <= r < rows and 0 <= c < cols:
            p = env.get((r, c))
            return p is None or p.get_type() == piece_type
        return False

    def check_target_edge_template(self, env: dict, r: int, c: int, piece_type: str, rows: int, cols: int) -> bool:
        if piece_type == "R":
            if r == rows - 2:
                cells = [(r+1, c), (r+1, c-1)]
                return all(self._is_safe_for_template(env, cr, cc, "R", rows, cols) for cr, cc in cells)
            elif r == rows - 3:
                cells = [(r+1, c), (r+1, c-1), (r+2, c), (r+2, c-1), (r+2, c-2)]
                return all(self._is_safe_for_template(env, cr, cc, "R", rows, cols) for cr, cc in cells)
        else:
            if c == cols - 2:
                cells = [(r, c+1), (r-1, c+1)]
                return all(self._is_safe_for_template(env, cr, cc, "B", rows, cols) for cr, cc in cells)
            elif c == cols - 3:
                cells = [(r, c+1), (r-1, c+1), (r, c+2), (r-1, c+2), (r-2, c+2)]
                return all(self._is_safe_for_template(env, cr, cc, "B", rows, cols) for cr, cc in cells)
        return False

    def get_valid_bridges(self, env: dict, r: int, c: int, piece_type: str, rows: int, cols: int) -> list:
        valid_bridges = []
        for (dr, dc), shared_cells in self.bridge_offsets:
            dest_r, dest_c = r + dr, c + dc
            if not (0 <= dest_r < rows and 0 <= dest_c < cols): continue
            dest_piece = env.get((dest_r, dest_c))
            if dest_piece is not None and dest_piece.get_type() != piece_type: continue

            is_bridge_safe = True
            for (sr, sc) in shared_cells:
                shared_r, shared_c = r + sr, c + sc
                if not (0 <= shared_r < rows and 0 <= shared_c < cols) or env.get((shared_r, shared_c)) is not None:
                    is_bridge_safe = False
                    break
            
            if is_bridge_safe:
                cost = 0 if (dest_piece is not None and dest_piece.get_type() == piece_type) else 1
                valid_bridges.append(((dest_r, dest_c), cost))
        return valid_bridges

    def _reconstruct_path(self, end_r: int, end_c: int, parents: dict, env: dict) -> list:
        """Remonte le chemin depuis la fin et extrait les cases vides."""
        path = []
        curr = (end_r, end_c)
        while curr is not None:
            r, c = curr
            p = env.get((r, c))
            if p is None:  # On ne s'intéresse qu'aux cases vides qu'il reste à jouer
                path.append((r, c))
            curr = parents.get(curr)
        return path

    def dijkstra_with_path(self, state: GameStateHex, piece_type: str) -> tuple[float, list]:
        """
        Dijkstra modifié. 
        Renvoie : (Distance Finale, Liste des cases vides sur ce chemin).
        """
        board = state.get_rep()
        env = board.get_env()
        rows, cols = board.get_dimensions()
        pq, dist_map = [], {}
        parents = {} # Pour tracer le chemin

        if piece_type == "R":
            for c in range(cols):
                p = env.get((0, c))
                cost = 1 if p is None else (0 if p.get_type() == "R" else None)
                if cost is not None:
                    dist_map[(0, c)] = cost
                    heapq.heappush(pq, (cost, 0, c))
                    parents[(0, c)] = None
        else:
            for r in range(rows):
                p = env.get((r, 0))
                cost = 1 if p is None else (0 if p.get_type() == "B" else None)
                if cost is not None:
                    dist_map[(r, 0)] = cost
                    heapq.heappush(pq, (cost, r, 0))
                    parents[(r, 0)] = None

        while pq:
            d, r, c = heapq.heappop(pq)
            if d > dist_map.get((r, c), float("inf")): continue

            # VICTOIRE PHYSIQUE
            if piece_type == "R" and r == rows - 1:
                return d, self._reconstruct_path(r, c, parents, env)
            if piece_type == "B" and c == cols - 1:
                return d, self._reconstruct_path(r, c, parents, env)
            
            # VICTOIRE VIRTUELLE (GABARIT DE BORD)
            if self.check_target_edge_template(env, r, c, piece_type, rows, cols):
                return d, self._reconstruct_path(r, c, parents, env)

            # Voisins classiques
            for _, (_, (nr, nc)) in board.get_neighbours(r, c).items():
                if 0 <= nr < rows and 0 <= nc < cols:
                    np = env.get((nr, nc))
                    if np is None: weight = 1
                    elif np.get_type() == piece_type: weight = 0
                    else: continue
                        
                    new_dist = d + weight
                    if new_dist < dist_map.get((nr, nc), float("inf")):
                        dist_map[(nr, nc)] = new_dist
                        parents[(nr, nc)] = (r, c) # On mémorise d'où on vient
                        heapq.heappush(pq, (new_dist, nr, nc))

            # Ponts virtuels
            for (nr, nc), weight in self.get_valid_bridges(env, r, c, piece_type, rows, cols):
                new_dist = d + weight
                if new_dist < dist_map.get((nr, nc), float("inf")):
                    dist_map[(nr, nc)] = new_dist
                    parents[(nr, nc)] = (r, c)
                    heapq.heappush(pq, (new_dist, nr, nc))

        return 999, []