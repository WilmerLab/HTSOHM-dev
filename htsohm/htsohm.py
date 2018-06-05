import os
import sys
from math import sqrt
from datetime import datetime

from sqlalchemy.sql import func
from sqlalchemy.orm.exc import FlushError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import text
import yaml

import htsohm
from htsohm import config
from htsohm.db import engine, session, Material
from htsohm import pseudomaterial_generator
from htsohm.simulation.run_all import run_all_simulations

def materials_in_generation(run_id, generation):
    """Count number of materials in a generation.

    Args:
        run_id (str): identification string for run.
        generation (int): iteration in overall bin-mutate-simulate rountine.

    Returns:
        Number(int) of materials in a particular generation that are present in
        the database (the final step in bin-mutate-simulate routine).

    """
    return session.query(Material).filter(
        Material.run_id == run_id,
        Material.generation == generation
    ).count()

def last_generation(run_id):
    """Finds latest generation present in database.

    Args:
        run_id (str): identification string for run.

    Returns:
        Last generation(int) to be included in database.

    """
    return session.query(func.max(Material.generation)).filter(
        Material.run_id == run_id,
    )[0][0]

def evaluate_convergence(run_id, generation):
    '''Determines convergence by calculating variance of bin-counts.
    
    Args:
        run_id (str): identification string for run.
        generation (int): iteration in bin-mutate-simulate routine.

    Returns:
        bool: True if variance is less than or equal to cutt-off criteria (so
            method will continue running).
    '''
    simulations = config['simulations']
    query_group = []
    if 'gas_adsorption' in simulations:
        query_group.append( getattr(Material, 'gas_adsorption_bin') )
    if 'surface_area' in simulations:
        query_group.append( getattr(Material, 'surface_area_bin') )
    if 'helium_void_fraction' in simulations:
        query_group.append( getattr(Material, 'void_fraction_bin') )

    bin_counts = session \
        .query(func.count(Material.id)) \
        .filter(
            Material.run_id == run_id, Material.generation < generation,
            Material.generation_index < config['children_per_generation']
        ) \
        .group_by(*query_group).all()
    bin_counts = [i[0] for i in bin_counts]    # convert SQLAlchemy result to list
    variance = sqrt( sum([(i - (sum(bin_counts) / len(bin_counts)))**2 for i in bin_counts]) / len(bin_counts))
    print('\nCONVERGENCE:\t%s\n' % variance)
    sys.stdout.flush()
    return variance <= config['convergence_cutoff_criteria']

def print_block(string):
    print('{0}\n{1}\n{0}'.format('=' * 80, string))

def worker_run_loop(run_id):
    """
    Args:
        run_id (str): identification string for run.

    Writes seed generation and simulates properties, then manages overall
    bin-mutate-simualte routine until convergence cutt-off or maximum
    number of generations is reached.

    """
    print('CONFIG\n{0}'.format(config))

    gen = last_generation(run_id) or 0

    converged = False
    while not converged:
        print_block('GENERATION {}'.format(gen))
        size_of_generation = config['children_per_generation']

        while materials_in_generation(run_id, gen) < size_of_generation:

            material = pseudomaterial_generator.random.new_material(run_id, gen)

            # simulate material properties
            run_all_simulations(material)
            material.ap_unit_cell_volume = float(material.structure.volume)
            material.ap_number_density = float(material.structure.number_density())
            material.ap_average_epsilon = float(material.structure.average_epsilon())
            material.ap_average_sigma = float(material.structure.average_sigma())

            session.add(material)
            session.commit()

            # add material to database, as needed
            material.generation_index = material.calculate_generation_index()
            if material.generation_index < config['children_per_generation']:
                print_block('ADDING MATERIAL {}'.format(material.uuid))
                session.add(material)

            else:
                # delete excess rows
                # session.delete(material)
                pass
            session.commit()
            sys.stdout.flush()
        gen += 1
        converged = evaluate_convergence(run_id, gen)
