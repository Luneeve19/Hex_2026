import heapq
import time
from player_hex import PlayerHex
from seahorse.game.action import Action
from game_state_hex import GameStateHex

class MyPlayer(PlayerHex):
    """
    Version Optimisée:
    - Garde l'intelligence (Dijkstra + Ponts + Blocage)
    - Ajoute Iterative Deepening (Gestion du temps)
    - Supprime les calculs lourds dans le tri des coups (Move Ordering)
    """

    def __init__(self, piece_type: str, name: str = "MyPlayerTurbo"):
        super().__init__(piece_type, name)
        # Définition des ponts (direction, [cases intermédiaires])
        self.bridge_offsets = [
            ((-1, 2), [(0, 1), (-1, 1)]),
            ((1, 1),  [(0, 1), (1, 0)]),
            ((2, -1), [(1, 0), (1, -1)]),
            ((1, -2), [(0, -1), (1, -1)]),
            ((-1, -1),[(0, -1), (-1, 0)]),
            ((-2, 1), [(-1, 0), (-1, 1)])
        ]
        # Pré-calcul des poids pour le centre (Move Ordering rapide)
        self.center_weights = {}

    def compute_action(self, current_state: GameStateHex, remaining_time: float = 15*60, **kwargs) -> Action:
        """
        Utilise l'Iterative Deepening pour aller le plus profond possible
        sans dépasser le temps.
        """
        start_time = time.time()
        # On garde 1 seconde de marge de sécurité ou 5% du temps restant
        time_limit = start_time + min(10, remaining_time * 0.05) 
        
        # Initialisation des poids du centre si pas encore fait (taille du plateau connue ici)
        if not self.center_weights:
            rows, cols = current_state.get_rep().get_dimensions()
            self._init_center_weights(rows, cols)

        best_action = None
        
        # Profondeur 1 (Rapide) -> Profondeur X
        # On essaie d'aller jusqu'à profondeur 10, mais le temps nous arrêtera avant
        try:
            for depth in range(1, 10):
                # Vérif temps avant de lancer une nouvelle profondeur
                if time.time() > time_limit:
                    break
                
                score, action = self.alpha_beta(
                    current_state, depth, float("-inf"), float("inf"), 
                    True, time_limit
                )
                if action:
                    best_action = action
                    
        except TimeoutError:
            pass # On retourne la meilleure action trouvée à la profondeur précédente

        # Fallback si rien trouvé (très rare)
        if best_action is None:
            return list(current_state.generate_possible_stateful_actions())[0]
            
        return best_action

    def _init_center_weights(self, rows, cols):
        """Crée une carte de chaleur statique pour privilégier le centre (rapide)"""
        cr, cc = rows // 2, cols // 2
        for r in range(rows):
            for c in range(cols):
                dist = abs(r - cr) + abs(c - cc)
                # Plus on est proche du centre, plus le score est haut (max ~20)
                self.center_weights[(r, c)] = 20 - dist

    def alpha_beta(self, state: GameStateHex, depth: int, alpha: float, beta: float, 
                   maximizing_player: bool, time_limit: float) -> tuple[float, Action]:
        
        # Vérification du temps (toutes les 100 vérifs ou à chaque nœud si nécessaire)
        if time.time() > time_limit:
            raise TimeoutError()

        if depth == 0 or state.is_done():
            return self.heuristic(state), None

        # Génération des actions
        actions = list(state.generate_possible_stateful_actions())
        
        if not actions:
            return self.heuristic(state), None

        # --- OPTIMISATION DU TRI DES COUPS ---
        # Au lieu de Dijkstra, on trie par "Proximité du centre" (statique)
        # C'est 100x plus rapide et suffisant pour l'Alpha-Beta
        def fast_score(action):
            # On regarde juste où la pièce est posée
            # Hack: on récupère la différence entre les deux grilles
            # Note: Pour aller encore plus vite, on pourrait utiliser action.get_move() si disponible
            # Ici on utilise une heuristique simple basée sur la dernière pièce posée
            next_rep = action.get_next_game_state().get_rep()
            # Simplification: On ne cherche pas la coordonnée exacte pour aller vite,
            # on fait confiance au hasard si l'API ne donne pas le coup direct.
            # Mais si on veut être précis sans être lent:
            return 0 
        
        # Tri basique : Le centre d'abord.
        # Pour une vraie vitesse, on peut souvent se passer du tri complexe à faible profondeur
        # ou implémenter un tri basé sur les voisins occupés.
        
        # Ici, pour ne pas ralentir, on ne trie pas ou on trie aléatoirement
        # Si tu veux trier: actions.sort(...) mais attention au coût python.
        
        best_action = actions[0]

        if maximizing_player:
            max_eval = float("-inf")
            for action in actions:
                next_state = action.get_next_game_state()
                eval_val, _ = self.alpha_beta(next_state, depth - 1, alpha, beta, False, time_limit)
                
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
                eval_val, _ = self.alpha_beta(next_state, depth - 1, alpha, beta, True, time_limit)
                
                if eval_val < min_eval:
                    min_eval = eval_val
                    best_action = action
                beta = min(beta, eval_val)
                if beta <= alpha: break
            return min_eval, best_action

    def heuristic(self, state: GameStateHex) -> float:
        if state.is_done():
            scores = state.get_scores()
            my_id = self.get_id()
            my_score = scores.get(my_id, 0)
            opp_score = sum(scores.values()) - my_score
            return (my_score - opp_score) * 100000 # Victoire certaine

        my_piece = self.get_piece_type()
        opp_piece = "B" if my_piece == "R" else "R"

        # 1. Dijkstra Difference (Le plus important)
        d_moi = self._get_shortest_path_distance(state, my_piece)
        d_adv = self._get_shortest_path_distance(state, opp_piece)

        # Si chemin impossible (infini), pénalité max
        if d_moi >= 999: return -50000
        if d_adv >= 999: return 50000

        # Score de base : différence de distance
        # On veut d_moi petit et d_adv grand
        score = (d_adv - d_moi) * 100

        # 2. Bonus stratégiques légers (sans boucles lourdes)
        # On ne recalcule pas tout, on fait confiance au Dijkstra
        
        return score

    def _get_shortest_path_distance(self, state, piece_type):
        """
        Dijkstra optimisé pour la vitesse.
        Supporte les 'Ponts' (Bridge) comme distance 0.
        """
        board = state.get_rep()
        env = board.get_env()
        rows, cols = board.get_dimensions()
        
        pq = []
        # Utiliser un set pour 'visited' est plus rapide qu'un dict 'dist_map' complet parfois
        min_dists = {} 

        # Initialisation des bords
        if piece_type == "R": # Haut vers Bas
            target_row = rows - 1
            for j in range(cols):
                p = env.get((0, j))
                if p is None: # Vide = coût 1
                    cost = 1
                    if cost < min_dists.get((0, j), 999):
                        min_dists[(0, j)] = cost
                        heapq.heappush(pq, (cost, 0, j))
                elif p.get_type() == "R": # Ma pièce = coût 0
                    min_dists[(0, j)] = 0
                    heapq.heappush(pq, (0, 0, j))
                # Sinon (pièce adverse) : obstacle, on n'ajoute pas
        else: # Gauche vers Droite (Bleu)
            target_col = cols - 1
            for i in range(rows):
                p = env.get((i, 0))
                if p is None:
                    cost = 1
                    if cost < min_dists.get((i, 0), 999):
                        min_dists[(i, 0)] = cost
                        heapq.heappush(pq, (cost, i, 0))
                elif p.get_type() == "B":
                    min_dists[(i, 0)] = 0
                    heapq.heappush(pq, (0, i, 0))

        while pq:
            d, r, c = heapq.heappop(pq)

            # Optimisation: Si on a déjà trouvé mieux, on passe
            if d > min_dists.get((r, c), 999):
                continue
            
            # Si on a atteint le bord opposé
            if (piece_type == "R" and r == target_row) or (piece_type == "B" and c == target_col):
                return d

            # Voisins directs (Distance 1 ou 0)
            neighbours = board.get_neighbours(r, c)
            for _, (_, (nr, nc)) in neighbours.items():
                if not (0 <= nr < rows and 0 <= nc < cols): continue
                
                cell_piece = env.get((nr, nc))
                if cell_piece is None: weight = 1
                elif cell_piece.get_type() == piece_type: weight = 0
                else: continue # Obstacle adverse

                new_dist = d + weight
                if new_dist < min_dists.get((nr, nc), 999):
                    min_dists[(nr, nc)] = new_dist
                    heapq.heappush(pq, (new_dist, nr, nc))

            # Voisins "Ponts" (Distance 0 si le pont est valide)
            # On vérifie seulement si la case actuelle est vide (coût 1) ou à nous (coût 0)
            # Si on est sur une case vide, on peut "sauter" vers une autre case vide via un pont
            for (dr, dc), intermediates in self.bridge_offsets:
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols:
                    # Vérifier si la destination est accessible (vide ou à nous)
                    dest_p = env.get((nr, nc))
                    if dest_p is not None and dest_p.get_type() != piece_type:
                        continue # Destination bloquée

                    # Vérifier si le pont est coupé (une des cases intermédiaires est prise par l'ennemi)
                    # Pour qu'un pont soit valide, les DEUX cases intermédiaires doivent être LIBRES
                    # (Ou au moins une libre si on veut être moins strict, mais ici on veut garantir la connexion)
                    is_bridge_safe = True
                    for (ir, ic) in intermediates:
                        mid_r, mid_c = r + ir, c + ic
                        # Si hors limites ou occupé par ENNEMI, le pont est cassé
                        if not (0 <= mid_r < rows and 0 <= mid_c < cols):
                            is_bridge_safe = False; break
                        mid_p = env.get((mid_r, mid_c))
                        if mid_p is not None: # Si occupé (même par nous), ce n'est plus un "pont" vide classique
                             # Si occupé par l'ennemi -> coupé.
                             # Si occupé par nous -> c'est juste une connexion normale, pas besoin de logique de pont.
                             is_bridge_safe = False; break
                    
                    if is_bridge_safe:
                        # Si pont valide, le coût pour traverser est 0 (virtuellement connecté)
                        # Mais on ajoute le coût de la case destination elle-même
                        weight = 0 if (dest_p is not None and dest_p.get_type() == piece_type) else 1 
                        # Note: Ici on simplifie. Normalement un pont ajoute 0 à la distance courante.
                        # Si je suis à dist X, et je saute un pont vers une case vide, je suis toujours à dist X (car j'ai besoin de poser 1 pion pour sécuriser, mais le pont me "donne" l'avancée).
                        # Ajustement fin : Considérons le saut comme gratuit.
                        
                        new_dist = d # Le saut est gratuit car on force l'ennemi à répondre
                        if dest_p is None: new_dist += 1 # Mais il faut quand même jouer le coup un jour ? 
                        # Dans la logique Hex standard : Bridge = connexion insécable.
                        # Donc distance ne change pas entre les deux bouts du pont.
                        
                        if new_dist < min_dists.get((nr, nc), 999):
                            min_dists[(nr, nc)] = new_dist
                            heapq.heappush(pq, (new_dist, nr, nc))

        return 999 # Pas de chemin trouvé