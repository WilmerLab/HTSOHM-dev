
from datetime import datetime
from glob import glob
import math
from multiprocessing import Pool
import os
import random
import shutil
import sys

import numpy as np
from sqlalchemy.orm import joinedload

from htsohm import generator, load_config_file, db
from htsohm.db import Material, VoidFraction
from htsohm.simulation.run_all import run_all_simulations
from htsohm.figures import delaunay_figure
import htsohm.select.triangulation as selector_tri
import htsohm.select.density_bin as selector_bin
import htsohm.select.best as selector_best
import htsohm.select.specific as selector_specific
import htsohm.select.neighbor_bin as selector_neighbor_bin

def print_block(string):
    print('{0}\n{1}\n{0}'.format('=' * 80, string))


def calc_bin(value, bound_min, bound_max, bins):
    """Find bin in parameter range.
    Args:
        value (float): some value, the result of a simulation.
        bound_min (float): lower limit, defining the parameter-space.
        bound_max (float): upper limit, defining the parameter-space.
        bins (int): number of bins used to subdivide parameter-space.
    Returns:
        Bin(int) corresponding to the input-value.
    """
    step = (bound_max - bound_min) / bins
    assigned_bin = (value - bound_min) // step
    assigned_bin = min(assigned_bin, bins-1)
    assigned_bin = max(assigned_bin, 0)
    return int(assigned_bin)

def calc_bins(box_r, num_bins, prop1range=(0.0, 1.0), prop2range=(0.0, 1.0)):
    return [(calc_bin(b[0], *prop1range, num_bins), calc_bin(b[1], *prop2range, num_bins)) for b in box_r]

def empty_lists_2d(x,y):
    return [[[] for j in range(x)] for i in range(y)]

def dump_restart(path, box_d, box_r, bin_counts, bin_materials, bins, gen):
    np.savez(path, box_d, box_r, bin_counts, bin_materials, bins, gen)

def load_restart(path):
    if path == "auto":
        restart_files = glob("*.txt.npz")
        restart_files.sort(key=os.path.getmtime)
        if len(restart_files) == 0:
            raise(Exception("ERROR: no txt.npz restart file in the current directory; auto cannot be used."))
        path = restart_files[-1]
        if len(restart_files) > 1:
            print("WARNING: more than one txt.npz file found in this directory. Using last one: %s" % path)

    npzfile = np.load(path, allow_pickle=True)
    return [npzfile[v] if npzfile[v].size != 1 else npzfile[v].item() for v in npzfile.files]

def load_restart_db(gen, num_bins, prop1range, prop2range, session):
    mats = session.query(Material).options(joinedload("void_fraction"), joinedload("gas_loading")) \
                    .filter(Material.generation <= gen).all()
    box_d = np.array([m.id for m in mats])
    box_r = np.array([(m.void_fraction[0].get_void_fraction(), m.gas_loading[0].absolute_volumetric_loading)
                     for m in mats])

    bin_counts = np.zeros((num_bins, num_bins))
    bin_materials = empty_lists_2d(num_bins, num_bins)

    bins = calc_bins(box_r, num_bins, prop1range=prop1range, prop2range=prop2range)
    for i, (bx, by) in enumerate(bins):
        bin_counts[bx,by] += 1
        bin_materials[bx][by].append(i)

    start_gen = gen + 1
    return box_d, box_r, bin_counts, bin_materials, set(bins), start_gen

def check_db_materials_for_restart(expected_num_materials, session, delete_excess=False):
    """Checks for if there are enough or extra materials in the database."""
    extra_materials = session.query(Material).filter(Material.id > expected_num_materials).all()
    if len(extra_materials) > 0:
        print("The database has an extra %d materials in it." % len(extra_materials))
        if (delete_excess):
            print("deleting from materials where id > %d" % expected_num_materials)
            db.delete_extra_materials(expected_num_materials)
        else:
            print("Is this the right database and restart file?")
            sys.exit(1)

    num_materials = session.query(Material).count()
    if num_materials < expected_num_materials:
        print("The database has fewer materials in it than the restart file indicated.")
        print("Is this the right database and restart file?")
        sys.exit(1)

def init_worker(config):
    """initialization function for worker that inits the database and gets a worker-specific
    session."""
    global worker_session
    _, worker_session = db.init_database(config["database_connection_string"])
    return

def simulate_generation_worker(parent_id):
    """gets most of its parameters from the global worker_metadata set in the
    parallel_simulate_generation method."""
    generator, config, gen = worker_metadata

    if parent_id > 0:
        parent = worker_session.query(Material).get(int(parent_id))
        material = generator(parent, config["structure_parameters"])
    else:
        material = generator(config["structure_parameters"])

    run_all_simulations(material, config)
    material.generation = gen
    worker_session.add(material)
    worker_session.commit()

    return (material.id, (material.void_fraction[0].get_void_fraction(),
                          material.gas_loading[0].absolute_volumetric_loading))

def parallel_simulate_generation(generator, parent_ids, config, gen, children_per_generation):
    global worker_metadata
    worker_metadata = (generator, config, gen)

    if parent_ids is None:
        parent_ids = [0] * (children_per_generation) # should only be needed for random!

    with Pool(processes=config['num_processes'], initializer=init_worker, initargs=[config]) as pool:
        results = pool.map(simulate_generation_worker, parent_ids)

    box_d, box_r = zip(*results)
    return (np.array(box_d), np.array(box_r))

def serial_runloop(config_path, restart_generation=0, override_db_errors=False):
    config = load_config_file(config_path)
    os.makedirs(config['output_dir'], exist_ok=True)
    print(config)

    children_per_generation = config['children_per_generation']
    prop1range = config['prop1range']
    prop2range = config['prop2range']
    verbose = config['verbose']
    VoidFraction.set_column_for_void_fraction(config['void_fraction_subtype'])
    num_bins = config['number_of_convergence_bins']
    benchmarks = config['benchmarks']
    next_benchmark = benchmarks.pop(0)
    last_benchmark_reached = False
    load_restart_path = config['load_restart_path']

    dbcs = config["database_connection_string"]
    engine, session = db.init_database(config["database_connection_string"],
                backup=(load_restart_path != False or restart_generation > 0))

    print('{:%Y-%m-%d %H:%M:%S}'.format(datetime.now()))

    if restart_generation > 0:
        print("Restarting from database using generation: %s" % restart_generation)
        box_d, box_r, bin_counts, bin_materials, bins, start_gen = load_restart_db(
            restart_generation, num_bins, prop1range, prop2range, session)

        print("Restarting at generation %d\nThere are currently %d materials" % (start_gen, len(box_r)))
        check_db_materials_for_restart(len(box_r), session, delete_excess=override_db_errors)
    elif load_restart_path:
        print("Restarting from file: %s" % load_restart_path)
        box_d, box_r, bin_counts, bin_materials, bins, start_gen = load_restart(load_restart_path)
        print("Restarting at generation %d\nThere are currently %d materials" % (start_gen, len(box_r)))
        check_db_materials_for_restart(len(box_r), session, delete_excess=override_db_errors)
    else:
        if session.query(Material).count() > 0:
            print("ERROR: cannot have existing materials in the database for a new run")
            sys.exit(1)

        # define variables that are needed for state
        bin_counts = np.zeros((num_bins, num_bins))
        bin_materials = empty_lists_2d(num_bins, num_bins)
        box_d = np.zeros(children_per_generation, dtype=int)
        box_r = -1 * np.ones((children_per_generation, 2))
        bins = set()

        # generate initial generation of random materials
        if config['initial_points_random_seed']:
            print("applying random seed to initial points: %d" % config['initial_points_random_seed'])
            random.seed(config['initial_points_random_seed'])

        box_d, box_r = parallel_simulate_generation(generator.random.new_material, None, config,
                        gen=0, children_per_generation=config['children_per_generation'])

        random.seed() # flush the seed so that only the initial points are set, not generated points

        all_bins = calc_bins(box_r, num_bins, prop1range=prop1range, prop2range=prop2range)
        for i, (bx, by) in enumerate(all_bins):
            bin_counts[bx,by] += 1
            bin_materials[bx][by].append(i)
        bins = set(all_bins)

        output_path = os.path.join(config['output_dir'], "binplot_0.png")
        delaunay_figure(box_r, num_bins, output_path, bins=bin_counts, \
                            title="Starting random materials", show_triangulation=False, show_hull=False, \
                            prop1range=prop1range, prop2range=prop2range)

        start_gen = 1

    for gen in range(start_gen, config['max_generations'] + 1):
        benchmark_just_reached = False
        parents_r = parents_d = []

        # mutate materials and simulate properties
        new_box_d = np.zeros(children_per_generation)
        new_box_r = -1 * np.ones((children_per_generation, 2))

        if config['selector_type'] == 'simplices-or-hull':
            parents_d, parents_r = selector_tri.choose_parents(children_per_generation, box_d, box_r, config['simplices_or_hull'])
        elif config['selector_type'] == 'density-bin':
            parents_d, parents_r = selector_bin.choose_parents(children_per_generation, box_d, box_r, bin_materials)
        elif config['selector_type'] == 'neighbor-bin':
            parents_d, parents_r = selector_neighbor_bin.choose_parents(children_per_generation, box_d, box_r, bin_materials)
        elif config['selector_type'] == 'best':
            parents_d, parents_r = selector_best.choose_parents(children_per_generation, box_d, box_r)
        elif config['selector_type'] == 'specific':
            parents_d, parents_r = selector_specific.choose_parents(children_per_generation, box_d, box_r, config['selector_specific_id'])

        if config['generator_type'] == 'random':
            generator_method = generator.random.new_material
        elif config['generator_type'] == 'mutate':
            generator_method = generator.mutate.mutate_material

        new_box_d, new_box_r = parallel_simulate_generation(generator_method, parents_d, config,
                        gen=gen, children_per_generation=config['children_per_generation'])

        # TODO: bins for methane loading?
        all_bins = calc_bins(new_box_r, num_bins, prop1range=prop1range, prop2range=prop2range)
        for i, (bx, by) in enumerate(all_bins):
            bin_counts[bx,by] += 1
            material_index = i + gen * children_per_generation
            bin_materials[bx][by].append(material_index)
        new_bins = set(all_bins) - bins
        bins = bins.union(new_bins)

        # evaluate algorithm effectiveness
        bin_fraction_explored = len(bins) / num_bins ** 2
        if verbose:
            print_block('GENERATION %s: %5.2f%%' % (gen, bin_fraction_explored * 100))
        while bin_fraction_explored >= next_benchmark:
            benchmark_just_reached = True
            print_block("%s: %5.2f%% exploration accomplished at generation %d" %
                ('{:%Y-%m-%d %H:%M:%S}'.format(datetime.now()), bin_fraction_explored * 100, gen))
            if benchmarks:
                next_benchmark = benchmarks.pop(0)
            else:
                last_benchmark_reached = True

        if config['bin_graph_on'] and (
            (benchmark_just_reached or gen == config['max_generations']) or \
            (config['bin_graph_every'] > 0  and gen % config['bin_graph_every'] == 0)):

            output_path = os.path.join(config['output_dir'], "binplot_%d.png" % gen)
            delaunay_figure(box_r, num_bins, output_path, children=new_box_r, parents=parents_r,
                            bins=bin_counts, new_bins=new_bins,
                            title="Generation %d: %d/%d (+%d) %5.2f%% (+%5.2f %%)" %
                                (gen, len(bins), num_bins ** 2, len(new_bins),
                                100*float(len(bins)) / num_bins ** 2, 100*float(len(new_bins)) / num_bins ** 2 ),
                            patches=None, prop1range=prop1range, prop2range=prop2range, \
                            perturbation_methods=["all"]*children_per_generation, show_triangulation=False, show_hull=False)

        if config['tri_graph_on'] and (
            (benchmark_just_reached or gen == config['max_generations']) or \
            (config['tri_graph_every'] > 0  and gen % config['tri_graph_every'] == 0)):

            output_path = os.path.join(config['output_dir'], "triplot_%d.png" % gen)
            delaunay_figure(box_r, num_bins, output_path, children=new_box_r, parents=parents_r,
                            bins=bin_counts, new_bins=new_bins,
                            title="Generation %d: %d/%d (+%d) %5.2f%% (+%5.2f %%)" %
                                (gen, len(bins), num_bins ** 2, len(new_bins),
                                100*float(len(bins)) / num_bins ** 2, 100*float(len(new_bins)) / num_bins ** 2 ),
                            patches=None, prop1range=prop1range, prop2range=prop2range, \
                            perturbation_methods=["all"]*children_per_generation)

        box_d = np.append(box_d, new_box_d, axis=0)
        box_r = np.append(box_r, new_box_r, axis=0)

        restart_path = os.path.join(config['output_dir'], "restart.txt.npz")
        dump_restart(restart_path, box_d, box_r, bin_counts, bin_materials, bins, gen + 1)
        if benchmark_just_reached or gen == config['max_generations']:
            shutil.move(restart_path, os.path.join(config['output_dir'], "restart%d.txt.npz" % gen))

        if last_benchmark_reached:
            break
