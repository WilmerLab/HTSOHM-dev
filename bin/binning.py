import numpy as np
import os

def bin3d(p_dir, bins):

    ml_file = p_dir + '/ch4_abs_cc_cc.txt'
    sa_file = p_dir + '/SAdata_m2_cc.txt'
    vf_file = p_dir + '/HVdata2col.txt'

    def bin_data(data_file, e_min, e_max, bins):  # bins data in one dimension (ml, sa, or vf) 
    
        name = np.genfromtxt(data_file, usecols=0, dtype=str)
        valu = np.genfromtxt(data_file, usecols=1, dtype=float)
    
        step = e_max / bins
        edge = np.arange(e_min, e_max + step, step)
        
        IDs = [ [] for i in range(bins) ]
    
        for i in range(bins):
        
            lower = edge[i]
            upper = edge[i + 1]
        
            for j in range( len(valu)):
                if valu[j] >= lower and valu[j] < upper:
                    IDs[i].append(name[j])
                
        return IDs
    
    ml_IDs = bin_data(ml_file, 0, 400., bins)
    sa_IDs = bin_data(sa_file, 0, 4500., bins)
    vf_IDs = bin_data(vf_file, 0, 1., bins)

    bin_IDs = [ [ [[] for i in range(bins)] for j in range(bins)] for k in range(bins)] # make empty 3D list

    freq = np.zeros([bins, bins, bins])

    for i in range(bins):
        for j in range(bins):
            for k in range(bins):
                for l in ml_IDs[i]:
                    for m in sa_IDs[j]:
                        if l == m:
                            for n in vf_IDs[k]:
                                if m == n:
                                    bin_IDs[i][j][k].append(n)

    bin_counts = np.empty([bins,bins,bins])  # 3D array containing number of materials per bin

    for i in range(bins):
        for j in range(bins):
            for k in range(bins):
                bin_counts[i,j,k] = len(bin_IDs[i][j][k])
            
    return bin_counts, bin_IDs
  
def find_bin(name, ID_array):
    
    dim = len(ID_array)
    
    for i in range(dim):
        for j in range(dim):
            for k in range(dim):
                if name in ID_array[i][j][k]:
                    
                    a = i
                    b = j
                    c = k
                    
    return [a, b, c]

def pick_parents(p_dir, bin_counts, bin_IDs, n_children, n_dummy=5):

    bins = len(bin_counts)

    weights = np.zeros([bins, bins, bins])

    for i in range(bins):
        for j in range(bins):
            for k in range(bins):

                if bin_counts[i][j][k] != 0.:

                    weights[i][j][k] = bin_counts.sum() / bin_counts[i][j][k]

    weights = weights / weights.sum() 

    w_list = []
    ID_list = []

    for i in range(bins):
        for j in range(bins):

            w_list = np.concatenate([w_list, weights[i,j,:]])

            for k in range(bins):

                ID_list = ID_list + [bin_IDs[i][j][k]]

    p_list = []
    dummyList = open(os.path.abspath(p_dir) + '/dummyList.txt', 'w')
    p_file = open(os.path.abspath(p_dir) + '/p_list.txt', 'w')

    for i in range(n_children):

        p = np.random.choice(ID_list, p=w_list)
        pos = find_bin(p[0], bin_IDs)

        p_list.append([p[0], pos])
        p_file.write((p[0] + '\t' + str(pos) + '\n'))

    d_list = []
    dummyList = open(os.path.abspath(p_dir) + '/dummyList.txt', 'w')

    for i in p_list:
        if i[0] not in d_list:
            d_list.append(i[0])
            for j in range(n_dummy):
                dummyList.write((i[0] + '\n'))
        
    return p_list  
    
