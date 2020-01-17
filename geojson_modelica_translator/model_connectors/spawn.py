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

import os
import shutil
from jinja2 import FileSystemLoader, Environment

from geojson_modelica_translator.model_connectors.base import Base as model_connector_base
from geojson_modelica_translator.modelica.input_parser import PackageParser
from geojson_modelica_translator.utils import ModelicaPath


class SpawnConnector(model_connector_base):
    def __init__(self, system_parameters):
        super().__init__(system_parameters)

        self.template_env = Environment(
            loader=FileSystemLoader(searchpath=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates'))
        )

    def add_building(self, urbanopt_building, mapper=None):
        """
        Add building to the translator.

        :param urbanopt_building: an urbanopt_building
        """

        # TODO: Need to convert units, these should exist on the urbanopt_building object
        # TODO: Abstract out the GeoJSON functionality
        if mapper is None:
            self.buildings.append({
                "area": urbanopt_building.feature.properties['floor_area'] * 0.092936,  # ft2 -> m2
                "building_id": urbanopt_building.feature.properties['id'],
                "building_type": urbanopt_building.feature.properties['building_type'],
                "floor_height": urbanopt_building.feature.properties['height'] * 0.3048,  # ft -> m
                "num_stories": urbanopt_building.feature.properties['number_of_stories_above_ground'],
                "num_stories_below_grade": urbanopt_building.feature.properties['number_of_stories'] -
                urbanopt_building.feature.properties['number_of_stories_above_ground'],
                "year_built": urbanopt_building.feature.properties['year_built']
            })

    def lookup_building_type(self, building_type):
        """
        This needs to be updated to decide which building to reference if no IDF is included.

        :param building_type:
        :return:
        """
        if 'office' in building_type.lower():
            return 'office'
        else:
            # TODO: define these mappings 'office', 'institute', 'institute4', institute8'
            return 'office'

    def to_modelica(self, project_name, root_building_dir):
        """
        Create spawn models based on the data in the buildings and geojsons

        :param project_name: str, Name of the overall project that will be set in the modelica file
        :param root_building_dir: str, root directory where building model will be exported
        """
        curdir = os.getcwd()
        loads_root_path = os.path.join(root_building_dir, project_name, 'Loads')
        spawn_fmu_template = self.template_env.get_template('spawn_fmu.mot')
        spawn_mos_template = self.template_env.get_template('RunSpawnBuilding.mot')
        building_names = []
        try:
            for building in self.buildings:
                # create each spawn building and save to the correct directory
                print(f"Creating spawn for building: {building['building_id']}")

                # Path for building data
                building_names.append(f"B{building['building_id']}")
                b_modelica_path = ModelicaPath(f"B{building['building_id']}", loads_root_path, True)

                # grab the data from the system_parameter file for this building id
                # TODO: create method in system_parameter class to make this easier and respect the defaults
                idf_filename = self.system_parameters.get_param_by_building_id(
                    building['building_id'], 'load_model_parameters.spawn.idf_filename'
                )
                epw_filename = self.system_parameters.get_param_by_building_id(
                    building['building_id'], 'load_model_parameters.spawn.epw_filename'
                )
                mos_weather_filename = self.system_parameters.get_param_by_building_id(
                    building['building_id'], 'load_model_parameters.spawn.mos_weather_filename'
                )
                thermal_zones = self.system_parameters.get_param_by_building_id(
                    building['building_id'], 'load_model_parameters.spawn.thermal_zone_names'
                )

                # construct th dict to pass into the template
                template_data = {
                    "load_resources_path": b_modelica_path.resources_relative_dir,
                    "idf": {
                        "idf_filename": idf_filename,
                        "filename": os.path.basename(idf_filename),
                        "path": os.path.dirname(idf_filename)
                    },
                    "epw": {
                        "epw_filename": epw_filename,
                        "filename": os.path.basename(epw_filename),
                        "path": os.path.dirname(epw_filename)
                    },
                    "mos_weather": {
                        "mos_weather_filename": mos_weather_filename,
                        "filename": os.path.basename(mos_weather_filename),
                        "path": os.path.dirname(mos_weather_filename)
                    },
                    "thermal_zones": []
                }
                for tz in thermal_zones:
                    # TODO: method for creating nice zone names for modelica
                    template_data['thermal_zones'].append({
                        "modelica_object_name": f"zn{tz}",
                        "spawn_object_name": tz
                    })

                # copy over the resource files for this building
                # TODO: move some of this over to a validation step
                if os.path.exists(template_data['idf']['idf_filename']):
                    shutil.copy(
                        template_data['idf']['idf_filename'],
                        os.path.join(b_modelica_path.resources_dir, template_data['idf']['filename'])
                    )
                else:
                    raise Exception(f"Missing IDF file for Spawn: {template_data['idf']['idf_filename']}")

                if os.path.exists(template_data['epw']['epw_filename']):
                    shutil.copy(
                        template_data['epw']['epw_filename'],
                        os.path.join(b_modelica_path.resources_dir, template_data['epw']['filename'])
                    )
                else:
                    raise Exception(f"Missing EPW file for Spawn: {template_data['epw']['epw_filename']}")

                if os.path.exists(template_data['mos_weather']['mos_weather_filename']):
                    shutil.copy(
                        template_data['mos_weather']['mos_weather_filename'],
                        os.path.join(b_modelica_path.resources_dir, template_data['mos_weather']['filename'])
                    )
                else:
                    raise Exception(
                        f"Missing MOS weather file for Spawn: {template_data['mos_weather']['mos_weather_filename']}")

                file_data = spawn_fmu_template.render(
                    project_name=project_name,
                    model_name=f"B{building['building_id']}",
                    data=template_data,
                )
                with open(os.path.join(os.path.join(b_modelica_path.files_dir, 'building.mo')), 'w') as f:
                    f.write(file_data)

                file_data = spawn_mos_template.render(
                    project_name=project_name,
                    model_name=f"B{building['building_id']}",
                    data=template_data,
                )
                with open(os.path.join(os.path.join(b_modelica_path.resources_dir, 'RunSpawnBuilding.mos')), 'w') as f:
                    f.write(file_data)
        finally:
            os.chdir(curdir)

        # run post process to create the remaining project files for this building
        self.post_process(project_name, root_building_dir, building_names)

    def post_process(self, project_name, root_building_dir, building_names):
        """
        Cleanup the export of Spawn files into a format suitable for the district-based analysis. This includes
        the following:

            * Add a Loads project
            * Add a project level project

        :param project_name: string, name of the project which will be used to set the package.mo file
        :param root_building_dir: string, where the project will be ultimately saved
        :param building_names: list, names of the buildings that need to be cleaned up after export
        :return: None
        """
        loads_root_path = os.path.join(root_building_dir, project_name, 'Loads')
        for b in building_names:
            b_modelica_path = os.path.join(loads_root_path, b)
            new_package = PackageParser.new_from_template(
                b_modelica_path, b, ['building'], within=f"{project_name}.Loads"
            )
            new_package.save()

        # now create the Loads level package. This (for now) will create the package without considering any existing
        # files in the Loads directory.
        package = PackageParser.new_from_template(
            loads_root_path, 'Loads', building_names, within=f'{project_name}'
        )
        package.save()

        # now create the Package level package. This really needs to happen at the GeoJSON to modelica stage, but
        # do it here for now for testing.
        pp = PackageParser.new_from_template(os.path.join(root_building_dir, project_name), project_name, ['Loads'])
        pp.save()
