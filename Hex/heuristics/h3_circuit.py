import numpy as np

def h3_circuit_resistance(state, piece_type):
    board = state.get_rep()
    env = board.get_env()
    dim = board.get_dimensions()[0]
    node_count = dim * dim + 2
    SOURCE = dim * dim
    SINK = dim * dim + 1

    def solve_resistance(ptype):
        R_PIECE, R_EMPTY, R_OPPONENT = 0.01, 1.0, 1e6
        node_res = np.full(dim * dim, R_EMPTY)
        for pos, piece in env.items():
            r, c = pos
            node_res[r * dim + c] = R_PIECE if piece.get_type() == ptype else R_OPPONENT

        L = np.zeros((node_count, node_count))
        def add_edge(i, j, cond):
            L[i, i] += cond; L[j, j] += cond; L[i, j] -= cond; L[j, i] -= cond

        for r in range(dim):
            for c in range(dim):
                u = r * dim + c
                for _, (_, (nr, nc)) in board.get_neighbours(r, c).items():
                    v = nr * dim + nc
                    if 0 <= nr < dim and 0 <= nc < dim and v > u:
                        cond = 1.0 / ((node_res[u] + node_res[v]) / 2.0)
                        add_edge(u, v, cond)

        if ptype == "R":
            for j in range(dim):
                add_edge(SOURCE, j, 1.0 / (node_res[j] / 2.0))
                add_edge((dim-1)*dim+j, SINK, 1.0 / (node_res[(dim-1)*dim+j] / 2.0))
        else:
            for i in range(dim):
                add_edge(SOURCE, i*dim, 1.0 / (node_res[i*dim] / 2.0))
                add_edge(i*dim+(dim-1), SINK, 1.0 / (node_res[i*dim+(dim-1)] / 2.0))

        reduced_L = np.delete(np.delete(L, SINK, 0), SINK, 1)
        I = np.zeros(node_count - 1); I[SOURCE] = 1.0
        try:
            phi = np.linalg.solve(reduced_L, I)
            return phi[SOURCE]
        except: return 1e6

    opp_piece = "B" if piece_type == "R" else "R"
    r_moi = solve_resistance(piece_type)
    r_adv = solve_resistance(opp_piece)
    if r_moi < 1e-6: return 800
    if r_adv < 1e-6: return -800
    return r_adv / r_moi
