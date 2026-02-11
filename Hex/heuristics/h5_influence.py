import numpy as np

def h5_influence_map(state, my_piece):
    board = state.get_rep()
    env = board.get_env()
    rows, cols = board.get_dimensions()
    grid = np.zeros((rows, cols))
    for (r, c), piece in env.items():
        val = 10 if piece.get_type() == my_piece else -10
        grid[r, c] += val
        for _, (_, (nr, nc)) in board.get_neighbours(r, c).items():
            if 0 <= nr < rows and 0 <= nc < cols:
                grid[nr, nc] += (val * 0.5)
                for _, (_, (nnr, nnc)) in board.get_neighbours(nr, nc).items():
                    if 0 <= nnr < rows and 0 <= nnc < cols and (nnr, nnc) != (r, c):
                        grid[nnr, nnc] += (val * 0.2)
    return np.sum(grid)
