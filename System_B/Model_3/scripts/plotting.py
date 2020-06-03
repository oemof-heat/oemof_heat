import os

import matplotlib.pyplot as plt
import pandas as pd

from helper import get_experiment_dirs


def bar_plot():
    pass

def plot_capacities(capacities, destination):
    idx = pd.IndexSlice

    cap_heat_dec = capacities.loc[idx[:, 'heat_decentral', :], :]
    cap_heat_cen = capacities.loc[idx[:, 'heat_central', :], :]
    cap_electricty = capacities.loc[idx[:, 'electricity', :], :]

    for cap in [cap_heat_dec, cap_heat_cen, cap_electricty]:
        cap.index = cap.index.droplevel(['to', 'tech', 'carrier'])

    print(cap_heat_dec)
    fig, axs = plt.subplots(2, 1)
    cap_heat_cen.plot.bar(ax=axs[0])
    cap_heat_dec.plot.bar(ax=axs[1])

    plt.tight_layout()

    plt.savefig(destination)


def plot_dispatch(bus, destination):
    start = '2017-02-01'
    end = '2017-03-01'

    bus = bus[start:end]
    demand = bus['heat-demand']
    bus_wo_demand = bus.drop('heat-demand', axis=1)

    fig, ax = plt.subplots(figsize=(12, 5))
    bus_wo_demand.plot.area(ax=ax)
    demand.plot.line(c='r', linewidth=2)
    ax.set_title('Dispatch')
    plt.savefig(destination)


def plot_yearly_production(bus, destination):
    yearly_sum = bus.sum().drop('heat-demand')

    fig, ax = plt.subplots()
    yearly_sum.plot.bar(ax=ax)
    ax.set_title('Yearly production')
    plt.tight_layout()
    plt.savefig(destination)

def main():
    dirs = get_experiment_dirs()

    capacities = pd.read_csv(
        os.path.join(dirs['postprocessed'], 'capacities.csv'),
        index_col=[0,1,2,3,4]
    )

    heat_bus = pd.read_csv(
        os.path.join(dirs['postprocessed'], 'heat_decentral.csv'),
        index_col=0
    )

    plot_capacities(capacities, os.path.join(dirs['plots'], 'capacities.svg'))

    plot_dispatch(heat_bus, os.path.join(dirs['plots'], 'heat_bus.svg'))

    plot_yearly_production(heat_bus, os.path.join(dirs['plots'], 'yearly_heat_production.svg'))


if __name__ == '__main__':
    main()