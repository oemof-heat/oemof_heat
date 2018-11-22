# -*- coding: utf-8 -*-
"""
Created on Mon Apr 30 15:21:48 2018

@author: Franziska Pleissner

System C: concrete example: Model of cooling process with a solar collector


             input/output     gas   thermal  electr.  cool   waste   ambient(/ground)

naturalgas         |---------->|       |       |       |       |
                   |           |       |       |       |       |
grid_el            |-------------------------->|       |       |
                   |           |       |       |       |       |
pv                 |-------------------------->|       |       |
                   |           |       |       |       |       |
collector          |------------------>|       |       |       |
                   |           |       |       |       |       |
boiler             |           |------>|       |       |       |
                   |           |       |       |       |       |
                   |<------------------|       |       |       |
absorption_chiller |---------------------------------->|       |
                   |------------------------------------------>|
                   |           |       |       |       |       |
cooling_tower      |<------------------------------------------|
                   |<--------------------------|       |       |       |
                   |-------------------------------------------------->|
                   |           |       |       |       |       |
aquifer            |<------------------------------------------|
                   |<--------------------------|       |       |       |
                   |-------------------------------------------------->|
                   |           |       |       |       |       |
storage_thermal    |------------------>|       |       |       |
                   |<------------------|       |       |       |
                   |           |       |       |       |       |
storage_electricity|-------------------------->|       |       |
                   |<--------------------------|       |       |
                   |           |       |       |       |       |
storage_cool       |---------------------------------->|       |
                   |<----------------------------------|       |
                   |           |       |       |       |       |
demand             |<----------------------------------|       |


"""

############
# Preamble #
############

# Import packages
from oemof.tools import logger, helpers
import oemof.solph as solph
import oemof.outputlib as outputlib

import time
import logging
import os
import pandas as pd

# import oemof plots
try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None

solver = 'cbc'
debug = False  # Set number_of_timesteps to 2 to get a readable lp-file.  # should be in config-file (doesn't exist yet)
number_of_time_steps = 200  # should be in the config-file (doesn't exist yet)
solver_verbose = False  # show/hide solver output

# initiate the logger
logger.define_logging(logfile='System_Oman.log',
                      screen_level=logging.INFO,
                      file_level=logging.DEBUG)

logging.info('Initialize the energy system')

date_time_index = pd.date_range('1/1/2017', periods=(2 if debug is True else number_of_time_steps), freq='H')

# Read data

abs_path = os.path.dirname(os.path.abspath(os.path.join(__file__, '..')))
results_dir = abs_path + '/model_runs/'
data_dir = abs_path + '/data/'

if not os.path.exists(results_dir):
    print('yes')
    os.makedirs(results_dir + '/optimisation_results')

# logger.define_logging(logpath=results_dir + '/optimisation_results')

# Read parameter values from parameter file
filename_param = data_dir + 'data_public/parameters_experiment_2.csv'
param_df = pd.read_csv(filename_param, index_col=1, sep=';')  # uses second column of csv-file for indexing
param_value = param_df['value']

# Import  PV and demand data
data = pd.read_csv((data_dir + 'data_confidential/Oman3.csv'), sep=';')


# Initialise the energysystem
energysystem = solph.EnergySystem(timeindex=date_time_index)

#######################
# Build up the system #
#######################

# Busses

bth = solph.Bus(label='thermal')
bco = solph.Bus(label="cool")
bwh = solph.Bus(label="waste")
bel = solph.Bus(label="electricity")
bga = solph.Bus(label="gas")
bam = solph.Bus(label="ambient")

energysystem.add(bth, bco, bwh, bel, bga, bam)

# Sinks and sources

ambience = solph.Sink(label='ambience', inputs={bam: solph.Flow()})

grid_ga = solph.Source(label='naturalgas', outputs={bga: solph.Flow(variable_costs=param_value['price_gas'])})

grid_el = solph.Source(label='grid_el', outputs={bel: solph.Flow(variable_costs=param_value['price_electr'])})

collector = solph.Source(label='collector', outputs={bth: solph.Flow(
    fixed=True, actual_value=data['solar gain kWprom2'],
    investment=solph.Investment(ep_costs=param_value['invest_costs_collect_output_th']))})  # Has to be developed

pv = solph.Source(label='pv', outputs={bel: solph.Flow(
    fixed=True, actual_value=data['PV Faktor'],
    investment=solph.Investment(ep_costs=param_value['invest_costs_pv_output_th']))})

demand = solph.Sink(label='demand', inputs={bco: solph.Flow(
    fixed=True, actual_value=data['Cooling load kW'], nominal_value=1)})

excess = solph.Sink(label='excess_thermal', inputs={bth: solph.Flow()})

energysystem.add(ambience, grid_el, grid_ga, collector, pv, demand, excess)

# Transformers

if param_value['nominal_value_boiler_output_thermal'] == 0:
    boil = solph.Transformer(
        label='boiler',
        inputs={bga: solph.Flow()},
        outputs={bth: solph.Flow(investment=solph.Investment(ep_costs=param_value['invest_costs_boiler_output_th']))},
        conversion_factors={bth: param_value['conv_factor_boiler_output_thermal']})
else:
    boil = solph.Transformer(
        label='boiler',
        inputs={bga: solph.Flow()},
        outputs={bth: solph.Flow(nominal_value=param_value['nominal_value_boiler_output_thermal'])},
        conversion_factors={bth: param_value['conv_factor_boiler_output_thermal']})

chil = solph.Transformer(
    label='absorption_chiller',
    inputs={bth: solph.Flow()},
    outputs={bco: solph.Flow(investment=solph.Investment(ep_costs=param_value['invest_costs_absorption_output_cool'])),
             bwh: solph.Flow()},
    conversion_factors={bco: param_value['conv_factor_absorption_output_cool'],
                        bwh: param_value['conv_factor_absorption_output_waste']})

aqui = solph.Transformer(
    label='aquifer',
    inputs={bwh: solph.Flow(investment=solph.Investment(ep_costs=param_value['invest_costs_aqui_input_th']),
                            variable_costs=param_value['var_costs_aquifer_input_waste']),
            bel: solph.Flow()},
    outputs={bam: solph.Flow()},
    conversion_factors={bwh: param_value['conv_factor_aquifer_input_waste'],
                        bel: param_value['conv_factor_aquifer_input_el']})

towe = solph.Sink(
    label='cooling_tower',
    inputs={bwh: solph.Flow(investment=solph.Investment(ep_costs=param_value['invest_costs_towe_input_th']),
                            variable_costs=param_value['var_costs_cool_tower_input_waste']),
            bel: solph.Flow()},
    outputs={bam: solph.Flow()},
    conversion_factors={bwh: param_value['conv_factor_tower_input_waste'],
                        bel: param_value['conv_factor_tower_input_el']})

energysystem.add(chil, boil, aqui, towe)

# storages

if param_value['nominal_capacitiy_stor_cool'] == 0:
    stor_co = solph.components.GenericStorage(
        label='storage_cool',
        inputs={bco: solph.Flow()},
        outputs={bco: solph.Flow()},
        capacity_loss=param_value['capac_loss_stor_cool'],
        invest_relation_input_capacity=1 / 6,
        invest_relation_output_capacity=1 / 6,
        inflow_conversion_factor=param_value['conv_factor_stor_cool_input'],
        outflow_conversion_factor=param_value['conv_factor_stor_cool_output'],
        nominal_capacity=param_value['nominal_capacitiy_stor_cool'])
else:
    stor_co = solph.components.GenericStorage(
        label='storage_cool',
        inputs={bco: solph.Flow()},
        outputs={bco: solph.Flow()},
        capacity_loss=param_value['capac_loss_stor_cool'],
        invest_relation_input_capacity=1 / 6,
        invest_relation_output_capacity=1 / 6,
        inflow_conversion_factor=param_value['conv_factor_stor_cool_input'],
        outflow_conversion_factor=param_value['conv_factor_stor_cool_output'],
        investment=solph.Investment(ep_costs=param_value['invest_costs_storage_cool_capacity']))

if param_value['nominal_capacitiy_stor_thermal'] == 0:
    stor_th = solph.components.GenericStorage(
        label='storage_thermal',
        inputs={bth: solph.Flow()},
        outputs={bth: solph.Flow()},
        capacity_loss=param_value['capac_loss_stor_thermal'],
        invest_relation_input_capacity=1 / 6,
        invest_relation_output_capacity=1 / 6,
        inflow_conversion_factor=param_value['conv_factor_stor_thermal_input'],
        outflow_conversion_factor=param_value['conv_factor_stor_thermal_output'],
        nominal_capacity=param_value['nominal_capacitiy_stor_thermal'])
else:
    stor_th = solph.components.GenericStorage(
        label='storage_thermal',
        inputs={bth: solph.Flow()},
        outputs={bth: solph.Flow()},
        capacity_loss=param_value['capac_loss_stor_thermal'],
        invest_relation_input_capacity=1 / 6,
        invest_relation_output_capacity=1 / 6,
        inflow_conversion_factor=param_value['conv_factor_stor_thermal_input'],
        outflow_conversion_factor=param_value['conv_factor_stor_thermal_output'],
        investment=solph.Investment(ep_costs=param_value['invest_costs_storage_thermal_capacity']))

if param_value['nominal_capacitiy_stor_el'] == 0:
    stor_el = solph.components.GenericStorage(
        label='storage_electricity',
        inputs={bel: solph.Flow()},
        outputs={bel: solph.Flow()},
        capacity_loss=param_value['capac_loss_stor_el'],
        invest_relation_input_capacity=1 / 6,
        invest_relation_output_capacity=1 / 6,
        inflow_conversion_factor=param_value['conv_factor_stor_el_input'],
        outflow_conversion_factor=param_value['conv_factor_stor_el_output'],
        nominal_capacity=param_value['nominal_capacitiy_stor_el'])
else:
    stor_el = solph.components.GenericStorage(
        label='storage_electricity',
        inputs={bel: solph.Flow()},
        outputs={bel: solph.Flow()},
        capacity_loss=param_value['capac_loss_stor_el'],
        invest_relation_input_capacity=1 / 6,
        invest_relation_output_capacity=1 / 6,
        inflow_conversion_factor=param_value['conv_factor_stor_el_input'],
        outflow_conversion_factor=param_value['conv_factor_stor_el_output'],
        investment=solph.Investment(ep_costs=param_value['invest_costs_storage_el_capacity']))

energysystem.add(stor_co, stor_th, stor_el)

########################################
# Create a model and solve the problem #
########################################

# Initialise the operational model (create problem) with constrains
model = solph.Model(energysystem)

if debug:
    filename = os.path.join(
        helpers.extend_basic_path('lp_files'), 'app_Oman.lp')
    logging.info('Store lp-file in {0}.'.format(filename))
    model.write(filename, io_options={'symbolic_solver_labels': True})

logging.info('Solve the optimization problem')
model.solve(solver=solver, solve_kwargs={'tee': solver_verbose})

logging.info('Store the energy system with the results.')

energysystem.results['main'] = outputlib.processing.results(model)
energysystem.results['meta'] = outputlib.processing.meta_results(model)
energysystem.results['param'] = outputlib.processing.param_results(model)

timestr = time.strftime("%Y%m%d-%H%M")
energysystem.dump(dpath=(abs_path + '/dumps'),
                  filename="Oman_thermal.oemof")

print('done')
