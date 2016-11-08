import sys
import os
import subprocess
import shutil
from datetime import datetime
from uuid import uuid4

import htsohm
from htsohm import config

#from htsohm.files import load_config_file
#config = load_config_file('settings/dev_run.yaml')

def write_raspa_file(filename, run_id, material_id):
    simulation_cycles = config['helium_void_fraction']['simulation_cycles']
    with open(filename, "w") as raspa_input_file:
        raspa_input_file.write(
            "SimulationType\t\t\tMonteCarlo\n" +
            "NumberOfCycles\t\t\t%s\n" % simulation_cycles +     # number of MonteCarlo cycles
            "PrintEvery\t\t\t10\n" +
            "PrintPropertiesEvery\t\t10\n" +
            "\n" +
            "Forcefield\t\t\t%s-%s\n" % (run_id, material_id) +
            "CutOff\t\t\t\t12.8\n" +           # LJ interaction cut-off, Angstroms
            "\n" +
            "Framework 0\n" +
            "FrameworkName %s-%s\n" % (run_id, material_id) +
            "UnitCells 1 1 1\n" +
            "ExternalTemperature 298.0\n" +    # External temperature, K
            "\n" +
            "Component 0 MoleculeName\t\thelium\n" +
            "            MoleculeDefinition\t\tTraPPE\n" +
            "            WidomProbability\t\t1.0\n" +
            "            CreateNumberOfMolecules\t0\n")

def parse_output(output_file):
    results = {}
    with open(output_file) as origin:
        for line in origin:
            if not "Average Widom Rosenbluth-weight:" in line:
                continue
            results['vf_helium_void_fraction'] = float(line.split()[4])
        print("\nVOID FRACTION :   %s\n" % (results['vf_helium_void_fraction']))
    return results

def run(run_id, material_id):
    simulation_directory  = config['simulations_directory']
#    simulation_directory = 'HTSOHM'
    if simulation_directory == 'HTSOHM':
        htsohm_dir = os.path.dirname(os.path.dirname(htsohm.__file__))
        path = os.path.join(htsohm_dir, run_id)
    elif simulation_directory == 'SCRATCH':
        path = os.environ['SCRATCH']
    else:
        print('OUTPUT DIRECTORY NOT FOUND.')
        sys.stdout.flush()
    output_dir = os.path.join(path, 'output_%s_%s' % (material_id, uuid4()))
    print("Output directory :\t%s" % output_dir)
    os.makedirs(output_dir, exist_ok=True)
    filename = os.path.join(output_dir, "VoidFraction.input")
    write_raspa_file(filename, run_id, material_id)
    while True:
        try:
            print("Date :\t%s" % datetime.now().date().isoformat())
            print("Time :\t%s" % datetime.now().time().isoformat())
            print("Calculating void fraction of %s-%s..." % (run_id, material_id))
            sys.stdout.flush()
            subprocess.run(['simulate', './VoidFraction.input'], check=True, cwd=output_dir)
            filename = "output_%s-%s_1.1.1_298.000000_0.data" % (run_id, material_id)
            output_file = os.path.join(output_dir, 'Output', 'System_0', filename)
            results = parse_output(output_file)
            shutil.rmtree(output_dir, ignore_errors=True)
        except (FileNotFoundError, IndexError, KeyError) as err:
            print(err)
            print(err.args)
            continue
        break

    return results
