from math import isclose
from random import choice, random, uniform

import numpy as np
from scipy.spatial import Delaunay, distance
from sqlalchemy import text
from sqlalchemy.orm.session import make_transient

from htsohm.db import engine, session, Material, Structure, LennardJones, AtomSites
from htsohm.pseudomaterial_generator.utilities import random_number_density

def random_position(x0, x1, strength):
    # get minimum distance between two points of (1) within the box, and (2) across the box boundary
    dx = min(abs(x0 - x1), 1 - abs(x0 - x1))


    if x0 > x1 and (x0 - x1) > 0.5: # then dx will be through boundary, so move right
        x2 = (x0 + strength * dx) % 1.
    if x0 >= x1 and (x0 - x1) < 0.5: # then dx will be in box, so move left
        x2 = x0 - strength * dx
    if x0 < x1 and (x1 - x0) > 0.5: # then dx will be through boundary, so move left
        x2 = (x0 - strength * dx) % 1.
    if x0 < x1 and (x1 - x0) < 0.5: # then dx will be in box, so move right
        x2 = x0 + strength * dx
    return x2

def net_charge(atom_sites):
    return sum([e.q for e in atom_sites])

def clone_parent(parent_id):
    # parent_id = session.query(Material.id).filter(Material.uuid==uuid).one()[0]
    parent = session.query(Material).get(parent_id)
    structure = parent.structure
    atom_sites = parent.structure.atom_sites
    for a in atom_sites:
        session.expunge(a)
        make_transient(a)
        a.id = None
    lennard_jones = parent.structure.lennard_jones
    for l in lennard_jones:
        session.expunge(l)
        make_transient(l)
        l.id = None
    session.expunge(structure)
    make_transient(structure)
    structure.id = None
    session.expunge(parent)
    make_transient(parent)
    parent.id = None
    return parent

def perturb_unweighted(curr_val, max_change, var_limits):
    new_val = curr_val + uniform(-max_change, max_change)
    return min(max(new_val, var_limits[0]), var_limits[1])


def mutate_material(run_id, parent_uuid, config):
    """Create records for pseudomaterial simulation and structure data."

    Args:
        run_id (str): identification string for run.
        number_of_atomtypes (int): number of different chemical species used to
            populate the unit cell.

    Returns:
        material (sqlalchemy.orm.query.Query): database row for storing
            simulation data specific to the material. See
            `htsohm/db/material.py` for more information.

    """
    number_of_atom_types    = config["number_of_atom_types"]
    lattice_limits          = config["lattice_constant_limits"]
    number_density_limits   = config["number_density_limits"]
    epsilon_limits          = config["epsilon_limits"]
    sigma_limits            = config["sigma_limits"]
    max_charge              = config["charge_limit"]
    strength                = config["mutation_strength"]

    ########################################################################
    # get parent structure
    parent = clone_parent(parent_uuid)
    ps = parent.structure

    # create database row
    child = Material(run_id, parent_uuid)
    cs = child.structure

    # TODO: USE NON-WEIGHTED PERTURBATION
    # perturb lattice constants
    cs.a = perturb_unweighted(ps.a, strength * (lattice_limits[1] - lattice_limits[0]), lattice_limits)
    cs.b = perturb_unweighted(ps.b, strength * (lattice_limits[1] - lattice_limits[0]), lattice_limits)
    cs.c = perturb_unweighted(ps.c, strength * (lattice_limits[1] - lattice_limits[0]), lattice_limits)

    # store unit cell volume to row
    child.unit_cell_volume = cs.volume

    # TODO: USE NON-WEIGHTED PERTURBATION
    # perturb lennard-jones parameters
    for at in ps.lennard_jones:
        cs.lennard_jones.append(LennardJones(
            atom_type = at.atom_type,
            sigma = at.sigma + strength * (uniform(*sigma_limits) - at.sigma),
            epsilon = at.epsilon + strength * (uniform(*epsilon_limits) - at.epsilon)))

    # TODO: USE NON-WEIGHTED PERTURBATION
    # perturb number density/ number of atom-sites
    child.number_density = perturb_unweighted(parent.number_density, \
                            (number_density_limits[1] - number_density_limits[0])*strength, \
                            number_density_limits)

    number_of_atoms = max(1, int(child.number_density * child.unit_cell_volume))

    # remove atom-sites, if necessary
    cs.atom_sites = np.random.choice(ps.atom_sites, min(number_of_atoms, len(ps.atom_sites)), replace=False).tolist()
    # remove atom-sites, if necessary
    # adjust charges if atom-sites were removed
    # while not isclose(net_charge(cs.atom_sites), 0., abs_tol=1.0e-6):
    #         # pick an atom-site at random
    #         i = choice(range(len(cs.atom_sites)))
    #         if net_charge(cs.atom_sites) < 0:
    #             dq = float("{0:.6f}".format(min(max_charge - cs.atom_sites[i].q, -net_charge(cs.atom_sites))))
    #             cs.atom_sites[i].q += dq
    #         else:
    #             dq = float("{0:.6f}".format(min(max_charge + cs.atom_sites[i].q, net_charge(cs.atom_sites))))
    #             cs.atom_sites[i].q -= dq

    # NOTE: I _think_ this is ok
    # perturb atom-site positions
    for a in cs.atom_sites:
        a.x = random_position(a.x, random(), strength)
        a.y = random_position(a.y, random(), strength)
        a.x = random_position(a.z, random(), strength)

    # TODO: new points always have ZERO charge?
    # add atom-sites, if necessary
    if number_of_atoms > len(cs.atom_sites):
        for i in range(number_of_atoms - len(cs.atom_sites)):
            cs.atom_sites.append(AtomSites(atom_type="A_{}".format(choice(range(number_of_atom_types))), x=random(), y=random(), z=random(), q=0.))

    # calculate avg. sigma/epsilon values
    sigma_sum, epsilon_sum = 0, 0
    for a in cs.atom_sites:
        index = int(a.atom_type[2:])
        sigma_sum += cs.lennard_jones[index].sigma
        epsilon_sum += cs.lennard_jones[index].epsilon
    child.average_sigma = sigma_sum / number_of_atoms
    child.average_epsilon = epsilon_sum / number_of_atoms

    # TODO: USE NON-WEIGHTED PERTURBATION
    # perturb partial charges
    # for i in range(number_of_atoms):
    #     while True:
    #         try:
    #             random_q = uniform(-max_charge, max_charge)
    #             dq = strength * (random_q - cs.atom_sites[i].q)
    #             j = choice(range(number_of_atoms))
    #             # TODO: what if i == j ?
    #             if abs(cs.atom_sites[i].q + dq) <= max_charge and abs(cs.atom_sites[j].q - dq) <= max_charge:
    #                 cs.atom_sites[i].q += dq
    #                 cs.atom_sites[j].q -= dq
    #                 break
    #         except:
    #             pass


    print("CHILD UUID  :\t{}".format(child.uuid))
    print("lattice constants: (%.2f, %.2f, %.2f) => (%.2f, %.2f, %.2f)" % (ps.a, ps.b, ps.c, cs.a, cs.b, cs.c))
    print("number_density: %.2e => %.2e" % (parent.number_density, child.number_density))
    print("number of atoms: %.2f => %.2f" % (int(parent.number_density * parent.unit_cell_volume), number_of_atoms))
    parent_ljs = ", ".join(["(%.1f, %.1f)" % (ljs.epsilon, ljs.sigma) for ljs in ps.lennard_jones])
    child_ljs = ", ".join(["(%.1f, %.1f)" % (ljs.epsilon, ljs.sigma) for ljs in cs.lennard_jones])
    print("lennard jones: %s => %s" % (parent_ljs, child_ljs))

    print("FRAMEWORK NET CHARGE :\t{}".format(sum([e.q for e in cs.atom_sites])))
    return child
