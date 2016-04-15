#! /usr/bin/env python

import numpy as np

def bin():

    SA_mc = 119.769879
    ML_a_cc = 71.3912078835
    VF_val = 0.322604
    
    ML_min = 0.
    ML_max = 350.
    SA_min = 0.
    SA_max = 4500.
    VF_min = 0.
    VF_max = 1.

    run_ID = 'thisandthat5'

    bins = int( run_ID[-1] )

    ML_step = ML_max / float(bins)
    SA_step = SA_max / float(bins)
    VF_step = VF_max / float(bins)

    ML_edges = np.arange( ML_min, ML_max + ML_step, ML_step )        
    SA_edges = np.arange( SA_min, SA_max + SA_step, SA_step )
    VF_edges = np.arange( VF_min, VF_max + VF_step, VF_step )

    for i in range( bins ):
        if SA_mc >= SA_edges[i] and SA_mc < SA_edges[i + 1]:
            SA_bin = i
        if ML_a_cc >= ML_edges[i] and ML_a_cc < ML_edges[i + 1]:
            ML_bin = i
        if VF_val >= VF_edges[i] and VF_val < VF_edges[i + 1]:
            VF_bin = i

    print(SA_bin, ML_bin, VF_bin)

if __name__ == "__main__":
    bin()
