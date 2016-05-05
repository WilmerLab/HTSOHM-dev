import numpy as np

from htsohm.runDB_declarative import Base, RunData
from htsohm.simulate import create_session, get_value, add_rows, update_table


def count_bin(run_id, ml_bin, sa_bin, vf_bin):
    
    s = create_session()
    c0 = s.query(RunData).filter(RunData.run_id == run_id,              # Not dummy-tested
                                 RunData.methane_loading_bin == ml_bin,
                                 RunData.surface_area_bin == sa_bin,
                                 RunData.void_fraction_bin == vf_bin,
                                 RunData.dummy_test_result == None).count()
    c1 = s.query(RunData).filter(RunData.run_id == run_id,              # Passed dummy-test
                                 RunData.methane_loading_bin == ml_bin,
                                 RunData.surface_area_bin == sa_bin,
                                 RunData.void_fraction_bin == vf_bin,
                                 RunData.dummy_test_result == 'y').count()
#    c2 = s.query(RunData).filter(RunData.Run == run_id,              # Parent failed dummy-test, child not tested
#                                 RunData.Bin_ML == ml_bin,
#                                 RunData.Bin_SA == sa_bin,
#                                 RunData.Bin_VF == vf_bin,
#                                 RunData.D_pass == 'm').count()


    bin_count = c0 + c1 #+ c2

    return bin_count


def count_all(run_id):

    bins = int(run_id[-1])
    all_counts = np.zeros([bins, bins, bins])

    for i in range(bins):
        for j in range(bins):
            for k in range(bins):
                
                b_count = count_bin(run_id, i, j, k)
                all_counts[i,j,k] = b_count

    return all_counts


def select_parents(run_id, children_per_generation, generation):

    s = create_session()

    bins = int(run_id[-1])
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
                res = s.query(RunData).filter(RunData.run_id == run_id,
                                              RunData.methane_loading_bin == i,
                                              RunData.surface_area_bin == j,
                                              RunData.void_fraction_bin == k,
                                              RunData.dummy_test_result == None
                                              ).all()
                for item in res:
                    bin_ids.append(item.material_id)
                res = s.query(RunData).filter(RunData.run_id == run_id,
                                              RunData.methane_loading_bin == i,
                                              RunData.surface_area_bin == j,
                                              RunData.void_fraction_bin == k,
                                              RunData.dummy_test_result == 'y'
                                              ).all()
                for item in res:
                    bin_ids.append(item.material_id)
#                res = s.query(RunData).filter(RunData.Run == run_id,
#                                              RunData.Bin_ML == i,
#                                              RunData.Bin_SA == j,
#                                              RunData.Bin_VF == k,
#                                              RunData.D_pass == 'm').all()
#                for item in res:
#                    bin_ids.append(item.Mat)
                id_list = id_list + [bin_ids]

    first = generation * children_per_generation
    last = (generation + 1) * children_per_generation
    new_mat_ids = np.arange(first, last)                   # IDs for next generation of materials

    for i in new_mat_ids:

        p_bin = np.random.choice(id_list, p=w_list)
        p_ID = np.random.choice(p_bin)                     # Select parent for new material

        _id =get_value(run_id, p_ID, "id")

        add_rows(run_id, [i])
        data = {'parent_id': _id}
        update_table(run_id, i, data)
   

#def CheckConvergance(run_id):
#
#    counts = count_all(run_id)
       
