from math import inf
import time

from player_hex import PlayerHex
from seahorse.game.action import Action
from game_state_hex import GameStateHex


class MyPlayer(PlayerHex):
    """
    Agent Hex amélioré en restant sur des idées "module 1" :
    - iterative deepening
    - tri des coups avant exploration
    - heuristique rapide mais plus informative
    - réduction du branching (top-k + zones actives)
    - gestion du temps avec arrêt de sécurité
    """

    def __init__(self, piece_type: str, name: str = "MyPlayer"):
        super().__init__(piece_type, name)

        # Attributs internes cachés du JSON
        self._time_margin = 0.08
        self._min_time_per_move = 0.01

    def compute_action(
        self,
        current_state: GameStateHex,
        remaining_time: float = 15 * 60,
        **kwargs
    ) -> Action:
        actions = list(current_state.generate_possible_stateful_actions())
        if not actions:
            raise RuntimeError("Aucune action légale disponible.")

        # Fallback ultra sûr
        fallback_action = actions[0]

        # Budget de temps pour CE coup
        start_time = time.perf_counter()
        move_budget = self._allocate_time_budget(current_state, remaining_time)

        # On filtre/réduit déjà les coups racine
        root_actions = self._select_promising_actions(
            current_state,
            actions,
            remaining_time=remaining_time,
            root=True,
        )

        if not root_actions:
            return fallback_action

        best_action = root_actions[0]
        last_completed_best_action = best_action

        depth = 1
        while True:
            if self._time_exceeded(start_time, move_budget):
                break

            search_result = self._search_root(
                current_state=current_state,
                actions=root_actions,
                depth=depth,
                start_time=start_time,
                move_budget=move_budget,
            )

            if search_result is None:
                break

            best_action = search_result
            last_completed_best_action = best_action
            depth += 1

        return last_completed_best_action

    # =========================
    # Gestion du temps
    # =========================

    def _allocate_time_budget(self, state: GameStateHex, remaining_time: float) -> float:
        empties = sum(1 for _ in state.get_rep().get_empty())
        step = state.get_step()
        dim = state.get_rep().get_dimensions()[0]
        total_cells = dim * dim

        # Budget de base selon avancement
        if step < 8:
            frac = 0.015
        elif empties > total_cells * 0.45:
            frac = 0.020
        elif empties > total_cells * 0.20:
            frac = 0.030
        else:
            frac = 0.045

        budget = max(self._min_time_per_move, remaining_time * frac)

        # Sécurité fin de réserve
        if remaining_time < 20:
            budget = min(budget, 0.20)
        elif remaining_time < 60:
            budget = min(budget, 0.50)
        else:
            budget = min(budget, 2.50)

        return budget

    def _time_exceeded(self, start_time: float, move_budget: float) -> bool:
        return (time.perf_counter() - start_time) >= max(
            self._min_time_per_move,
            move_budget - self._time_margin
        )

    def _time_almost_exceeded(self, start_time: float, move_budget: float) -> bool:
        return (time.perf_counter() - start_time) >= max(
            self._min_time_per_move,
            move_budget - self._time_margin * 0.5
        )

    # =========================
    # Root search + IDS
    # =========================

    def _search_root(
        self,
        current_state: GameStateHex,
        actions,
        depth: int,
        start_time: float,
        move_budget: float,
    ):
        maximizing_root = current_state.get_active_player().get_id() == self.get_id()

        ordered_actions = self._order_actions(
            current_state,
            actions,
            maximizing=maximizing_root,
        )

        if maximizing_root:
            best_value = -inf
            best_action = ordered_actions[0]
            alpha = -inf
            beta = inf

            for action in ordered_actions:
                if self._time_exceeded(start_time, move_budget):
                    return None

                next_state = action.get_next_game_state()
                value = self._minimax(
                    state=next_state,
                    depth=depth - 1,
                    alpha=alpha,
                    beta=beta,
                    maximizing=False,
                    start_time=start_time,
                    move_budget=move_budget,
                )

                if value is None:
                    return None

                if value > best_value:
                    best_value = value
                    best_action = action

                alpha = max(alpha, best_value)

            return best_action

        best_value = inf
        best_action = ordered_actions[0]
        alpha = -inf
        beta = inf

        for action in ordered_actions:
            if self._time_exceeded(start_time, move_budget):
                return None

            next_state = action.get_next_game_state()
            value = self._minimax(
                state=next_state,
                depth=depth - 1,
                alpha=alpha,
                beta=beta,
                maximizing=True,
                start_time=start_time,
                move_budget=move_budget,
            )

            if value is None:
                return None

            if value < best_value:
                best_value = value
                best_action = action

            beta = min(beta, best_value)

        return best_action

    def _minimax(
        self,
        state: GameStateHex,
        depth: int,
        alpha: float,
        beta: float,
        maximizing: bool,
        start_time: float,
        move_budget: float,
    ):
        if self._time_exceeded(start_time, move_budget):
            return None

        if depth == 0 or state.is_done():
            return self._evaluate(state)

        actions = list(state.generate_possible_stateful_actions())
        if not actions:
            return self._evaluate(state)

        actions = self._select_promising_actions(
            state,
            actions,
            remaining_time=None,
            root=False,
        )
        actions = self._order_actions(state, actions, maximizing=maximizing)

        if maximizing:
            value = -inf
            for action in actions:
                if self._time_almost_exceeded(start_time, move_budget):
                    return None

                next_state = action.get_next_game_state()
                child_value = self._minimax(
                    state=next_state,
                    depth=depth - 1,
                    alpha=alpha,
                    beta=beta,
                    maximizing=False,
                    start_time=start_time,
                    move_budget=move_budget,
                )

                if child_value is None:
                    return None

                value = max(value, child_value)
                alpha = max(alpha, value)

                if beta <= alpha:
                    break

            return value

        value = inf
        for action in actions:
            if self._time_almost_exceeded(start_time, move_budget):
                return None

            next_state = action.get_next_game_state()
            child_value = self._minimax(
                state=next_state,
                depth=depth - 1,
                alpha=alpha,
                beta=beta,
                maximizing=True,
                start_time=start_time,
                move_budget=move_budget,
            )

            if child_value is None:
                return None

            value = min(value, child_value)
            beta = min(beta, value)

            if beta <= alpha:
                break

        return value

    # =========================
    # Réduction du branching
    # =========================

    def _select_promising_actions(
        self,
        state: GameStateHex,
        actions,
        remaining_time=None,
        root: bool = False,
    ):
        if len(actions) <= 1:
            return actions

        active_zone = self._active_zone_positions(state)

        scored = []
        for action in actions:
            next_state = action.get_next_game_state()
            move_pos = self._extract_move_position(state, next_state)

            proximity_bonus = 0.0
            if move_pos is not None:
                if move_pos in active_zone:
                    proximity_bonus += 15.0
                elif self._is_near_active_zone(move_pos, active_zone):
                    proximity_bonus += 8.0

            score = self._evaluate(next_state) + proximity_bonus
            scored.append((score, action))

        scored.sort(key=lambda x: x[0], reverse=True)

        total = len(scored)

        # top-k différent racine / profondeur interne
        if root:
            if total > 100:
                k = 14
            elif total > 60:
                k = 12
            elif total > 30:
                k = 10
            else:
                k = total
        else:
            if total > 80:
                k = 8
            elif total > 40:
                k = 7
            elif total > 20:
                k = 6
            else:
                k = total

        return [action for _, action in scored[:k]]

    def _order_actions(self, state: GameStateHex, actions, maximizing: bool):
        scored = []
        for action in actions:
            next_state = action.get_next_game_state()
            score = self._evaluate(next_state)
            scored.append((score, action))

        scored.sort(key=lambda x: x[0], reverse=maximizing)
        return [action for _, action in scored]

    def _active_zone_positions(self, state: GameStateHex):
        env = state.get_rep().get_env()
        occupied = list(env.keys())

        if not occupied:
            dim = state.get_rep().get_dimensions()[0]
            center = dim // 2
            zone = set()
            for i in range(max(0, center - 1), min(dim, center + 2)):
                for j in range(max(0, center - 1), min(dim, center + 2)):
                    zone.add((i, j))
            return zone

        zone = set()
        for i, j in occupied:
            zone.add((i, j))
            for _, (_, pos) in state.get_neighbours(i, j).items():
                zone.add(pos)
        return zone

    def _is_near_active_zone(self, pos, active_zone) -> bool:
        i, j = pos
        for ai, aj in active_zone:
            if abs(i - ai) <= 2 and abs(j - aj) <= 2:
                return True
        return False

    def _extract_move_position(self, current_state: GameStateHex, next_state: GameStateHex):
        current_env = current_state.get_rep().get_env()
        next_env = next_state.get_rep().get_env()

        for pos, piece in next_env.items():
            if pos not in current_env and piece is not None:
                return pos
        return None

    # =========================
    # Heuristique
    # =========================

    def _evaluate(self, state: GameStateHex) -> float:
        """
        Heuristique rapide et plus informative :
        - victoire/défaite terminale
        - taille de plus grande composante
        - span sur l’axe de victoire
        - contact avec bords utiles
        - pénalité si groupes séparés
        - liens locaux
        - faible bonus centre
        """
        my_id = self.get_id()
        players = state.players
        p1_id = players[0].get_id()

        if state.is_done():
            if state.scores.get(my_id, 0) == 1:
                return 1_000_000.0
            return -1_000_000.0

        env = state.get_rep().get_env()
        dim = state.get_rep().get_dimensions()[0]

        my_type = self.get_piece_type()
        opp_type = "B" if my_type == "R" else "R"

        my_positions = []
        opp_positions = []

        for (i, j), piece in env.items():
            if piece is None:
                continue
            t = piece.get_type()
            if t == my_type:
                my_positions.append((i, j))
            elif t == opp_type:
                opp_positions.append((i, j))

        my_vertical_goal = (my_id == p1_id)
        opp_vertical_goal = not my_vertical_goal

        my_features = self._analyze_groups(state, my_positions, my_type, my_vertical_goal)
        opp_features = self._analyze_groups(state, opp_positions, opp_type, opp_vertical_goal)

        my_links = self._count_friendly_links(state, my_positions, my_type)
        opp_links = self._count_friendly_links(state, opp_positions, opp_type)

        my_center = self._center_bonus(dim, my_positions)
        opp_center = self._center_bonus(dim, opp_positions)

        my_count = len(my_positions)
        opp_count = len(opp_positions)

        return (
            14.0 * (my_features["best_component_size"] - opp_features["best_component_size"])
            + 11.0 * (my_features["best_span"] - opp_features["best_span"])
            + 8.0 * (my_features["border_contacts"] - opp_features["border_contacts"])
            + 2.5 * (my_links - opp_links)
            + 1.0 * (my_count - opp_count)
            - 7.0 * (my_features["group_count"] - opp_features["group_count"])
            + 0.20 * (my_center - opp_center)
        )

    def _analyze_groups(self, state: GameStateHex, positions, piece_type: str, vertical_goal: bool):
        pos_set = set(positions)
        visited = set()
        dim = state.get_rep().get_dimensions()[0]

        best_component_size = 0
        best_span = 0
        border_contacts = 0
        group_count = 0

        for start in positions:
            if start in visited:
                continue

            group_count += 1
            stack = [start]
            visited.add(start)
            component = []

            while stack:
                i, j = stack.pop()
                component.append((i, j))

                for _, (t, (ni, nj)) in state.get_neighbours(i, j).items():
                    if t == piece_type and (ni, nj) in pos_set and (ni, nj) not in visited:
                        visited.add((ni, nj))
                        stack.append((ni, nj))

            comp_size = len(component)
            best_component_size = max(best_component_size, comp_size)

            if vertical_goal:
                coords = [i for i, _ in component]
                touches_start = any(i == 0 for i, _ in component)
                touches_end = any(i == dim - 1 for i, _ in component)
            else:
                coords = [j for _, j in component]
                touches_start = any(j == 0 for _, j in component)
                touches_end = any(j == dim - 1 for _, j in component)

            span = max(coords) - min(coords) + 1
            best_span = max(best_span, span)

            if touches_start:
                border_contacts += 1
            if touches_end:
                border_contacts += 1

            if touches_start and touches_end:
                border_contacts += 8

        return {
            "best_component_size": best_component_size,
            "best_span": best_span,
            "border_contacts": border_contacts,
            "group_count": group_count,
        }

    def _count_friendly_links(self, state: GameStateHex, positions, piece_type: str) -> int:
        pos_set = set(positions)
        links = 0

        for i, j in positions:
            for _, (t, (ni, nj)) in state.get_neighbours(i, j).items():
                if t == piece_type and (ni, nj) in pos_set:
                    links += 1

        return links // 2

    def _center_bonus(self, dim: int, positions) -> float:
        if not positions:
            return 0.0

        center = (dim - 1) / 2.0
        score = 0.0

        for i, j in positions:
            dist = abs(i - center) + abs(j - center)
            score += (dim - dist)

        return score