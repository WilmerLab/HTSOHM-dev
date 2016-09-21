# related third party imports
import numpy as np
from sqlalchemy import func, or_

# local application/library specific imports
from htsohm.db import Base, Material, session

def select_parent(run_id, max_generation, generation_limit):
    """Use bin-counts to preferentially select a list of rare parents.

    Each bin contains some number of materials, and those bins with the fewers materials represent
    the most rare structure-property combinations. These rare materials are preferred as parents
    for new materials, because their children are most likely to display unique properties. This
    function first calculates a `weight` for each bin, based on the number of constituent
    materials. These weights affect the probability of selecting a parent from that bin. Once a bin
    is selected, a parent is randomly-selected from those materials within that bin.
    """

    # Each bin is counted...
    bins_and_counts = session \
        .query(
            func.count(Material.id),
            Material.methane_loading_bin,
            Material.surface_area_bin,
            Material.void_fraction_bin
        ) \
        .filter(
            Material.run_id == run_id,
            or_(Material.retest_passed == True, Material.retest_passed == None),
            Material.generation <= max_generation,
            Material.generation_index < generation_limit,
        ) \
        .group_by(
            Material.methane_loading_bin, Material.surface_area_bin, Material.void_fraction_bin
        ).all()[1:]
    bins = [{"ML" : i[1], "SA" : i[2], "VF" : i[3]} for i in bins_and_counts]
    total = sum([i[0] for i in bins_and_counts])
    # ...then assigned a weight.
    weights = [i[0] / float(total) for i in bins_and_counts]

    parent_bin = np.random.choice(bins, p=weights)
    parent_query = session \
        .query(Material.id) \
        .filter(
            Material.run_id == run_id,
            or_(Material.retest_passed == True, Material.retest_passed == None),
            Material.methane_loading_bin == parent_bin["ML"],
            Material.surface_area_bin == parent_bin["SA"],
            Material.void_fraction_bin == parent_bin["VF"],
            Material.generation <= max_generation,
            Material.generation_index < generation_limit,
        ).all()
    potential_parents = [i[0] for i in parent_query]

    return int(np.random.choice(potential_parents))
