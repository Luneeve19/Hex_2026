from __future__ import annotations

import heapq
import math
import time
from typing import Dict, List, Optional, Tuple

from game_state_hex import GameStateHex
from player_hex import PlayerHex
from seahorse.game.action import Action


class SearchTimeout(Exception):
    pass


class MyPlayer(PlayerHex):
    """
    Hex player V2.

    Main ideas:
    - iterative deepening
    - alpha-beta pruning
    - transposition table
    - strong move ordering
    - improved two-distance style heuristic
    - bridge / save-bridge patterns
    """

    WIN_SCORE = 1_000_000.0
    INF = 10**12

    TT_EXACT = 0
    TT_LOWER = 1
    TT_UPPER = 2

    # Relative positions of the 6 classical two-bridge patterns in Hex.
    BRIDGE_OFFSETS = [(-2, 1), (-1, -1), (-1, 2), (1, -2), (1, 1), (2, -1)]

    def __init__(self, piece_type: str, name: str = "MyPlayer"):
        super().__init__(piece_type, name)
        self.tt: Dict[tuple, dict] = {}
        self.search_start = 0.0
        self.search_deadline = 0.0
        self.max_depth_completed = 0
        self.root_best_action: Optional[Action] = None

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------
    def compute_action(
        self,
        current_state: GameStateHex,
        remaining_time: float = 15 * 60,
        **kwargs,
    ) -> Action:
        actions = list(current_state.generate_possible_stateful_actions())
        if not actions:
            raise RuntimeError("No legal actions available.")
        if len(actions) == 1:
            return actions[0]

        if len(self.tt) > 200_000:
            self.tt.clear()

        allocated_time = self._allocate_time(current_state, remaining_time)
        self.search_start = time.perf_counter()
        self.search_deadline = self.search_start + allocated_time
        self.max_depth_completed = 0

        ordered_root = self._order_actions(current_state, actions)
        fallback_action = ordered_root[0][0]
        best_action = fallback_action
        self.root_best_action = fallback_action

        max_depth = min(8, len(self._get_empty_cells(current_state)))
        if max_depth < 1:
            max_depth = 1

        for depth in range(1, max_depth + 1):
            try:
                score, action = self._alpha_beta_root(current_state, depth)
                if action is not None:
                    best_action = action
                    self.root_best_action = action
                    self.max_depth_completed = depth
            except SearchTimeout:
                break

        return best_action

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------
    def _alpha_beta_root(self, state: GameStateHex, depth: int) -> tuple[float, Optional[Action]]:
        self._check_timeout()

        alpha = -self.INF
        beta = self.INF
        best_value = -self.INF
        best_action = None

        root_actions = [a for a, _, _ in self._order_actions(state)]

        for action in root_actions:
            self._check_timeout()
            next_state = action.get_next_game_state()
            value = self._alpha_beta(next_state, depth - 1, alpha, beta)
            if value > best_value:
                best_value = value
                best_action = action
            alpha = max(alpha, best_value)

        return best_value, best_action

    def _alpha_beta(self, state: GameStateHex, depth: int, alpha: float, beta: float) -> float:
        self._check_timeout()

        if depth <= 0 or state.is_done():
            return self.heuristic(state)

        maximizing = state.get_active_player().get_piece_type() == self.get_piece_type()
        state_key = self._state_key(state)
        alpha_orig, beta_orig = alpha, beta

        entry = self.tt.get(state_key)
        tt_move = entry.get("best_move") if entry else None
        if entry is not None and entry["depth"] >= depth:
            flag = entry["flag"]
            value = entry["value"]
            if flag == self.TT_EXACT:
                return value
            if flag == self.TT_LOWER:
                alpha = max(alpha, value)
            elif flag == self.TT_UPPER:
                beta = min(beta, value)
            if alpha >= beta:
                return value

        actions = list(state.generate_possible_stateful_actions())
        if not actions:
            return self.heuristic(state)

        ordered = self._order_actions(state, actions, tt_move)
        best_action = None

        if maximizing:
            value = -self.INF
            for action, _, _ in ordered:
                self._check_timeout()
                child = action.get_next_game_state()
                child_value = self._alpha_beta(child, depth - 1, alpha, beta)
                if child_value > value:
                    value = child_value
                    best_action = action
                alpha = max(alpha, value)
                if alpha >= beta:
                    break
        else:
            value = self.INF
            for action, _, _ in ordered:
                self._check_timeout()
                child = action.get_next_game_state()
                child_value = self._alpha_beta(child, depth - 1, alpha, beta)
                if child_value < value:
                    value = child_value
                    best_action = action
                beta = min(beta, value)
                if alpha >= beta:
                    break

        flag = self.TT_EXACT
        if value <= alpha_orig:
            flag = self.TT_UPPER
        elif value >= beta_orig:
            flag = self.TT_LOWER

        self.tt[state_key] = {
            "depth": depth,
            "value": value,
            "flag": flag,
            "best_move": self._action_to_key(state, best_action) if best_action is not None else None,
        }
        return value

    # ------------------------------------------------------------------
    # Heuristic evaluation
    # ------------------------------------------------------------------
    def heuristic(self, state: GameStateHex) -> float:
        if state.is_done():
            scores = state.get_scores()
            my_score = scores.get(self.get_id(), 0)
            return self.WIN_SCORE if my_score > 0 else -self.WIN_SCORE

        my_piece = self.get_piece_type()
        opp_piece = self._opponent_piece(my_piece)

        my_primary, my_secondary = self._two_best_connection_costs(state, my_piece)
        opp_primary, opp_secondary = self._two_best_connection_costs(state, opp_piece)

        my_metric = 2.0 * my_primary + my_secondary
        opp_metric = 2.0 * opp_primary + opp_secondary

        bridge_diff = self._count_bridges(state, my_piece) - self._count_bridges(state, opp_piece)
        threatened_diff = self._count_threatened_bridges(state, my_piece) - self._count_threatened_bridges(state, opp_piece)
        influence_diff = self._influence_score(state, my_piece) - self._influence_score(state, opp_piece)

        return (
            12.0 * (opp_metric - my_metric)
            + 9.0 * bridge_diff
            + 14.0 * threatened_diff
            + 1.5 * influence_diff
        )

    def _two_best_connection_costs(self, state: GameStateHex, piece_type: str) -> tuple[float, float]:
        """
        Practical two-distance style approximation.

        We compute the two best weighted connection costs from one side to the
        opposite side using a two-shortest-path variant of Dijkstra.

        Costs:
        - own stone   -> 0
        - empty cell  -> 1
        - opponent    -> blocked
        """
        board = state.get_rep()
        env = board.get_env()
        rows, cols = board.get_dimensions()

        dist1: Dict[tuple[int, int], float] = {}
        dist2: Dict[tuple[int, int], float] = {}
        pq: List[tuple[float, int, int]] = []

        def cell_cost(pos: tuple[int, int]) -> Optional[int]:
            piece = env.get(pos)
            if piece is None:
                return 1
            if piece.get_type() == piece_type:
                return 0
            return None

        if piece_type == "R":
            starts = [(0, c) for c in range(cols)]
            targets = {(rows - 1, c) for c in range(cols)}
        else:
            starts = [(r, 0) for r in range(rows)]
            targets = {(r, cols - 1) for r in range(rows)}

        for pos in starts:
            c = cell_cost(pos)
            if c is None:
                continue
            if c < dist1.get(pos, self.INF):
                dist1[pos] = c
                dist2.setdefault(pos, self.INF)
                heapq.heappush(pq, (c, pos[0], pos[1]))

        while pq:
            d, r, c = heapq.heappop(pq)
            pos = (r, c)
            best = dist1.get(pos, self.INF)
            second = dist2.get(pos, self.INF)
            if d > second:
                continue

            for nr, nc in self._neighbors_coords(state, pos):
                nxt = (nr, nc)
                w = cell_cost(nxt)
                if w is None:
                    continue
                new_d = d + w

                b1 = dist1.get(nxt, self.INF)
                b2 = dist2.get(nxt, self.INF)

                if new_d < b1:
                    dist2[nxt] = b1
                    dist1[nxt] = new_d
                    heapq.heappush(pq, (new_d, nr, nc))
                    if b1 < self.INF:
                        heapq.heappush(pq, (b1, nr, nc))
                elif b1 < new_d < b2:
                    dist2[nxt] = new_d
                    heapq.heappush(pq, (new_d, nr, nc))
                elif new_d == b1 and new_d < b2:
                    # Keep an equal-strength backup path.
                    dist2[nxt] = new_d
                    heapq.heappush(pq, (new_d, nr, nc))

        candidates: List[float] = []
        for pos in targets:
            d1 = dist1.get(pos, self.INF)
            d2 = dist2.get(pos, self.INF)
            if d1 < self.INF:
                candidates.append(d1)
            if d2 < self.INF:
                candidates.append(d2)

        if not candidates:
            return 500.0, 500.0

        candidates.sort()
        primary = candidates[0]
        secondary = candidates[1] if len(candidates) > 1 else primary + 2.0
        return float(primary), float(secondary)

    def _influence_score(self, state: GameStateHex, piece_type: str) -> float:
        """
        Lightweight global shape feature.
        Rewards stones that are connected to same-color neighbors and that advance
        toward the player objective.
        """
        env = state.get_rep().get_env()
        rows, cols = state.get_rep().get_dimensions()
        score = 0.0

        for pos, piece in env.items():
            if piece.get_type() != piece_type:
                continue

            friendly = 0
            for nb in self._neighbors_coords(state, pos):
                nb_piece = env.get(nb)
                if nb_piece is not None and nb_piece.get_type() == piece_type:
                    friendly += 1
            score += 0.8 * friendly

            if piece_type == "R":
                progress = min(pos[0], rows - 1 - pos[0])
            else:
                progress = min(pos[1], cols - 1 - pos[1])
            score += 0.15 * progress

        return score

    # ------------------------------------------------------------------
    # Move ordering
    # ------------------------------------------------------------------
    def _order_actions(
        self,
        state: GameStateHex,
        actions: Optional[List[Action]] = None,
        tt_move: Optional[tuple] = None,
    ) -> List[tuple[Action, float, tuple[int, int]]]:
        if actions is None:
            actions = list(state.generate_possible_stateful_actions())

        maximizing = state.get_active_player().get_piece_type() == self.get_piece_type()
        current_piece = state.get_active_player().get_piece_type()
        sign = 1.0 if current_piece == self.get_piece_type() else -1.0

        ordered: List[tuple[Action, float, tuple[int, int]]] = []
        current_env = state.get_rep().get_env()

        for action in actions:
            next_state = action.get_next_game_state()
            pos = self._extract_played_position(current_env, next_state.get_rep().get_env())
            score = 0.0

            if next_state.is_done():
                root_win = next_state.get_scores().get(self.get_id(), 0) > 0
                score += self.WIN_SCORE if root_win else -self.WIN_SCORE

            score += sign * 40.0 * self._local_bridge_creation_bonus(next_state, current_piece, pos)
            score += sign * 60.0 * self._local_savebridge_bonus(state, current_piece, pos)
            score += sign * 35.0 * self._local_block_bridge_bonus(state, self._opponent_piece(current_piece), pos)
            score += sign * 12.0 * self._adjacency_bonus(state, current_piece, pos)
            score += sign * 8.0 * self._goal_progress_bonus(state, current_piece, pos)
            score += sign * 3.0 * self._center_bonus(state, pos)

            if tt_move is not None and pos == tt_move:
                score += sign * 100_000.0

            ordered.append((action, score, pos))

        ordered.sort(key=lambda item: item[1], reverse=maximizing)
        return ordered

    def _adjacency_bonus(self, state: GameStateHex, piece_type: str, pos: tuple[int, int]) -> float:
        env = state.get_rep().get_env()
        own = 0
        opp = 0
        opp_piece = self._opponent_piece(piece_type)
        for nb in self._neighbors_coords(state, pos):
            piece = env.get(nb)
            if piece is None:
                continue
            if piece.get_type() == piece_type:
                own += 1
            elif piece.get_type() == opp_piece:
                opp += 1
        return 1.7 * own + 1.2 * opp

    def _goal_progress_bonus(self, state: GameStateHex, piece_type: str, pos: tuple[int, int]) -> float:
        rows, cols = state.get_rep().get_dimensions()
        r, c = pos
        if piece_type == "R":
            return min(r, rows - 1 - r)
        return min(c, cols - 1 - c)

    def _center_bonus(self, state: GameStateHex, pos: tuple[int, int]) -> float:
        rows, cols = state.get_rep().get_dimensions()
        cr = (rows - 1) / 2.0
        cc = (cols - 1) / 2.0
        r, c = pos
        return -abs(r - cr) - abs(c - cc)

    # ------------------------------------------------------------------
    # Bridge / save-bridge patterns
    # ------------------------------------------------------------------
    def _count_bridges(self, state: GameStateHex, piece_type: str) -> int:
        env = state.get_rep().get_env()
        count = 0
        seen = set()

        for pos, piece in env.items():
            if piece.get_type() != piece_type:
                continue
            for dr, dc in self.BRIDGE_OFFSETS:
                other = (pos[0] + dr, pos[1] + dc)
                if not state.in_board(other):
                    continue
                other_piece = env.get(other)
                if other_piece is None or other_piece.get_type() != piece_type:
                    continue

                pair_key = tuple(sorted((pos, other)))
                if pair_key in seen:
                    continue

                common = self._common_neighbors(state, pos, other)
                if len(common) != 2:
                    continue
                if all(env.get(cell) is None for cell in common):
                    seen.add(pair_key)
                    count += 1

        return count

    def _count_threatened_bridges(self, state: GameStateHex, piece_type: str) -> int:
        env = state.get_rep().get_env()
        opp_piece = self._opponent_piece(piece_type)
        count = 0
        seen = set()

        for pos, piece in env.items():
            if piece.get_type() != piece_type:
                continue
            for dr, dc in self.BRIDGE_OFFSETS:
                other = (pos[0] + dr, pos[1] + dc)
                if not state.in_board(other):
                    continue
                other_piece = env.get(other)
                if other_piece is None or other_piece.get_type() != piece_type:
                    continue

                pair_key = tuple(sorted((pos, other)))
                if pair_key in seen:
                    continue

                common = self._common_neighbors(state, pos, other)
                if len(common) != 2:
                    continue

                empties = 0
                opps = 0
                for cell in common:
                    cell_piece = env.get(cell)
                    if cell_piece is None:
                        empties += 1
                    elif cell_piece.get_type() == opp_piece:
                        opps += 1
                if empties == 1 and opps == 1:
                    seen.add(pair_key)
                    count += 1

        return count

    def _local_bridge_creation_bonus(self, next_state: GameStateHex, piece_type: str, pos: tuple[int, int]) -> int:
        env = next_state.get_rep().get_env()
        created = 0
        seen = set()

        for dr, dc in self.BRIDGE_OFFSETS:
            other = (pos[0] + dr, pos[1] + dc)
            if not next_state.in_board(other):
                continue
            other_piece = env.get(other)
            if other_piece is None or other_piece.get_type() != piece_type:
                continue

            pair_key = tuple(sorted((pos, other)))
            if pair_key in seen:
                continue

            common = self._common_neighbors(next_state, pos, other)
            if len(common) != 2:
                continue
            if all(env.get(cell) is None for cell in common):
                seen.add(pair_key)
                created += 1
        return created

    def _local_savebridge_bonus(self, state: GameStateHex, piece_type: str, pos: tuple[int, int]) -> int:
        env = state.get_rep().get_env()
        opp_piece = self._opponent_piece(piece_type)
        saved = 0
        seen = set()

        for stone, piece in env.items():
            if piece.get_type() != piece_type:
                continue
            for dr, dc in self.BRIDGE_OFFSETS:
                other = (stone[0] + dr, stone[1] + dc)
                if not state.in_board(other):
                    continue
                other_piece = env.get(other)
                if other_piece is None or other_piece.get_type() != piece_type:
                    continue

                pair_key = tuple(sorted((stone, other)))
                if pair_key in seen:
                    continue

                common = self._common_neighbors(state, stone, other)
                if len(common) != 2 or pos not in common:
                    continue

                other_common = common[0] if common[1] == pos else common[1]
                other_piece_at_common = env.get(other_common)
                if other_piece_at_common is not None and other_piece_at_common.get_type() == opp_piece:
                    seen.add(pair_key)
                    saved += 1
        return saved

    def _local_block_bridge_bonus(self, state: GameStateHex, opponent_piece: str, pos: tuple[int, int]) -> int:
        env = state.get_rep().get_env()
        blocked = 0
        seen = set()

        for stone, piece in env.items():
            if piece.get_type() != opponent_piece:
                continue
            for dr, dc in self.BRIDGE_OFFSETS:
                other = (stone[0] + dr, stone[1] + dc)
                if not state.in_board(other):
                    continue
                other_piece = env.get(other)
                if other_piece is None or other_piece.get_type() != opponent_piece:
                    continue

                pair_key = tuple(sorted((stone, other)))
                if pair_key in seen:
                    continue

                common = self._common_neighbors(state, stone, other)
                if len(common) != 2 or pos not in common:
                    continue

                if all(env.get(cell) is None for cell in common):
                    seen.add(pair_key)
                    blocked += 1
        return blocked

    # ------------------------------------------------------------------
    # State / move utilities
    # ------------------------------------------------------------------
    def _allocate_time(self, state: GameStateHex, remaining_time: float) -> float:
        empties = len(self._get_empty_cells(state))
        plies_left = max(1, math.ceil(empties / 2))
        reserve = 2.0
        usable = max(0.2, remaining_time - reserve)
        base = usable / plies_left

        if state.get_step() <= 4:
            return min(max(2.0, 1.5 * base), 12.0)
        if empties <= 20:
            return min(max(1.0, 1.2 * base), 15.0)
        return min(max(0.25, 0.9 * base), 8.0)

    def _check_timeout(self) -> None:
        if time.perf_counter() >= self.search_deadline:
            raise SearchTimeout()

    def _state_key(self, state: GameStateHex) -> tuple:
        board = state.get_rep()
        env = board.get_env()
        rows, cols = board.get_dimensions()
        cells = []
        for r in range(rows):
            for c in range(cols):
                piece = env.get((r, c))
                if piece is None:
                    cells.append(".")
                else:
                    cells.append(piece.get_type())
        return ("".join(cells), state.get_active_player().get_piece_type())

    def _action_to_key(self, state: GameStateHex, action: Optional[Action]) -> Optional[tuple[int, int]]:
        if action is None:
            return None
        return self._extract_played_position(
            state.get_rep().get_env(),
            action.get_next_game_state().get_rep().get_env(),
        )

    def _extract_played_position(self, env_before: dict, env_after: dict) -> tuple[int, int]:
        for pos in env_after.keys():
            if pos not in env_before:
                return pos
        raise RuntimeError("Could not extract played position.")

    def _neighbors_coords(self, state: GameStateHex, pos: tuple[int, int]) -> List[tuple[int, int]]:
        r, c = pos
        out = []
        for _, (_, (nr, nc)) in state.get_neighbours(r, c).items():
            if state.in_board((nr, nc)):
                out.append((nr, nc))
        return out

    def _common_neighbors(self, state: GameStateHex, a: tuple[int, int], b: tuple[int, int]) -> List[tuple[int, int]]:
        na = set(self._neighbors_coords(state, a))
        nb = set(self._neighbors_coords(state, b))
        return list(na & nb)

    def _get_empty_cells(self, state: GameStateHex) -> List[tuple[int, int]]:
        return list(state.get_rep().get_empty())

    @staticmethod
    def _opponent_piece(piece_type: str) -> str:
        return "B" if piece_type == "R" else "R"
