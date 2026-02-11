import heapq
import time
from player_hex import PlayerHex
from seahorse.game.action import Action
from game_state_hex import GameStateHex

class MyPlayer(PlayerHex):
    """
    Version 4: "Speed & Depth"
    - Stratégie : Dijkstra avec Ponts (Bridges) + Iterative Deepening.
    - Nettoyage : Suppression des heuristiques lentes (Panic, Blocking).
    - Objectif : Atteindre une profondeur 3 ou 4 constante.
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
        # Cache pour le tri des coups (Move Ordering) uniquement
        self.center_cache = {}

    def compute_action(self, current_state: GameStateHex, remaining_time: float = 15*60, **kwargs) -> Action:
        """
        Iterative Deepening : Explore profondeur 1, puis 2, puis 3...
        S'arrête dès que le temps alloué au coup est écoulé.
        """
        # Initialisation du cache au premier tour
        if not self.center_cache:
            rows, cols = current_state.get_rep().get_dimensions()
            self._init_center_cache(rows, cols)

        start_time = time.time()
        # Allocation temps : 5% du temps restant ou 10s max (sécurité)
        time_limit = start_time + min(10, remaining_time * 0.05) 
        
        # Fallback : coup par défaut si pas de temps
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
            pass # On retourne le meilleur résultat de la profondeur complétée précédente

        return best_action

    def _init_center_cache(self, rows, cols):
        """Pré-calcule la distance au centre pour le tri rapide des coups."""
        cr, cc = rows // 2, cols // 2
        for r in range(rows):
            for c in range(cols):
                # Distance euclidienne carrée (plus rapide que racine)
                self.center_cache[(r, c)] = (r - cr)**2 + (c - cc)**2

    def alpha_beta(self, state: GameStateHex, depth: int, alpha: float, beta: float, 
                   maximizing_player: bool, time_limit: float, is_root: bool = False) -> tuple[float, Action]:
        
        # Vérification stricte du temps
        if time.time() > time_limit:
            raise TimeoutError()

        if depth == 0 or state.is_done():
            return self.heuristic(state), None

        actions = list(state.generate_possible_stateful_actions())
        if not actions:
             return self.heuristic(state), None

        # --- MOVE ORDERING (Tri des coups) ---
        # On trie les coups uniquement à la racine pour booster l'élagage Alpha-Beta.
        # On privilégie les coups centraux, statistiquement meilleurs.
        if is_root:
            curr_env = state.get_rep().get_env()
            def score_action(action):
                # Estimation rapide de la position jouée (diff des envs)
                # Note: Dans une version C++, on passerait le move en paramètre.
                next_env = action.get_next_game_state().get_rep().get_env()
                for k in next_env:
                    if k not in curr_env:
                        # Plus la distance au centre est petite, meilleur est le score
                        dist = self.center_cache.get(k, 100)
                        return -dist # On veut trier par distance croissante (score décroissant)
                return -1000
            
            actions.sort(key=score_action, reverse=True)

        best_action = actions[0]

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
            return min_eval, best_action

    def heuristic(self, state: GameStateHex) -> float:
        """
        L'intelligence pure : Différence de Dijkstra.
        Tout le reste (blocage, panique) est émergent de la profondeur de recherche.
        """
        if state.is_done():
            scores = state.get_scores()
            my_id = self.get_id()
            my_score = scores.get(my_id, 0)
            opp_score = sum(scores.values()) - my_score
            return (my_score - opp_score) * 100000

        my_piece = self.get_piece_type()
        opp_piece = "B" if my_piece == "R" else "R"

        # Dijkstra Optimisé avec Ponts
        d_moi = self._get_shortest_path_distance(state, my_piece)
        d_adv = self._get_shortest_path_distance(state, opp_piece)

        # Si chemin impossible (infini), victoire/défaite virtuelle
        if d_moi >= 999: return -50000
        if d_adv >= 999: return 50000

        # Formule simple et robuste : Maximiser (Adv - Moi)
        return (d_adv - d_moi) * 100

    def _get_shortest_path_distance(self, state, piece_type):
        """
        Dijkstra A* simplifié + Ponts + TEMPLATES DE BORD.
        """
        board = state.get_rep()
        env = board.get_env()
        rows, cols = board.get_dimensions()
        pq, dist_map = [], {}

        # --- 1. SETUP DES CIBLES & DÉPARTS ---
        if piece_type == "R":
            # Rouge veut aller de Haut (0) -> Bas (rows-1)
            start_row, target_row = 0, rows - 1
            # On scanne la ligne de départ
            for j in range(cols):
                p = env.get((start_row, j))
                d = 1 if p is None else (0 if p.get_type() == "R" else None)
                if d is not None: dist_map[(start_row, j)] = d; heapq.heappush(pq, (d, start_row, j))
        else:
            # Bleu veut aller de Gauche (0) -> Droite (cols-1)
            start_col, target_col = 0, cols - 1
            # On scanne la colonne de départ
            for i in range(rows):
                p = env.get((i, start_col))
                d = 1 if p is None else (0 if p.get_type() == "B" else None)
                if d is not None: dist_map[(i, start_col)] = d; heapq.heappush(pq, (d, i, start_col))

        # --- 2. PROPAGATION ---
        while pq:
            d, r, c = heapq.heappop(pq)
            
            if d > dist_map.get((r, c), float("inf")): continue

            # --- DETECTION DE VICTOIRE (Bord atteint) ---
            if piece_type == "R":
                if r == target_row: return d
                # TEMPLATE DE BORD (Bas) : Si on est ligne avant-dernière (rows-2)
                # et que les 2 cases devant (vers le bas) sont libres -> on est connecté !
                if r == rows - 2:
                    # Les voisins Hex vers le bas sont (r+1, c) et (r+1, c-1)
                    # Si les deux sont valides et vides (ou à nous), c'est gagné virtuellement
                    c1 = env.get((r+1, c))     # Bas-Droite
                    c2 = env.get((r+1, c-1))   # Bas-Gauche
                    # Vérif si case dispo (None) ou Ami. Si Ennemi, le template est cassé.
                    valid_c1 = (c1 is None or c1.get_type() == "R")
                    valid_c2 = (c2 is None or c2.get_type() == "R")
                    
                    # Attention aux bords gauche/droite du plateau
                    if (0 <= c < cols and valid_c1) and (0 <= c-1 < cols and valid_c2):
                        # C'est un template valide ! Distance = d (pas de coût ajout)
                        return d

            else: # Bleu
                if c == target_col: return d
                # TEMPLATE DE BORD (Droite) : Si on est colonne avant-dernière
                if c == cols - 2:
                    # Voisins vers la droite : (r, c+1) et (r-1, c+1)
                    c1 = env.get((r, c+1))
                    c2 = env.get((r-1, c+1))
                    valid_c1 = (c1 is None or c1.get_type() == "B")
                    valid_c2 = (c2 is None or c2.get_type() == "B")

                    if (0 <= r < rows and valid_c1) and (0 <= r-1 < rows and valid_c2):
                        return d

            # --- VOISINS CLASSIQUES ---
            for _, (_, (nr, nc)) in board.get_neighbours(r, c).items():
                if 0 <= nr < rows and 0 <= nc < cols:
                    np = env.get((nr, nc))
                    if np is None: weight = 1
                    elif np.get_type() == piece_type: weight = 0
                    else: continue
                    
                    if d + weight < dist_map.get((nr, nc), float("inf")):
                        dist_map[(nr, nc)] = d + weight
                        heapq.heappush(pq, (d + weight, nr, nc))
            
            # --- PONTS (Bridges) ---
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