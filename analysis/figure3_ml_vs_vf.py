#!/usr/bin/env python3
import click
import matplotlib
import matplotlib.pyplot as plt
from matplotlib import rc
import numpy as np
import pandas as pd

prop1range = [0.0, 1.0]   # VF
prop2range = [0.0, 800.0] # ML
num_ch4_a3 = 2.69015E-05 # from methane-comparison.xlsx
fsl = fs = 8

rc('font',**{'family':'sans-serif','sans-serif':['Helvetica']})
# rc('text', usetex=True)

@click.command()
@click.argument('csv-path', type=click.File())
def figure3_ml_vs_vf(csv_path):
    num_bins = 40

    # figure has to be a little "oversized" so that mpl makes it big enough to fill a 1-column fig.
    fig = plt.figure(figsize=(4.5,4.5))

    # we only want 5 colors for ch4/uc, where each color is centered at 0,1,2,3,4 +-0.5.
    cm = matplotlib.cm.get_cmap("viridis",5)

    points = pd.read_csv(csv_path)
    points['ch4_uc'] = points.absolute_volumetric_loading * (num_ch4_a3 * points.a * points.b * points.c)
    ax = fig.subplots(ncols=1)

    ax.set_xlim(prop1range[0], prop1range[1])
    ax.set_ylim(prop2range[0], prop2range[1])
    ax.set_xticks(prop1range[1] * np.array([0.0, 0.25, 0.5, 0.75, 1.0]))
    ax.set_yticks(prop2range[1] * np.array([0.0, 0.25, 0.5, 0.75, 1.0]))
    ax.set_xticks(prop1range[1] * np.array(range(0,num_bins + 1))/num_bins, minor=True)
    ax.set_yticks(prop2range[1] * np.array(range(0,num_bins + 1))/num_bins, minor=True)

    ax.tick_params(axis='x', which='major', labelsize=fs)
    ax.tick_params(axis='y', which='major', labelsize=fs)

    ax.grid(which='major', axis='both', linestyle='-', color='0.9', zorder=0)

    sc = ax.scatter(points.void_fraction_geo, points.absolute_volumetric_loading, zorder=2,
                alpha=0.6, s=points.a, edgecolors=None, linewidths=0, c=points.ch4_uc,
                cmap=cm, vmin=-0.5, vmax=4.5)

    ax.set_xlabel('Void Fraction', fontsize=fsl)
    ax.set_ylabel('Methane Loading [V/V]', fontsize=fsl)

    # fig.subplots_adjust(wspace=0.05, hspace=0.05)
    output_path = "figure3.png"

    fig.savefig(output_path, dpi=1200, bbox_inches='tight')
    plt.close(fig)

if __name__ == '__main__':
    figure3_ml_vs_vf()
