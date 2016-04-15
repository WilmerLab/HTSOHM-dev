# /usr/bin/env python

def HTSOHM(children_per_generation,    # number of materials per generation
           number_of_atomtypes,        # number of atom-types per material
           strength_0,                 # intial strength parameter
           number_of_bins,             # number of bins for analysis
           max_generations=20):        # maximum number of generations

    # Start run (see DD.MM.YYYY_HH.MM.SS_CpG.NoA_S0_NoB.txt for parameters)
    
    import sys
    import os
    import datetime 

    sys.path.insert(0, os.environ['SRC_DIR'])

    start = datetime.datetime.now()
    run_ID = ( "%s.%s.%s_%s.%s.%s_%s.%s_%s_%s" %
               (start.day, start.month, start.year,
                start.hour, start.minute, start.second,
                children_per_generation, number_of_atomtypes,
                strength_0,
                number_of_bins))

    wd = os.environ['HTSOHM_DIR']      # specify working directory          

    run_file = open( wd + '/' + run_ID + '.txt', "w")
    run_file.write( "Date:\t\t\t\t%s:%s:%s\n" % (start.day, start.month,
                                                 start.year) +
                    "Time:\t\t\t\t%s:%s:%s\n" % (start.hour, start.minute, 
                                                 start.second) +
                    "Children per generation:\t%s\n" % (
                                                 children_per_generation) +
                    "Number of atom-types:\t\t%s\n" % (number_of_atomtypes) +
                    "Initial mutation strength:\t%s\n" % (strength_0) +
                    "Number of bins:\t\t\t%s\n" % (number_of_bins))
    run_file.close()


    # Create seed population
    import generate as gen             # materials' generation script(s)

    gen.generate(children_per_generation, number_of_atomtypes, run_ID)
    SimulateNext = range( children_per_generation )

    import simulate as sim             # run simulations, output data to HTSOHM-dev.db
    # Screen seed population
    for i in SimulateNext:
        sim.simulate(run_ID, i)

    import numpy as np
    generation = 1                     # `Generation` counter
    first = generation * children_per_generation
    last = (generation + 1) * children_per_generation
    SimulateNext = np.arange(first, last)

    import binning as bng
    # Select parents, add IDs to database...
    bng.SelectParents(run_ID, children_per_generation, generation)
    sim.DummyTest(run_ID, generation)
    
    # Create `first` generation of child-materials
    import mutate as mut
    mut.FirstS(run_ID, strength_0)     # Create strength-parameter array `run_ID`.npy
    mut.mutate(run_ID, generation)     # Create first generation of child-materials

    for i in SimulateNext:
        sim.simulate(run_ID, i)

    # Iterate for following generation(s)...
    NextGeneration = np.arange(2, max_generations)
    for i in NextGeneration:
        generation = i
        first = generation * children_per_generation
        last = (generation + 1) * children_per_generation
        NextMaterials = np.arange(first, last)

        bng.SelectParents(run_ID, children_per_generation, generation)
        sim.DummyTest(run_ID, generation)
        mut.CalculateS(run_ID, generation)
        mut.mutate(run_ID, generation)

        for j in NextMaterials:
            sim.simulate(run_ID, j)
        
if __name__ == "__main__":
    import sys
    HTSOHM(int(sys.argv[1]),
           int(sys.argv[2]),
           float(sys.argv[3]),
           int(sys.argv[4]))
