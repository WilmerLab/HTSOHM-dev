from glob import glob
import os
from uuid import uuid4

import click

from htsohm import db, load_config_file, simulation
from htsohm.simulation import void_fraction, gas_loading


@click.command()
@click.argument('config-path', type=click.Path())
@click.argument('material_ids', type=int, nargs=-1)
def output_config_files(config_path, material_ids):
    config = load_config_file(config_path)
    db.init_database(db.get_sqlite_dbcs())
    session = db.get_session()

    from htsohm.db import Material

    for m_id in material_ids:
        m = session.query(Material).get(m_id)

        for i in config["simulations"]:
            simcfg = config["simulations"][i]
            output_dir = "output_%d_%s_%s_%d" % (m.id, m.uuid[0:8], simcfg["type"], i)
            os.makedirs(output_dir, exist_ok=True)

            sim = getattr(simulation, simcfg["type"])
            sim.write_output_files(m, simcfg, output_dir)


if __name__ == '__main__':
    output_config_files()
