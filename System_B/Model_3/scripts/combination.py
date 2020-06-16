import os

import matplotlib.pyplot as plt
import pandas as pd

from helper import get_experiment_dirs, get_scenario_assumptions


def add_index(x, name, value):
    x[name] = value
    x.set_index(name, append=True, inplace=True)
    return x


def get_scenario_paths(scenario_assumptions):
    scenario_paths = {}

    for scenario in scenario_assumptions['name']:
        path = get_experiment_dirs(scenario)['postprocessed']

        scenario_paths.update({scenario: path})

    return scenario_paths


def get_scenario_dfs(scenario_paths, file_name):
    scenario_df = {}

    for scenario, path in scenario_paths.items():
        file_path = os.path.join(path, file_name)

        df = pd.read_csv(file_path)

        scenario_df.update({scenario: df})

    return scenario_df


def combine_scalars(scenario_dfs):
    for scenario, df in scenario_dfs.items():
        df.insert(0, 'scenario', scenario)

    all_scalars = pd.concat(scenario_dfs.values(), 0)

    all_scalars.set_index(
        ['scenario', 'name', 'type', 'carrier', 'tech', 'var_name'],
        inplace=True
    )

    return all_scalars


def plot_stacked_bar(df, slicing, scenario_order, title=None):
    select = df.loc[slicing, :]

    select = select.unstack(level=[1,2,3,4,5])

    select = select.loc[scenario_order]

    fig, ax = plt.subplots()
    select.plot.bar(ax=ax, stacked=True)
    ax.set_title(title)
    ax.legend(loc='center left', bbox_to_anchor=(1.0, 0.5))
    plt.tight_layout()
    plt.show()


def main(scenario_assumptions):
    print("Combining scenario results")

    combined_results_dir = get_experiment_dirs('all_scenarios')['postprocessed']

    scenario_paths = get_scenario_paths(scenario_assumptions)

    scenario_dfs = get_scenario_dfs(scenario_paths, 'scalars.csv')

    all_scalars = combine_scalars(scenario_dfs)

    file_path = os.path.join(combined_results_dir, 'scalars.csv')
    all_scalars.to_csv(file_path)
    print(f"Saved scenario results to {file_path}")

    all_scalars.drop('heat-distribution', level='name', inplace=True)
    all_scalars.drop('heat-demand', level='name', inplace=True)

    # define the order of scenarios
    scenario_order = [
        'status_quo',
        'flexfriendly',
        'flexfriendly_taxlevies=80',
        'flexfriendly_taxlevies=70',
        'flexfriendly_taxlevies=60',
    ]

    idx = pd.IndexSlice
    slicing = idx[scenario_paths.keys(), :, :, 'heat', :, ['capacity', 'invest']]
    plot_stacked_bar(all_scalars, slicing, scenario_order, 'Existing and newly built capacity')

    slicing = idx[scenario_paths.keys(), :, :, :, :, 'yearly_heat']
    plot_stacked_bar(all_scalars, slicing, scenario_order, 'Yearly heat')

    slicing = idx[scenario_paths.keys(), :, :, 'heat', :, ['capacity_cost', 'carrier_cost']]
    plot_stacked_bar(all_scalars, slicing, scenario_order, 'Costs')


if __name__ == '__main__':
    scenario_assumptions = get_scenario_assumptions()
    main(scenario_assumptions)
