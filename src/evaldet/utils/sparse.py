import numpy as np
from scipy import sparse


def create_coo_array(  # type: ignore
    vals_dict: dict[tuple[int, int], int], shape: tuple[int, int]
) -> sparse.coo_array:
    """Create a sparse COO array.

    Args:
        vals_dict: A dictionary with values. The key should be a tuple of
            ``(row_ind, col_ind)``, and the value should be the entry for the cell
            at that index.
        shape: Shape of the new array: ``(n_rows, n_cols)``
    """
    row_inds = np.array(tuple(x[0] for x in vals_dict))
    col_inds = np.array(tuple(x[1] for x in vals_dict))
    vals = np.array(tuple(vals_dict.values()))

    return sparse.coo_array((vals, (row_inds, col_inds)), shape=shape)
