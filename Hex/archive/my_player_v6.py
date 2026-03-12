import heapq
import time
from player_hex import PlayerHex
from seahorse.game.action import Action
from game_state_hex import GameStateHex

class MyPlayer(PlayerHex):
    """
    Agent de base "Back to Basics".
    - Minimax + Alpha-Bêta pur.
    - Heuristique : Différence des plus courts chemins (Dijkstra basique).
    - Aucun artifice de Move Ordering ou de Table de Transposition.
    """

    def __init__(self, piece_type: str, name: str = "BaseAgent"):
        super().__init__(piece_type, name)

    def compute_action(self, current_state: GameStateHex, remaining_time: float = 15*60, **kwargs) -> Action:
        # On se donne un temps fixe simple (ex: 5 secondes) pour ne pas épuiser les 15 minutes[cite: 50, 51].
        start_time = time.time()
        time_limit = start_time + 5.0 
        
        actions = list(current_state.generate_possible_stateful_actions())
        if not actions:
            raise ValueError("Aucune action possible")

        best_action = actions[0]
        
        # Approfondissement itératif très basique (profondeur 1, puis 2, puis 3)
        try:
            for depth in range(1, 4): # On bloque à 3 pour s'assurer que l'agent répond vite
                if time.time() > time_limit:
                    break
                
                val, action = self.alpha_beta(
                    current_state, depth, float("-inf"), float("inf"), 
                    True, time_limit
                )
                if action:
                    best_action = action
                    
        except TimeoutError:
            pass # Si on manque de temps, on garde le meilleur coup de l'itération précédente

        return best_action

    def alpha_beta(self, state: GameStateHex, depth: int, alpha: float, beta: float, 
                   maximizing_player: bool, time_limit: float) -> tuple[float, Action]:
        
        # Arrêt d'urgence si on dépasse le temps
        if time.time() > time_limit:
            raise TimeoutError()

        # Condition d'arrêt : profondeur atteinte ou fin de partie
        if depth == 0 or state.is_done():
            return self.heuristic(state), None

        actions = list(state.generate_possible_stateful_actions())
        best_action = actions[0] if actions else None

        if maximizing_player:
            max_eval = float("-inf")
            for action in actions:
                next_state = action.get_next_game_state()
                eval_val, _ = self.alpha_beta(next_state, depth - 1, alpha, beta, False, time_limit)
                
                if eval_val > max_eval:
                    max_eval = eval_val
                    best_action = action
                alpha = max(alpha, eval_val)
                if beta <= alpha: 
                    break # Élagage Bêta
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
                if beta <= alpha: 
                    break # Élagage Alpha
            return min_eval, best_action

    def heuristic(self, state: GameStateHex) -> float:
        """
        Heuristique stricte : (Distance de l'Adversaire) - (Ma Distance).
        Plus l'adversaire est loin de connecter et plus je suis proche, meilleur est le score.
        """
        if state.is_done():
            scores = state.get_scores()
            my_score = scores.get(self.get_id(), 0)
            # Victoire = score infini, Défaite = score -infini
            return float("inf") if my_score > 0 else float("-inf")

        my_piece = self.get_piece_type()
        opp_piece = "B" if my_piece == "R" else "R"

        my_dist = self.dijkstra(state, my_piece)
        opp_dist = self.dijkstra(state, opp_piece)

        # Si un chemin est complètement bloqué, on pénalise lourdement
        if my_dist >= 999: return -50000
        if opp_dist >= 999: return 50000

        return opp_dist - my_dist

    def dijkstra(self, state: GameStateHex, piece_type: str) -> float:
        """
        Algorithme de Dijkstra brut pour trouver le plus court chemin.
        Coût : 0 si c'est notre pièce, 1 si case vide. Murs = pièces adverses.
        """
        board = state.get_rep()
        env = board.get_env()
        rows, cols = board.get_dimensions()
        
        pq = []
        dist_map = {}

        # 1. Initialisation de la ligne/colonne de départ
        if piece_type == "R":
            # Le joueur Rouge veut relier le Haut (ligne 0) au Bas (ligne rows-1) [cite: 20, 21]
            for c in range(cols):
                p = env.get((0, c))
                cost = 1 if p is None else (0 if p.get_type() == "R" else None)
                if cost is not None:
                    dist_map[(0, c)] = cost
                    heapq.heappush(pq, (cost, 0, c))
        else:
            # Le joueur Bleu veut relier la Gauche (colonne 0) à la Droite (colonne cols-1) [cite: 20, 21]
            for r in range(rows):
                p = env.get((r, 0))
                cost = 1 if p is None else (0 if p.get_type() == "B" else None)
                if cost is not None:
                    dist_map[(r, 0)] = cost
                    heapq.heappush(pq, (cost, r, 0))

        # 2. Propagation
        while pq:
            d, r, c = heapq.heappop(pq)

            # Si on a déjà trouvé un chemin plus court vers cette case, on ignore
            if d > dist_map.get((r, c), float("inf")):
                continue

            # Condition de victoire atteinte
            if piece_type == "R" and r == rows - 1:
                return d
            if piece_type == "B" and c == cols - 1:
                return d

            # Voisins classiques [cite: 97]
            for _, (_, (nr, nc)) in board.get_neighbours(r, c).items():
                if 0 <= nr < rows and 0 <= nc < cols:
                    np = env.get((nr, nc))
                    
                    if np is None:
                        weight = 1
                    elif np.get_type() == piece_type:
                        weight = 0
                    else:
                        continue # Pièce adverse, on ne peut pas passer
                        
                    new_dist = d + weight
                    if new_dist < dist_map.get((nr, nc), float("inf")):
                        dist_map[(nr, nc)] = new_dist
                        heapq.heappush(pq, (new_dist, nr, nc))

        return 999 # Aucun chemin trouvé (bloqué)