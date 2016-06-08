import os
import shutil
import yaml

import numpy as np
from random import random, choice, uniform

from htsohm import binning as bng
from htsohm import simulate as sim
from htsohm.runDB_declarative import session, RunData
from htsohm import utilities as utl

def create_strength_array(run_id):
    """Create 3-dimensional array of strength parameters.
    The method divides the 3-dimensional materials parameter space into congruent bins. Each bin
    has its own mutation strength, which is automatically increased or decreased depending upon
    the distribution of children whose parent belong to that bin. This function initializes a
    3-dimensional strength-parameter bin with the initial mutation strength chosen for the run.
    """
    wd = os.environ['HTSOHM_DIR']
    config_file = os.path.join(wd, 'config', run_id + '.yaml')
    with open(config_file) as yaml_file:
        config = yaml.load(yaml_file)
    bins               = config["number-of-bins"]
    initial_strength   = config["initial-mutation-strength"]
    strength_array = initial_strength * np.ones([bins, bins, bins])
    filename = os.path.join(wd, 'config', run_id)
    np.save(strength_array, filename)

def recalculate_strength_array(run_id, generation):
    """Rewrite 3-dimensional array of stregnth parameters.
    In the event that a particular bin contains parents whose children exhibit radically
    divergent properties, the strength paramter for the bin is modified. In order to deftermine
    which bins to adjust, the script refers to the distribution of children in the previous
    generation which share a common parent. The criteria follows:
     ________________________________________________________________
     - if none of the children share  |  decrease strength parameter
       the parent's bin               |  by 50 %
     - if all other child-bin-counts  |  
       are at least 10% greater than  |
       the parent-bin-count           |
     _________________________________|_____________________________
     - if the parent-bin-count is at  |  increase strength parameter
       least 3 times greater than     |  by 50 %
       all other child-bin-counts     |
     _________________________________|_____________________________
    """
    s = session
    db = RunData
    
    parent_list = []
    children = s.query(db).filter(db.run_id == run_id, db.generation == generation)
    for item in children:
        p = s.query(db).get(item.parent_id)
        parent = {
            "id"  : item.parent_id,
            "bin" : [p.methane_loading_bin, p.surface_area_bin, p.void_fraction_bin]}
        parent_list.append(parent)

    wd = os.environ['HTSOHM_DIR']
    strength_array_file = os.path.join(wd, 'config', run_id + '.npy')
    strength_array = np.load(strength_array_file)

    for parent in parent_list:
        parent_id    = parent["id"]
        parent_bin   = parent["bin"]
        child_bins   = []
        child_counts = []
        children = s.query(db).filter(db.run_id == run_id, db.generation == generation - 1,
            db.parent_id == parent_id).all()
        for child in children:
            child_bin = [child.methane_loading_bin, child.surface_area_bin, child.void_fraction_bin]
            bin_count = s.query(db).filter(db.run_id == run_id,
                db.generation == generation - 1, db.parent_id == parent_id,
                db.methane_load_bin == child[0], db.surface_area_bin == child[1],
                db.void_fraction_bin == child[2]).count()
            if child_bin not in child_bins:
                child_bins.append(child_bin)
                child.counts.append(bin_count)
        if parent_bin not in child_bins:
            strength_array[parent_bin] = 0.5 * strength_array[parent_bin]
        elif parent_bin in child_bins:
            parent_bin_count = child_counts[child_bins.index(parent_bin)]
            del child_counts[child_bins.index(parent_bin)]
            if parent_bin_count < 1.1 * min(child_counts):
                strength_array[parent_bin] = 0.5 * strength_array[parent_bin]
            if parent_bin_count >= 3 * min(child_counts):
                strength_array[parent_bin] = 1.5 * strength_array[parent_bin]

    os.remove(strength_array_file)                   # remove old file
    np.save(strength_array_file, strength_array)     # write new file

def closest_distance(x, y):
    """Find the `closest` distance over a periodic boundary.
    """
    a = 1 - y + x
    b = abs(y - x)
    c = 1 - x + y
    return min(a, b, c)

def random_position(x_o, x_r, strength):
    """Given two values, return some random point between them.
    """
    dx = closest_distance(x_o, x_r)
    if (x_o > x_r
            and (x_o - x_r) > 0.5):
        xfrac = round((x_o + strength * dx) % 1., 4)
    if (x_o < x_r
            and (x_r - x_o) > 0.5):
        xfrac = round((x_o - strength * dx) % 1., 4)
    if (x_o >= x_r
            and (x_o - x_r) < 0.5):
        xfrac = round(x_o - strength * dx, 4)
    if (x_o < x_r
            and (x_r - x_o) < 0.5):
        xfrac = round(x_o + strength * dx, 4)
    return xfrac

def write_mutant_definition_files(run_id, generation):
    """Mutate a parent-material's definition files to create new, child-material.
    At this point, a generation of materials has been initialized with parent-material IDs (primary
    keys). This function loads the necessary parameters from the selected parent's definition
    files, perturbs all of these values, and then writes them to new definition-files, creating
    a new material. The degree to which each value is perturbed is controlled by the mutation-
    strength-parameter.""" 
    print( "\nCreating generation :\t%s" % (generation) )
    md = os.environ['MAT_DIR']
    fd = os.environ['FF_DIR']
    wd = os.environ['HTSOHM_DIR']
    strength_array_file = os.path.join(wd, 'config', run_id + '.npy')
    strength_array = np.load(strength_array_file)
    children = session.query(RunData).filter(RunData.run_id == run_id,
        RunData.generation == generation).all()
    materials = []
    for child in children:
        child_id = child.id
        print("CHILD\t%s\n" % (child_id))
        ########################################################################
        # write force_field.def
        child_forcefield_directory = os.path.join(fd, run_id + '-' + str(child_id))
        os.mkdir(child_forcefield_directory)
        force_field_file = os.path.join(child_forcefield_directory, 'force_field.def')
        utl.write_force_field(force_field_file)                        # WRITE FORCE_FIELD.DEF

        ########################################################################
        # copy pseudo_atoms.def
        parent_id = str(child.parent_id)
        print("PARENT\t%s\n" % (parent_id))
        parent_forcefield_directory = os.path.join(fd, run_id + '-' + parent_id)
        parent_pseudo_file = os.path.join(parent_forcefield_directory, 'pseudo_atoms.def')
        shutil.copy(parent_pseudo_file, child_forcefield_directory)    # COPY PSEUDO_ATOMS.DEF

        ########################################################################
        # get mutation strength parameter
        parent = session.query(RunData).get(parent_id)
        parent_bin = [parent.methane_loading_bin, parent.surface_area_bin, parent.void_fraction_bin]
        mutation_strength = strength_array[parent_bin]                 # GET BIN-STRENGTH PARAMETER

        ########################################################################
        # load boundaries from config-file
        wd = os.environ['HTSOHM_DIR']
        config_file = os.path.join(wd, 'config', run_id + '.yaml')
        with open(config_file) as yaml_file:
            config = yaml.load(yaml_file)
        lattice_limits          = config["lattice-constant-limits"]
        number_density_limits   = config["number-density-limits"]
        epsilon_limits          = config["epsilon-limits"]
        sigma_limits            = config["sigma-limits"]
        
        ########################################################################
        # perturb LJ-parameters, write force_field_mixing_rules.def
        p_mix = os.path.join(fd, run_id + '-' + parent_id, 'force_field_mixing_rules.def')
        n1, n2, old_epsilons, old_sigmas = np.genfromtxt(p_mix, unpack=True, skip_header=7,
            skip_footer=9)
        chemical_ids = np.genfromtxt(p_mix, unpack=True, skip_header=7, skip_footer=9,
            usecols=0, dtype=str)
        atom_types = []
        for i in range(len(chemical_ids)):
            epsilon = round( old_epsilons[i] + mutation_strength * (uniform(**epsilon_limits) - 
                old_epsilons[i]), 4)
            sigma = round( old_sigmas[i] + mutation_strength * (uniform(**sigma_limits) - 
                old_sigmas[i]), 4)
            atom_type = {
                "chemical-id" : chemical_ids[i],
                "charge"      : 0.,
                "epsilon"     : epsilon,
                "sigma"       : sigma}
            atom_types.append(atom_type)

        mix_file = os.path.join(child_forcefield_directory, 'force_field_mixing_rules.def')
        utl.write_mixing_rules(mix_file, atom_types)

        ########################################################################
        # load values from parent cif-file
        p_cif = os.path.join(md, run_id + '-' + parent_id + '.cif')
        n1, n2, old_x, old_y, old_z = np.genfromtxt(p_cif, unpack=True, skip_header=16)
        old_atom_types = np.genfromtxt(p_cif, usecols=0, dtype=str, skip_header=16)
        old_abc = np.genfromtxt(p_cif, unpack=True, skip_header=4, skip_footer=len(old_x) + 9,
            usecols = 1)
        ########################################################################
        # calculate new lattice constants
        old_a = old_abc[0]
        old_b = old_abc[1]
        old_c = old_abc[2]
        random_a = round(uniform(*lattice_limits), 4)
        random_b = round(uniform(*lattice_limits), 4)
        random_c = round(uniform(*lattice_limits), 4)
        a = round(old_a + mutation_strength * (random_a - old_a), 4) 
        b = round(old_b + mutation_strength * (random_b - old_b), 4)
        c = round(old_c + mutation_strength * (random_c - old_c), 4)
        lattice_constants = [a, b, c]
        ########################################################################
        # calulate new number density, number of atoms
        old_ND = len(old_x) / (old_a * old_b * old_c)
        random_ND = round(uniform(*number_density_limits), 4)
        number_density = old_ND + mutation_strength * (random_ND - old_ND)
        number_of_atoms = int(number_density * a * b * c)
        ########################################################################
        # remove excess atom-sites, if any
        if number_of_atoms < len(old_x):
            difference = len(old_x) - number_of_atoms
            del old_x[-difference:]
            del old_y[-difference:]
            del old_z[-difference:]
        ########################################################################
        # perturb atom-site positions
        atom_sites = []
        for i in range(len(old_x)):
            chemical_id = old_atom_types[i]
            x = random_position(old_x[i], random(), mutation_strength)
            y = random_position(old_y[i], random(), mutation_strength)
            z = random_position(old_z[i], random(), mutation_strength)
            atom_site = {
                "chemical-id" : chemical_id,
                "x-frac"      : x,
                "y-frac"      : y,
                "z-frac"      : z}
            atom_sites.append(atom_site)
        ########################################################################
        # add atom-sites, if needed
        if number_of_atoms > len(atom_sites):
            for new_sites in range(number_of_atoms - len(atom_sites)):
                atom_site = {
                    "chemical-id" : choice(chemical_ids),
                    "x-frac"      : round(random(), 4),
                    "y-frac"      : round(random(), 4),
                    "z-frac"      : round(random(), 4)}
                atom_sites.append(atom_site)

        cif_file = os.path.join(md, run_id + '-' + child_id + '.cif')
        utl.write_cif_file(cif_file, lattice_constants, atom_sites)
        material = [child_id, atom_types, atom_sites]
        materials.append(material)
    print( "...done!\n" )
