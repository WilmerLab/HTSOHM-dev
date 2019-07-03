
from glob import glob
import math
import os
import shutil
import sys
import subprocess

from datetime import datetime
from uuid import uuid4
from string import Template
from pathlib import Path

from htsohm.material_files import write_mol_file, write_mixing_rules
from htsohm.material_files import write_pseudo_atoms, write_force_field
from htsohm.simulation.files import load_and_subs_template
from htsohm.db import VoidFraction
from htsohm.void_fraction import calculate_void_fraction

def write_raspa_file(filename, material, simulation_config):
    """Writes RASPA input file for calculating helium void fraction.

    Args:
        filename (str): path to input file.
        run_id (str): identification string for run.
        material_id (str): uuid for material.

    Writes RASPA input-file.

    """

    # Load simulation parameters from config
    unit_cells = material.structure.minimum_unit_cells(simulation_config['cutoff'])
    values = {
            "Cutoff"                 : simulation_config['cutoff'],
            "NumberOfCycles"         : simulation_config["simulation_cycles"],
            "FrameworkName"          : material.uuid,
            "ExternalTemperature"    : simulation_config["temperature"],
            "MoleculeName"           : simulation_config["adsorbate"],
            "UnitCell"               : " ".join(map(str, unit_cells))}

    # Load template and replace values
    input_data = load_and_subs_template("input_file_templates/void_fraction.input", values)

    # Write simulation input-file
    with open(filename, "w") as raspa_input_file:
        raspa_input_file.write(input_data)

def write_output_files(material, simulation_config, output_dir):
    # Write simulation input-files
    # RASPA input-file
    filename = os.path.join(output_dir, "void_fraction.input")
    write_raspa_file(filename, material, simulation_config)
    # Pseudomaterial mol-file
    write_mol_file(material, output_dir)
    # Lennard-Jones parameters, force_field_mixing_rules.def
    write_mixing_rules(material.structure, output_dir)
    # Pseudoatom definitions, pseudo_atoms.def (placeholder values)
    write_pseudo_atoms(material.structure, output_dir)
    # Overwritten interactions, force_field.def (none overwritten by default)
    write_force_field(output_dir)

def parse_output(output_file, material, simulation_config):
    """Parse output file for void fraction data.

    Args:
        output_file (str): path to simulation output file.

    Returns:
        results (dict): average Widom Rosenbluth-weight.

    """
    void_fraction = VoidFraction()
    void_fraction.adsorbate = simulation_config["adsorbate"]
    void_fraction.temperature = simulation_config["temperature"]

    with open(output_file) as origin:
        for line in origin:
            if not "Average Widom Rosenbluth-weight:" in line:
                continue
            void_fraction.void_fraction = float(line.split()[4])
        print("\nVOID FRACTION : {}".format(void_fraction.void_fraction))
        if material.parent:
            print("(parent VOID FRACTION : {})".format(material.parent.void_fraction[0].void_fraction))
        print("\n")
    material.void_fraction.append(void_fraction)

def run(material, simulation_config, config):
    """Runs void fraction simulation.

    Args:
        material (Material): material record.

    Returns:
        results (dict): void fraction simulation results.

    """
    output_dir = "output_{}_{}".format(material.uuid, uuid4())
    print("Output directory : {}".format(output_dir))
    os.makedirs(output_dir, exist_ok=True)

    write_output_files(material, simulation_config, output_dir)

    # Run simulations
    print("Date             : {}".format(datetime.now().date().isoformat()))
    print("Time             : {}".format(datetime.now().time().isoformat()))
    print("Simulation type  : {}".format(simulation_config["type"]))
    print("Probe            : {}".format(simulation_config["adsorbate"]))
    print("Temperature      : {}".format(simulation_config["temperature"]))

    # while not Path(output_file).exists():
    process = subprocess.run(["simulate", "-i", "./void_fraction.input"], check=True, cwd=output_dir)

    data_files = glob(os.path.join(output_dir, "Output", "System_0", "*.data"))
    if len(data_files) != 1:
        raise Exception("ERROR: There should only be one data file in the output directory for %s. Check code!" % output_dir)
    output_file = data_files[0]

    # Parse output
    parse_output(output_file, material, simulation_config)

    # run geometric void fraction
    atoms = [(a.x, a.y, a.z, a.lennard_jones.sigma) for a in material.structure.atom_sites]
    box = (material.structure.a, material.structure.b, material.structure.c)
    material.void_fraction[-1].void_fraction_geo = calculate_void_fraction(atoms, box)
    print("GEOMETRIC void fraction: %f" % material.void_fraction[-1].void_fraction_geo)
    # run zeo void fraction here

    if not config['keep_configs']:
        shutil.rmtree(output_dir, ignore_errors=True)
    sys.stdout.flush()
