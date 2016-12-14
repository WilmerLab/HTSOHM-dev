import sys
import os
import subprocess
import shutil
from datetime import datetime
from uuid import uuid4

import htsohm
from htsohm import config

def write_raspa_file(filename, run_id, material_id):
    """Writes RASPA input file for calculating surface area.

    Args:
        filename (str): path to input file.
        run_id (str): identification string for run.
        material_id (str): uuid for material.

    Writes RASPA input-file.

    """
    simulation_cycles = config['surface_area']['simulation_cycles']
    with open(filename, "w") as raspa_input_file:
        raspa_input_file.write(
            "SimulationType\t\t\tMonteCarlo\n" +
            "NumberOfCycles\t\t\t%s\n" % (simulation_cycles) +             # number of MonteCarlo cycles
            "PrintEvery\t\t\t1\n" +
            "PrintPropertiesEvery\t\t1\n" +
            "\n" +
            "Forcefield %s-%s\n" % (run_id, material_id) +
            "CutOff 12.8\n" +                        # electrostatic cut-off, Angstroms
            "\n" +
            "Framework 0\n" +
            "FrameworkName %s-%s\n" % (run_id, material_id) +
            "UnitCells 1 1 1\n" +
            "SurfaceAreaProbeDistance Minimum\n" +
            "\n" +
            "Component 0 MoleculeName\t\tN2\n" +
            "            StartingBead\t\t0\n" +
            "            MoleculeDefinition\t\tTraPPE\n" +
            "            SurfaceAreaProbability\t1.0\n" +
            "            CreateNumberOfMolecules\t0\n")

def parse_output(output_file):
    """Parse output file for void fraction data.

    Args:
        output_file (str): path to simulation output file.

    Returns:
        results (dict): total unit cell, gravimetric, and volumetric surface
            areas.

    """
    results = {}
    with open(output_file) as origin:
        count = 0
        for line in origin:
            if "Surface area" in line:
                if count == 0:
                    results['sa_unit_cell_surface_area'] = float(line.split()[2])
                    count = count + 1
                elif count == 1:
                    results['sa_gravimetric_surface_area'] = float(line.split()[2])
                    count = count + 1
                elif count == 2:
                    results['sa_volumetric_surface_area'] = float(line.split()[2])

    print(
        "\nSURFACE AREA\n" +
        "%s\tA^2\n"      % (results['sa_unit_cell_surface_area']) +
        "%s\tm^2/g\n"    % (results['sa_gravimetric_surface_area']) +
        "%s\tm^2/cm^3"   % (results['sa_volumetric_surface_area']))
    return results

def run(run_id, material_id):
    """Runs surface area simulation.

    Args:
        run_id (str): identification string for run.
        material_id (str): unique identifier for material.

    Returns:
        results (dict): surface area simulation results.

    """
    simulation_directory  = config['simulations_directory']
    if simulation_directory == 'HTSOHM':
        htsohm_dir = os.path.dirname(os.path.dirname(htsohm.__file__))
        path = os.path.join(htsohm_dir, run_id)
    elif simulation_directory == 'SCRATCH':
        path = os.environ['SCRATCH']
    else:
        print('OUTPUT DIRECTORY NOT FOUND.')
    output_dir = os.path.join(path, 'output_%s_%s' % (material_id, uuid4()))
    print("Output directory :\t%s" % output_dir)
    os.makedirs(output_dir, exist_ok=True)
    filename = os.path.join(output_dir, "SurfaceArea.input")
    write_raspa_file(filename, run_id, material_id)
    while True:
        try:
            print("Date :\t%s" % datetime.now().date().isoformat())
            print("Time :\t%s" % datetime.now().time().isoformat())
            print("Calculating surface area of %s-%s..." % (run_id, material_id))
            subprocess.run(['simulate', './SurfaceArea.input'], check=True, cwd=output_dir)

            filename = "output_%s-%s_1.1.1_298.000000_0.data" % (run_id, material_id)
            output_file = os.path.join(output_dir, 'Output', 'System_0', filename)
            results = parse_output(output_file)
            shutil.rmtree(output_dir, ignore_errors=True)
            sys.stdout.flush()
        except (FileNotFoundError, KeyError) as err:
            print(err)
            print(err.args)
            continue
        break

    return results
