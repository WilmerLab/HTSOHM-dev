import os
import yaml
import numpy as np

from htsohm.runDB_declarative import Base, RunData, session
from htsohm import simulate as sim

def count_bin(run_id, ml_bin, sa_bin, vf_bin):
    c0 = session.query(RunData).filter(          # Not dummy-tested
        RunData.run_id == run_id, RunData.methane_loading_bin == ml_bin,
        RunData.surface_area_bin == sa_bin, RunData.void_fraction_bin == vf_bin,
        RunData.dummy_test_result == None).count()
    c1 = session.query(RunData).filter(          # Passed dummy-test
        RunData.run_id == run_id, RunData.methane_loading_bin == ml_bin,
        RunData.surface_area_bin == sa_bin, RunData.void_fraction_bin == vf_bin,
        RunData.dummy_test_result == 'pass').count()
    bin_count = c0 + c1

    return bin_count

def check_number_of_bins(run_id):
    wd = os.environ['HTSOHM_DIR']
    config_file = os.path.join(wd, 'config', run_id + '.yaml')
    with open(config_file) as yaml_file:
        config = yaml.load(yaml_file)
    bins = config['number-of-bins']

    return bins

def count_all(run_id):
    bins = check_number_of_bins(run_id)
    all_counts = np.zeros([bins, bins, bins])
    for i in range(bins):
        for j in range(bins):
            for k in range(bins):
                b_count = count_bin(run_id, i, j, k)
                all_counts[i,j,k] = b_count

    return all_counts

def select_parents(run_id, children_per_generation, generation):
    bins = check_number_of_bins(run_id)
    counts = count_all(run_id)
    weights = np.zeros([bins, bins, bins])
    for i in range(bins):
        for j in range(bins):
            for k in range(bins):
                if counts[i,j,k] != 0.:
                    weights[i,j,k] = counts.sum() / counts[i,j,k]
    weights = weights / weights.sum()

    w_list = []
    id_list = []
    for i in range(bins):
        for j in range(bins):
            w_list = np.concatenate( [w_list, weights[i,j,:]] )
            for k in range(bins):
                bin_ids = []
                res = session.query(RunData).filter(
                    RunData.run_id == run_id, RunData.methane_loading_bin == i,
                    RunData.surface_area_bin == j,
                    RunData.void_fraction_bin == k,
                    RunData.dummy_test_result == None).all()
                for item in res:
                    bin_ids.append(item.id)
                res = session.query(RunData).filter(
                    RunData.run_id == run_id, RunData.methane_loading_bin == i,
                    RunData.surface_area_bin == j,
                    RunData.void_fraction_bin == k,
                    RunData.dummy_test_result == 'pass').all()
                for item in res:
                    bin_ids.append(item.id)
                id_list = id_list + [bin_ids]

    first = generation * children_per_generation
    last = (generation + 1) * children_per_generation
    new_material_ids = np.arange(first, last)              # IDs for next generation of materials
    new_material_primary_keys = []
    for i in new_material_ids:
        res = session.query(RunData).filter(
            RunData.run_id == run_id, RunData.material_id == str(i))
        for item in res:
            new_material_primary_keys.append(item.id)

    next_materials_list = []
    for i in new_material_primary_keys:
        parent_bin = np.random.choice(id_list, p=w_list)
        parent_id = np.random.choice(parent_bin)           # Select parent for new material
        next_material = [ i, parent_id ]
        next_materials_list.append(next_material)

    for i in next_materials_list:
        row = session.query(RunData).get(i[0])
        row.parent_id = str(i[1])

    return next_materials_list
