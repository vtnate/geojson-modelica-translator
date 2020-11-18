"""
****************************************************************************************************
:copyright (c) 2019-2020 URBANopt, Alliance for Sustainable Energy, LLC, and other contributors.

All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted
provided that the following conditions are met:

Redistributions of source code must retain the above copyright notice, this list of conditions
and the following disclaimer.

Redistributions in binary form must reproduce the above copyright notice, this list of conditions
and the following disclaimer in the documentation and/or other materials provided with the
distribution.

Neither the name of the copyright holder nor the names of its contributors may be used to endorse
or promote products derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR
IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND
FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER
IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT
OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
****************************************************************************************************
"""
# !/usr/bin/env python
# coding: utf-8

from pathlib import Path

import pandas as pd


class CSVModelica(object):

    def __init__(self, input_csv_file_path):
        """
        Convert a CSV file into the format required by Modelica. This is specific to the Mass Flow Rate file only
        and requires the file format to contain the following headers in this order.

        0: Date/Time, string, date time. This column isn't used and will be removed upon writing out.
        1: THWR, double, Temperature hot water return, degC
        2: THWSET, double, Temperature hot water setpoint, degC
        3: TChWR, double, Temperature chilled water return, degC
        4: TChWSET, double, Temperature chilled water setpoint, degC
        5: massFlowRateHeating, double, heating water mass flow rate, must be named massFlowRateHeating, kg/s
        6: massFlowRateCooling, double, cooling water mass flow rate, must be named massFlowRateCooling, kg/s


        :param input_csv_file_path: string, path to file to convert.
        """

        if not Path(input_csv_file_path).exists():
            raise Exception(f"Unable to convert CSV file because this path does not exist: {input_csv_file_path}")

        # read the data set
        columns_to_use = [
            'SecondsFromStart',
            'heatingReturnTemperature[C]',
            'heatingSupplyTemperature[C]',
            'massFlowRateHeating',
            'ChilledWaterReturnTemperature[C]',
            'ChilledWaterSupplyTemperature[C]',
            'massFlowRateCooling']
        try:
            self.timeseries_output = pd.read_csv(input_csv_file_path, usecols=columns_to_use).round(2)
        except ValueError as ve:
            #     ValueError if column header is misspelled or missing
            raise SystemExit(ve)

        # If time doesn't start at zero, copy the first line since Dymola wants to have time start at zero.
        if (self.timeseries_output.loc[0][0] != 0):
            self.timeseries_15min = self.timeseries_output.loc[[0], :]
        #     sort_index() puts the copied row at the top, as it also has index 0
        #     reset_index() makes the index unique again, while keeping the duplicated row at the top
            self.timeseries_output = pd.concat([self.timeseries_output,
                                                self.timeseries_15min]).sort_index().reset_index(drop=True)

        # Extract the nominal flow rates from the file
        self.nominal_heating_mass_flow_rate = pd.DataFrame(
            {'#heating': ['#Nominal heating water mass flow rate'],
             '#value': [self.timeseries_output['massFlowRateHeating'].max()],
             '#units': ['kg/s']},
            columns=['#heating', '#value', '#units']
        )
        self.nominal_cooling_mass_flow_rate = pd.DataFrame(
            {'#cooling': ['#Nominal chilled water mass flow rate'],
             '#value': [self.timeseries_output['massFlowRateCooling'].max()],
             '#units': ['kg/s']},
            columns=['#cooling', '#value', '#units']
        )

    def timeseries_to_modelica_data(
            self,
            output_modelica_file_name,
            energyplus_timestep_minutes=15,
            data_type='double',
            overwrite=True):
        """
        Convert the loaded data to the format needed for Modelica by adding in the nominal heating water mass flow
        rate and the nominal cooling water mass flow rate into the header.

        :param output_modelica_file_name: string, The name of the outputfile. The extension is automatically added.
        :param energyplus_timestep_minutes: int, EnergyPlus timestep (time between each reading), defaults to 15
        :param data_type: string, data type being converted, defaults to double
        :param overwrite: boolean, if the resulting file exists, then overwrite, defaults to True.
        :return:
        """
        # evaluate dimensions of the matrix
        size = self.timeseries_output.shape
        print(size)
        print(self.timeseries_output.index)
        # modify the index for modelica mos
        self.timeseries_output.index = self.timeseries_output.index * energyplus_timestep_minutes
        self.timeseries_output.index.name = '#time'

        # Remove the first column, which is the date/time (regardless of the name)
        self.timeseries_output.drop(self.timeseries_output.columns[0], axis=1, inplace=True)
        # write to csv for modelica
        output_modelica_file_name_full = f'{output_modelica_file_name}.csv'
        if Path(output_modelica_file_name_full).exists() and not overwrite:
            raise Exception(f"Output file already exists and overwrite is False: {output_modelica_file_name}")

        print(output_modelica_file_name)
        print(os.path.basename(output_modelica_file_name))
        with open(output_modelica_file_name_full, 'w') as f:
            line1 = '#1'
            line2 = f"{data_type} {Path(output_modelica_file_name).stem}({size[0]}, {size[1]})"
            line3 = '#Nominal heating water mass flow rate=' + str(self.nominal_heating_mass_flow_rate.loc[0, '#value'])
            line4 = '#Nominal chilled water mass flow rate=' + str(self.nominal_cooling_mass_flow_rate.loc[0, '#value'])
            f.write('{}\n' '{}\n' '{}\n' '{}\n'.format(line1, line2, line3, line4))
            self.timeseries_output.to_csv(f, header=True)
