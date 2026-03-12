import time
import numpy as np
from player_hex import PlayerHex
from seahorse.game.action import Action
from game_state_hex import GameStateHex

class MyPlayer(PlayerHex):
    """
    Agent "Ohm's Law" (La Sorcellerie Électrique).
    - Remplace Dijkstra par une évaluation de flux de courant (Matrice Laplacienne).
    - Utilise NumPy pour inverser des matrices de résistance équivalente.
    - Évalue la redondance des chemins : 5 chemins longs valent mieux qu'un seul chemin court.
    """

    def __init__(self, piece_type: str, name: str = "TeslaAgent"):
        super().__init__(piece_type, name)
        # On va pré-calculer les voisins pour aller plus vite, car appeler board.get_neighbours() 
        # prend trop de temps au sein des boucles critiques.
        self.adj_cache = {}
        
        # Constantes de "Conductance" (Facilité du courant à passer. Conductance = 1 / Résistance)
        self.C_EMPTY_TO_EMPTY = 1.0       # Résistance normale entre cases vides
        self.C_SUPERCONDUCTOR = 1000.0    # Conductance massive si on connecte à l'une de NOS pièces

    def _init_adj_cache(self, rows: int, cols: int):
        """Pré-calcule le graphe de la grille pour ne pas le recalculer à chaque fois."""
        for r in range(rows):
            for c in range(cols):
                neighbors = []
                # Les 6 directions standard d'un plateau Hex (selon l'implémentation standard)
                for dr, dc in [(-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0)]:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < rows and 0 <= nc < cols:
                        neighbors.append((nr, nc))
                self.adj_cache[(r, c)] = neighbors

    def compute_action(self, current_state: GameStateHex, remaining_time: float = 15*60, **kwargs) -> Action:
        """
        Gère le budget temps alloué par le projet (15 minutes au total)[cite: 50].
        L'évaluation par Matrice Laplacienne est LOURDE. On va se limiter à 5 secondes.
        """
        start_time = time.time()
        time_limit = start_time + 5.0 # Temps max par coup
        
        rows, cols = current_state.get_rep().get_dimensions()
        if not self.adj_cache:
            self._init_adj_cache(rows, cols)

        actions = list(current_state.generate_possible_stateful_actions())
        if not actions:
            raise ValueError("Aucune action possible")

        # Fallback basique
        best_action = actions[0]

        try:
            # Comme l'inversion de matrice prend beaucoup de CPU (interdiction d'utiliser le GPU)[cite: 52], 
            # on risque de ne pas dépasser la profondeur 2 ou 3.
            for depth in range(1, 4):
                if time.time() > time_limit:
                    break
                
                val, action = self.alpha_beta(
                    current_state, depth, float("-inf"), float("inf"), 
                    True, time_limit
                )
                if action:
                    best_action = action
                    
        except TimeoutError:
            pass # Si le temps imparti est dépassé, on garde le meilleur coup de l'itération d'avant

        return best_action

    def alpha_beta(self, state: GameStateHex, depth: int, alpha: float, beta: float, 
                   maximizing_player: bool, time_limit: float) -> tuple[float, Action]:
        """Minimax standard avec élagage Alpha-Bêta."""
        if time.time() > time_limit:
            raise TimeoutError()

        if depth == 0 or state.is_done():
            return self.heuristic(state), None

        actions = list(state.generate_possible_stateful_actions())
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
        La Sorcellerie de Shannon : La fonction d'évaluation.
        On évalue qui a le meilleur circuit électrique.
        Plus le "courant" passe facilement (Conductance totale élevée), plus on gagne.
        """
        if state.is_done():
            return float("inf") if state.get_scores().get(self.get_id(), 0) > 0 else float("-inf")

        my_piece = self.get_piece_type()
        opp_piece = "B" if my_piece == "R" else "R"

        # On calcule le flux de courant pour nous
        my_conductance = self._calculate_network_conductance(state, my_piece)
        
        # On calcule le flux de courant pour l'adversaire
        opp_conductance = self._calculate_network_conductance(state, opp_piece)

        # Si l'adversaire est totalement bloqué (son courant est à 0), c'est une victoire mathématique
        if opp_conductance <= 1e-6: return 50000
        # Si NOUS sommes bloqués, c'est une défaite mathématique
        if my_conductance <= 1e-6: return -50000

        # L'heuristique est simplement la différence de "facilité" à faire passer le courant.
        return my_conductance - opp_conductance

    def _calculate_network_conductance(self, state: GameStateHex, piece_type: str) -> float:
        """
        Construit et résout le circuit électrique pour un joueur donné.
        """
        board = state.get_rep()
        env = board.get_env()
        rows, cols = board.get_dimensions()

        # ÉTAPE 1 : Filtrer les nœuds (cases)
        # Les pièces adverses sont des "trous" dans le circuit. On ne les ajoute même pas.
        valid_nodes = []
        node_to_idx = {}
        idx = 0

        for r in range(rows):
            for c in range(cols):
                p = env.get((r, c))
                # On garde la case si elle est vide (None) ou si elle nous appartient
                if p is None or p.get_type() == piece_type:
                    valid_nodes.append((r, c))
                    node_to_idx[(r, c)] = idx
                    idx += 1

        n_nodes = len(valid_nodes)
        if n_nodes == 0:
            return 0.0

        # ÉTAPE 2 : Construction de la Matrice Laplacienne L = D - A
        # L est de taille (n_nodes, n_nodes)
        # On utilise des float64 pour la précision numérique de numpy.
        L = np.zeros((n_nodes, n_nodes), dtype=np.float64)

        for i, (r, c) in enumerate(valid_nodes):
            p = env.get((r, c))
            is_my_piece = (p is not None and p.get_type() == piece_type)

            for nr, nc in self.adj_cache[(r, c)]:
                if (nr, nc) in node_to_idx:
                    j = node_to_idx[(nr, nc)]
                    npiece = env.get((nr, nc))
                    is_neighbor_my_piece = (npiece is not None and npiece.get_type() == piece_type)

                    # Si au moins une des deux cases est notre pièce, le lien est un supra-conducteur
                    if is_my_piece or is_neighbor_my_piece:
                        c_val = self.C_SUPERCONDUCTOR
                    else:
                        c_val = self.C_EMPTY_TO_EMPTY

                    # Remplissage standard de la matrice Laplacienne
                    L[i, j] -= c_val
                    L[i, i] += c_val

        # ÉTAPE 3 : Création des "Générateurs" (Les bords de la grille)
        # Pour faire circuler le courant, on relie le bord A au Pôle Positif (+1 Volt)
        # et le bord B au Pôle Négatif / Terre (0 Volt).
        b = np.zeros(n_nodes, dtype=np.float64)
        
        # On va identifier les nœuds qui touchent les bords visés
        source_nodes = []
        sink_nodes = []

        if piece_type == "R":
            # Le joueur Rouge va du Haut (row 0) vers le Bas (row=rows-1)
            source_nodes = [node_to_idx[(0, c)] for c in range(cols) if (0, c) in node_to_idx]
            sink_nodes = [node_to_idx[(rows - 1, c)] for c in range(cols) if (rows - 1, c) in node_to_idx]
        else:
            # Le joueur Bleu va de la Gauche (col 0) vers la Droite (col=cols-1)
            source_nodes = [node_to_idx[(r, 0)] for r in range(rows) if (r, 0) in node_to_idx]
            sink_nodes = [node_to_idx[(r, cols - 1)] for r in range(rows) if (r, cols - 1) in node_to_idx]

        # Si un des bords est totalement bloqué par l'adversaire, aucun courant ne peut passer.
        if not source_nodes or not sink_nodes:
            return 0.0

        # ÉTAPE 4 : Appliquer les Conditions aux Limites (Dirichlet)
        # En algèbre linéaire, pour forcer le voltage d'un nœud à une valeur fixe dans le système L * V = b,
        # on "écrase" sa ligne dans la matrice : L[i, :] = 0, L[i, i] = 1, et b[i] = Voltage.
        for idx_s in source_nodes:
            L[idx_s, :] = 0.0
            L[idx_s, idx_s] = 1.0
            b[idx_s] = 1.0  # Voltage Source = 1 Volt

        for idx_t in sink_nodes:
            L[idx_t, :] = 0.0
            L[idx_t, idx_t] = 1.0
            b[idx_t] = 0.0  # Voltage Sink = 0 Volt

        # ÉTAPE 5 : RÉSOUDRE LE SYSTÈME L * V = b
        # numpy calcule magiquement le voltage de toutes les autres cases pour équilibrer le réseau.
        try:
            V = np.linalg.solve(L, b)
        except np.linalg.LinAlgError:
            # Cas rare (ex: matrice singulière si le graphe est bizarrement déconnecté en plein milieu)
            return 0.0

        # ÉTAPE 6 : Calculer la Conductance Totale (Le "Courant" total I)
        # La loi d'Ohm : Courant Total = Somme des courants sortant de la source.
        # I_total = Somme( Conductance * (Voltage_Source - Voltage_Voisin) )
        total_current = 0.0
        
        for idx_s in source_nodes:
            r, c = valid_nodes[idx_s]
            p = env.get((r, c))
            is_source_piece = (p is not None and p.get_type() == piece_type)

            for nr, nc in self.adj_cache[(r, c)]:
                if (nr, nc) in node_to_idx:
                    idx_n = node_to_idx[(nr, nc)]
                    
                    # On ne compte le courant qui SORT de la source vers l'intérieur du plateau
                    if idx_n not in source_nodes:
                        npiece = env.get((nr, nc))
                        is_neighbor_piece = (npiece is not None and npiece.get_type() == piece_type)
                        
                        c_val = self.C_SUPERCONDUCTOR if (is_source_piece or is_neighbor_piece) else self.C_EMPTY_TO_EMPTY
                        
                        # Courant sur ce "fil" = Conductance * Différence de potentiel
                        # Puisque V[idx_s] vaut 1.0 (imposé plus haut)
                        current_branch = c_val * (1.0 - V[idx_n])
                        total_current += current_branch

        return total_current