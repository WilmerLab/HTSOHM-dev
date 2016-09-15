from time import sleep
import os

import yaml
from sqlalchemy import func
import sjs

sjs.load(os.path.join("settings","sjs.yaml"))
queue = sjs.get_job_queue()

from htsohm.utilities import load_input, write_run_parameters_file
from htsohm.utilities import read_run_parameters_file, evaluate_convergence
from htsohm.utilities import save_convergence
from htsohm.htsohm import seed_generation, queue_all_materials, queue_create_next_generation
from htsohm.htsohm import update_strength_array
from htsohm.runDB_declarative import Material, session

def start_run(input_file):
    run_parameters = load_input(input_file)
    run_id = write_run_parameters_file(run_parameters)['run-id']
    return run_id

def generation_write_complete(run_id, generation):
    materials_per_generation = read_run_parameters_file(run_id)['children-per-generation']
    materials_successfully_written =  session \
        .query(func.count(Material.id)) \
        .filter(
            run_id == run_id, Material.generation == generation,
            Material.write_check == 'done'
        ) \
        .all()[0][0]
    return materials_successfully_written >= materials_per_generation

def manage_run(run_id, generation):
    config = read_run_parameters_file(run_id)
    if generation > config['maximum-number-of-generations']:
        print("Max generations exceeded; terminating run.")
        final_convergence = evaluate_convergence(run_id)
        save_convergence(run_id, generation, final_convergence)
        return -1 # -1 means we're done
    elif generation == 0:
        seed_generation(run_id, config['children-per-generation'],
            config['number-of-atom-types'])
        queue_all_materials(run_id, generation, queue)
        generation += 1
    elif generation >= 1:
        if not generation_write_complete(run_id, generation):
            convergence = evaluate_convergence(run_id)
            save_convergence(run_id, generation - 1, convergence)
            if convergence <= config['convergence-cutoff-criteria']:
                print('Desired convergence attained; terminating run.')
                return -1
            update_strength_array(run_id, generation)
            queue_create_next_generation(run_id, generation, queue)
        else:
            queue_all_materials(run_id, generation, queue)
            generation += 1
    return generation
