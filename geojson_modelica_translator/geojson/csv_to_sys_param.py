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

import json
from copy import deepcopy
from pathlib import Path

import pandas as pd


class CSVToSysParam(object):
    """
    Parser for URBANopt output to write a system_parameters file
    """

    def __init__(self, scenario_dir=None, feature_file=None):
        if Path(scenario_dir).exists():
            self.scenario_dir = scenario_dir
        else:
            raise Exception(f"Unable to find your scenario. The path you provided was: {scenario_dir}")

        if Path(feature_file).exists():
            self.feature_file = feature_file
        else:
            raise Exception(f"Unable to find your feature file. The path you provided was: {feature_file}")

        self.sys_param_template = Path(__file__).parent.parent.parent / 'tests' / 'geojson' / 'data' / 'time_series_template.json'

        self.measure_list = []

    def _parse_items(self, measure_folder: Path) -> None:
        """
        Go through each folder (OpenStudio measure) in a feature and pull out the mass-flow-rate data file & modelica loads file
        """
        if str(measure_folder).endswith('_export_time_series_modelica'):
            self.measure_list.append(Path(measure_folder) / "building_loads.csv")
        elif str(measure_folder).endswith('_export_modelica_loads'):
            self.measure_list.append(Path(measure_folder) / "modelica.mos")

    def _parse_feature(self, feature: Path) -> None:
        """
        Go through each feature directory in UO SDK output
        """
        for item in feature.iterdir():
            if item.is_dir():
                self._parse_items(item)

    def csv_to_sys_param(self, sys_param_filename, overwrite=True):
        if Path(sys_param_filename).exists() and not overwrite:
            raise Exception(f"Output file already exists and overwrite is False: {sys_param_filename}")

        # TODO: move all these methods inside the SystemParameters class
        # sys_param = SystemParameters(sys_param_filename, template)
        # sys_param.populate_filenames(geojson)

        # Parse the sys_param template
        with open(self.sys_param_template) as template_file:
            param_template = json.load(template_file)

        for dir in self.scenario_dir.iterdir():
            if dir.is_dir():
                self._parse_feature(dir)

        # Parse the FeatureFile
        building_ids = []
        with open(self.feature_file) as json_file:
            data = json.load(json_file)
            for feature in data['features']:
                if not feature['properties']['type'] == 'Site Origin':
                    building_ids.append(feature['properties']['id'])

        # Make sys_param template entries for each feature_id
        building_list = []
        for building in building_ids:
            feature_info = deepcopy(param_template['buildings']['custom'][0])
            feature_info['geojson_id'] = building
            building_list.append(feature_info)

        # Grab the modelica file for the each Feature, and add it to the appropriate building dict
        district_nominal_mfrt = 0
        for building in building_list:
            building_nominal_mfrt = 0
            for measure_file_path in self.measure_list:
                feature_name, measure_load_name = str(measure_file_path).split('/')[-3:-1]
                if feature_name != building['geojson_id']:
                    continue
                if (measure_file_path.suffix == '.mos'):
                    building['load_model_parameters']['time_series']['filepath'] = str(measure_file_path)
                if (measure_file_path.suffix == '.csv') and ('_export_time_series_modelica' in str(measure_load_name)):
                    mfrt_df = pd.read_csv(measure_file_path)
                    building_nominal_mfrt = mfrt_df['massFlowRateHeating'].max()
                    building['load_model_parameters']['time_series']['nominal_flow_building'] = float(building_nominal_mfrt)
                district_nominal_mfrt += building_nominal_mfrt

        # Remove buildings that don't have successful simulations, with modelica outputs
        building_list = [x for x in building_list if x['load_model_parameters']['time_series']['filepath'] is not None]
        if len(building_list) == 0:
            raise Exception("No Modelica files found. The UO SDK simulations may not have been successful")

        # TODO: Thermal zone names - useful for Spawn in the future in separate method
        # input_loads_columns = list(self.input_loads_file.columns)
        # thermal_zone_names = []
        # for column_header in input_loads_columns:
        #     if 'Zone' in column_header:
        #         thermal_zone_names.append(column_header.split('_')[-1])
        # thermal_zone_names = list((set(thermal_zone_names)))

        param_template['buildings']['custom'] = building_list
        param_template['buildings']['default']['ets_model_parameters']['indirect']['nominal_flow_district'] = district_nominal_mfrt

        with open(sys_param_filename, 'w') as outfile:
            json.dump(param_template, outfile, indent=2)
