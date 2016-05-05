#! /usr/bin/env python

import os
import subprocess
import shlex
import shutil

import numpy as np

from htsohm.runDB_declarative import Base, RunData, create_session

def add_rows(run_id, mat_ids):
#
#    from runDB_declarative import RunData

    s = create_session()

    for i in mat_ids:
        check_first = s.query(RunData).filter( RunData.run_id == run_id,
                                               RunData.material_id == str(i)
                                              ).count()
        if not check_first:
            new_mat = RunData( run_id=run_id, material_id=str(i) )
            s.add(new_mat)
    s.commit()


def update_table(run_id, mat_id, data):
#
#   from runDB_declarative import RunData

    s = create_session()
    material = s.query(RunData).filter( RunData.run_id == run_id,
                                        RunData.material_id == str(mat_id) )
    material.update(data)
    s.commit()


def get_value(run_id, mat_id, value):
#
#    from runDB_declarative import RunData

    s = create_session()
    material = s.query(RunData).filter( RunData.run_id == run_id,
                                     RunData.material_id == str(mat_id) )

    for i in material:
        database_value = getattr(i, value)

    return database_value

def id_to_mat(run_id, ID):
#
#    from runDB_declarative import RunData

    s = create_session()
    material = s.query(RunData).filter( RunData.run_id == run_id,
                                     RunData.id == str(ID) )

    for i in material:
        mat = getattr(i, "material_id")

    return mat


def void_fraction(run_id, mat_id):
#
#    import os
#    import subprocess
#    import shlex

    pwd = os.getcwd()
    
    # Simulate VOID FRACTION:
    vf_input = open( pwd + '/void_fraction.input', "w")
    vf_input.write( "SimulationType\t\t\tMonteCarlo\n" +
                    "NumberOfCycles\t\t\t1000\n" +             # number of MonteCarlo cycles
         "PrintEvery\t\t\t100\n" +
                    "PrintPropertiesEvery\t\t100\n" +
                    "\n" +
                    "Forcefield\t\t\t%s-%s\n" % (run_id, mat_id) +
                    "CutOff\t\t\t\t12.8\n" +                       # LJ interaction cut-off, Angstroms
                    "\n" +
                    "Framework 0\n" +
                    "FrameworkName %s-%s\n" % (run_id, mat_id) +
                    "UnitCells 1 1 1\n" +
                    "ExternalTemperature 298.0\n" +       # External temperature, K
                    "\n" +
                    "Component 0 MoleculeName\t\thelium\n" +
                    "            MoleculeDefinition\t\tTraPPE\n" +
                    "            WidomProbability\t\t1.0\n" +
                    "            CreateNumberOfMolecules\t0\n" )
    vf_input.close()

    subprocess.run(shlex.split('simulate void_fraction.input'), check=True)


def methane_loading(run_id, mat_id):
#
#    import os
#    import subprocess
#    import shlex

    pwd = os.getcwd()

    vf = get_value(run_id, mat_id, "helium_void_fraction")

    # Simulate METHANE LOADING
    ml_input = open( pwd + '/methane_loading.input', "w")
    ml_input.write( "SimulationType\t\t\tMonteCarlo\n" +
                    "NumberOfCycles\t\t\t1000\n" +             # number of MonteCarlo cycles
                    "NumberOfInitializationCycles\t500\n" +    # number of initialization cycles
                    "PrintEvery\t\t\t100\n" +
                    "RestartFile\t\t\tno\n" +
                    "\n" +
                    "Forcefield\t\t\t%s-%s\n" % (run_id, mat_id) +
                    "ChargeMethod\t\t\tEwald\n"
                    "CutOff\t\t\t\t12.0\n" +                   # electrostatic cut-off, Angstroms
                    "\n" +
                    "Framework 0\n" +
                    "FrameworkName %s-%s\n" % (run_id, mat_id) +
                    "UnitCells 1 1 1\n" +
                    "HeliumVoidFraction %s\n" % (vf) +
                    "ExternalTemperature 298.0\n" +            # External temperature, K
                    "ExternalPressure 3500000\n" +             # External pressure, Pa
                    "\n" +
                    "Component 0 MoleculeName\t\tmethane\n" +
                    "            MoleculeDefinition\t\tTraPPE\n" +
                    "            TranslationProbability\t1.0\n" +
                    "            ReinsertionProbability\t1.0\n" +
                    "            SwapProbability\t\t1.0\n" +
                    "            CreateNumberOfMolecules\t0\n" )
    ml_input.close()

    subprocess.run(shlex.split('simulate methane_loading.input'), check=True)

def surface_area(run_id, mat_id):
#
#    import os
#    import subprocess
#    import shlex

    pwd = os.getcwd()

    # Simulate SURFACE AREA:
    sa_input = open( pwd + '/surface_area.input', "w")
    sa_input.write( "SimulationType\t\t\tMonteCarlo\n" +
                    "NumberOfCycles\t\t\t10\n" +             # number of MonteCarlo cycles
                    "PrintEvery\t\t\t1\n" +
                    "PrintPropertiesEvery\t\t1\n" +
                    "\n" +
                    "Forcefield %s-%s\n" % (run_id, mat_id) +
                    "CutOff 12.8\n" +                        # electrostatic cut-off, Angstroms
                    "\n" +
                    "Framework 0\n" +
                    "FrameworkName %s-%s\n" % (run_id, mat_id) +
                    "UnitCells 1 1 1\n" +
                    "SurfaceAreaProbeDistance Minimum\n" +
                    "\n" +
                    "Component 0 MoleculeName\t\tN2\n" +
                    "            StartingBead\t\t0\n" +
                    "            MoleculeDefinition\t\tTraPPE\n" +
                    "            SurfaceAreaProbability\t1.0\n" +
                    "            CreateNumberOfMolecules\t0\n" )
    sa_input.close()

    subprocess.run(shlex.split('simulate surface_area.input'), check=True)

def get_ml(run_id, mat_id):

    methane_loading(run_id, mat_id)

    ml_data = "Output/System_0/output_%s-%s_1.1.1_298.000000_3.5e+06.data" % (run_id, mat_id)
    with open(ml_data) as origin:
        for line in origin:
            if "absolute [mol/kg" in line:
                ml_a_mk = line.split()[5]
            elif "absolute [cm^3 (STP)/g" in line:
                ml_a_cg = line.split()[6]
            elif "absolute [cm^3 (STP)/c" in line:
                ml_a_cc = line.split()[6]
            elif "excess [mol/kg" in line:
                ml_e_mk = line.split()[5]
            elif "excess [cm^3 (STP)/g" in line:
                ml_e_cg = line.split()[6]
            elif "excess [cm^3 (STP)/c" in line:
                ml_e_cc = line.split()[6]

    data = {"absolute_volumetric_loading": ml_a_cc,
            "absolute_gravimetric_loading": ml_a_cg,
            "absolute_molar_loading": ml_a_mk,
            "excess_volumetric_loading": ml_e_cc,
            "excess_gravimetric_loading": ml_e_cg,
            "excess_molar_loading": ml_e_mk}
    update_table(run_id, mat_id, data)

    print( "\nMETHANE LOADING\tabsolute\texcess\n" +
           "mol/kg\t\t%s\t%s\n" % (ml_a_mk, ml_e_mk) +
           "cc/g\t\t%s\t%s\n" % (ml_a_cg, ml_e_cg) +
           "cc/cc\t\t%s\t%s\n" % (ml_a_cc, ml_e_cc) )

    #STILL NEED TO GREP HEATDESORP
    os.remove("methane_loading.input")
    shutil.rmtree("Output")
    shutil.rmtree("Movies")
    shutil.rmtree("VTK")
    shutil.rmtree("Restart")


def get_sa(run_id, mat_id):
    surface_area(run_id, mat_id)

    sa_data = "Output/System_0/output_%s-%s_1.1.1_298.000000_0.data" % (run_id, mat_id)
    with open(sa_data) as origin:
        count = 0
        for line in origin:
            if "Surface area" in line:
                if count == 0:
                    sa_a2 = line.split()[2]
                    count = count + 1
                elif count == 1:
                    sa_mg = line.split()[2]
                    count = count + 1
                elif count == 2:
                    sa_mc = line.split()[2]
    
    data = {"unit_cell_surface_area": sa_a2,
            "volumetric_surface_area": sa_mc,
            "gravimetric_surface_area": sa_mg}
    update_table(run_id, mat_id, data)

    print( "\nSURFACE AREA\n" +
           "%s\tA^2\n" % (sa_a2) +
           "%s\tm^2/g\n" % (sa_mg) +
           "%s\tm^2/cm^3" % (sa_mc) )

    os.remove("surface_area.input")
    shutil.rmtree("Output")
    shutil.rmtree("Movies")
    shutil.rmtree("VTK")
    shutil.rmtree("Restart")


def get_vf(run_id, mat_id):

    void_fraction(run_id, mat_id)

    vf_data = "Output/System_0/output_%s-%s_1.1.1_298.000000_0.data" % (run_id, mat_id)
    with open(vf_data) as origin:
        for line in origin:
            if not "Average Widom Rosenbluth-weight:" in line:
                continue
            try:
                vf_val = float(line.split()[4][:-1])
            except IndexError:
                print()

    print( "\nVOID FRACTION :   %s\n" % (vf_val) )

    # Add to database...
    data = {"helium_void_fraction": vf_val}
    update_table(run_id, mat_id, data)

    os.remove("void_fraction.input")
    shutil.rmtree("Output")
    shutil.rmtree("Movies")
    shutil.rmtree("VTK")
    shutil.rmtree("Restart")


def get_bins(run_id, mat_id):
   
    ml = get_value(run_id, mat_id, "absolute_volumetric_loading")
    sa = get_value(run_id, mat_id, "volumetric_surface_area")
    vf = get_value(run_id, mat_id, "helium_void_fraction")
 
    # Arbitary structure-property space "boundaries"
    ml_min = 0.
    ml_max = 350.
    sa_min = 0.
    sa_max = 4500.
    vf_min = 0.
    vf_max = 1.

    bins = int( run_id[-1] )

    ml_step = ml_max / float(bins)
    sa_step = sa_max / float(bins)
    vf_step = vf_max / float(bins)

    ml_edges = np.arange( ml_min, ml_max + ml_step, ml_step )
    sa_edges = np.arange( sa_min, sa_max + sa_step, sa_step )
    vf_edges = np.arange( vf_min, vf_max + vf_step, vf_step )

    for i in range( bins ):
        if sa >= sa_edges[i] and sa < sa_edges[i + 1]:
            sa_bin = i
        if ml >= ml_edges[i] and ml < ml_edges[i + 1]:
            ml_bin = i
        if vf >= vf_edges[i] and vf < vf_edges[i + 1]:
            vf_bin = i

    data = {"methane_loading_bin": str(ml_bin),
            "surface_area_bin": str(sa_bin),
            "void_fraction_bin": str(vf_bin)}
    update_table(run_id, mat_id, data)


def simulate(run_id, mat_ids):
   for i in mat_ids:
       get_vf(run_id, i)
       get_ml(run_id, i)
       get_sa(run_id, i)
       get_bins(run_id, i)


def dummy_test(run_id, generation):
#
#    import os
#    import subprocess
#    import shlex
#    import shutil
#
#    from sqlalchemy import create_engine
#    from sqlalchemy.orm import sessionmaker
#
#    from runDB_declarative import RunData, Base
#
#    import numpy as np

    s = create_session()

    tolerance = 0.05      # Acceptable deviation from original value(s)...
    number_of_trials = 1    # Number of times each simulation is repeated.

    wd = os.environ['HTSOHM_DIR']
    with open(wd + '/' + run_id + '.txt') as origin:
        for line in origin:
            if "Children per generation:" in line:
                children_per_generation = int(line.split()[3])
    first = generation * children_per_generation
    last = (generation + 1) * children_per_generation
    child_ids = np.arange(first, last)

    parents_ids = []
    for i in child_ids:

        parent_id = get_value(run_id, i, "parent_id")
        if parent_id not in parents_ids:
            parents_ids.append(parent_id)

    bad_materials = []
    for i in parents_ids:
        material_id = id_to_mat(run_id, i)

        print( "\nRe-Simulating %s-%s...\n" % (run_id, material_id) )

        ml_o = get_value(run_id, material_id, "absolute_volumetric_loading")
        sa_o = get_value(run_id, material_id, "volumetric_surface_area")
        vf_o = get_value(run_id, material_id, "helium_void_fraction")

        vfs = []
        for j in range(number_of_trials):
            void_fraction(run_id, material_id)
            vf_data = ( "Output/System_0/output_" +
                        "%s-%s_1.1.1_298.000000_0.data" % (run_id, material_id)
                        )
            with open(vf_data) as origin:
                for line in origin:
#                    if not "Average Widom:" in line:
#                        continue
#                    try:
#                        vf_val = line.split()[3]
#                    except IndexError:
#                        print()
                    if not "Average Widom Rosenbluth-weight:" in line:       #ONLY ON AKAIJA BUILD
                        continue
                    try:
                        vf_val = line.split()[4]
                    except IndexError:
                        print()

            vfs.append( float(vf_val) )

        mls = []
        for j in range(number_of_trials):
            methane_loading(run_id, material_id)
            ml_data = ( "Output/System_0/output_" + 
                        "%s-%s_1.1.1_298.000000_" % (run_id, material_id) +
                        "3.5e+06.data" )
            with open(ml_data) as origin:
                for line in origin:
                    if "absolute [cm^3 (STP)/c" in line:
                        ml_a_cc = line.split()[6]
            mls.append( float(ml_a_cc) )

        sas = []
        for j in range(number_of_trials):
            surface_area(run_id, material_id)
            sa_data = ( "Output/System_0/output_" + 
                        "%s-%s_1.1.1_298.000000_0.data" % (run_id, material_id)
                        )
            with open(sa_data) as origin:
                count = 0
                for line in origin:
                    if "Surface area" in line:
                        if count == 0:
                            sa_a2 = line.split()[2]
                            count = count + 1
                        elif count == 1:
                            sa_mg = line.split()[2]
                            count = count + 1
                        elif count == 2:
                            sa_mc = line.split()[2]
            sas.append( float(sa_mc) )

        if abs(np.mean(mls) - ml_o) >= tolerance * ml_o:
            bad_materials.append(i)
        if abs(np.mean(sas) - sa_o) >= tolerance * sa_o:
            bad_materials.append(i)
        if abs(np.mean(vfs) - vf_o) >= tolerance * vf_o:
            bad_materials.append(i)

    failed = []
    for i in bad_materials:
        if i not in failed:
            failed.append(i)

    for i in parents_ids:
        material_id = id_to_mat(run_id, i)
        if i not in failed:
            data = {"dummy_test_result": 'y'}
            update_table(run_id, material_id, data)
        elif i in failed:
            data = {"dummy_test_result": 'n'}
            update_table(run_id, material_id, data)
#            AffectedMats = s.query(RunData).filter(RunData.run_id == run_id,
#                                                   RunData.parent_id == i
#                                                   ).all()
#            Maybes = [j.Mat for j in AffectedMats]
#            for j in Maybes:
#                update_table(run_id, j, data)
                                                    
    if len(failed) == 0:
        print( "\nALL PARENTS IN GENERATION " + 
               "%s PASSED THE DUMMY TEST.\n" % (generation) )
    if len(failed) != 0:
        print( "\nTHE FOLLOWING PARENTS IN GENERATION " +
               "%s FAIL THE DUMMY TEST:" % (generation) )
        for i in failed:
            material_id = id_to_mat(run_id, i)
            print( "\t%s-%s\n" % (run_id, material_id) )


if __name__ == "__main__":
    import sys
    simulate(str(sys.argv[1]),
             int(sys.argv[2]))
