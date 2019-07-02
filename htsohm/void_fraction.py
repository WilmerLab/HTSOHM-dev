
import itertools
from math import sqrt, ceil

import numpy as np

def calculate_void_fraction(atoms, box, points_per_angstrom=10):
    """ assumes box starts at (0,0,0)
    """
    xi_max = box[0] * points_per_angstrom
    yi_max = box[1] * points_per_angstrom
    zi_max = box[2] * points_per_angstrom

    dx = 1 / points_per_angstrom
    dy = 1 / points_per_angstrom
    dz = 1 / points_per_angstrom

    lattice_fill = np.zeros((xi_max, yi_max, zi_max))

    for x, y, z, r in atoms:
        delt_i = ceil(r / dx)
        xi = int(x // dx); yi = int(y // dy); zi = int(z // dz)

        # limit the lattice_indices to only crossing a boundary once in each direction
        lattice_indices = itertools.product(
            range(max(xi - delt_i, -xi_max), min(xi + delt_i + 1, 2*xi_max)),
            range(max(yi - delt_i, -yi_max), min(yi + delt_i + 1, 2*yi_max)),
            range(max(zi - delt_i, -zi_max), min(zi + delt_i + 1, 2*zi_max)))

        for lxi, lyi, lzi in lattice_indices:
            lx = lxi * dx; ly = lyi * dy; lz = lzi * dz
            if sqrt((lx - x)**2 + (ly - y)**2 + (lz -z)**2) < r:
                lattice_fill[lxi % xi_max, lyi % xi_max, lzi % xi_max] = 1.0

    return 1 - np.sum(lattice_fill) / (xi_max * yi_max * zi_max)
