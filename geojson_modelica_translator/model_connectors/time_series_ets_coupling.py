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

from geojson_modelica_translator.model_connectors.base import \
    Base as model_connector_base
from geojson_modelica_translator.modelica.input_parser import PackageParser
from geojson_modelica_translator.utils import ModelicaPath


class TimeSeriesConnectorETS(model_connector_base):
    def __init__(self, system_parameters):
        super().__init__(system_parameters)

    def to_modelica(self, scaffold):
        """
        Create TimeSeries models based on the data in the buildings and geojsons

        :param scaffold: Scaffold object, Scaffold of the entire directory of the project.
        """
        curdir = os.getcwd()
        timeSeries_ets_coupling_template = self.template_env.get_template("TimeSeriesCouplingETS.mot")
        timeSeries_building_template = self.template_env.get_template("TimeSeriesBuilding.mot")
        cooling_indirect_template = self.template_env.get_template("CoolingIndirect.mot")
        timeSeries_ets_mos_template = self.template_env.get_template("RunTimeSeriesCouplingETS.most")
        building_names = []
        try:
            for building in self.buildings:
                building_names.append(f"B{building['building_id']}")
                b_modelica_path = ModelicaPath(
                    f"B{building['building_id']}", scaffold.loads_path.files_dir, True
                )

                # grab the data from the system_parameter file for this building id
                # TODO: create method in system_parameter class to make this easier and respect the defaults
                time_series_filename = self.system_parameters.get_param_by_building_id(
                    building["building_id"], "load_model_parameters.time_series.filepath"
                )

                template_data = {
                    "load_resources_path": b_modelica_path.resources_relative_dir,
                    "time_series": {
                        "filepath": time_series_filename,
                        "filename": os.path.basename(time_series_filename),
                        "path": os.path.dirname(time_series_filename),
                    },
                    "nominal_values": {
                        "delTDisCoo": self.system_parameters.get_param_by_building_id(
                            building["building_id"], "load_model_parameters.time_series.delTDisCoo"
                        )
                    }
                }

                if os.path.exists(template_data["time_series"]["filepath"]):
                    new_file = os.path.join(b_modelica_path.resources_dir, template_data["time_series"]["filename"])
                    os.makedirs(os.path.dirname(new_file), exist_ok=True)
                    shutil.copy(template_data["time_series"]["filepath"], new_file)
                else:
                    raise Exception(f"Missing MOS file for time series: {template_data['time_series']['filepath']}")

                # write a file name building.mo, CoolingIndirect.mo and TimeSeriesCouplingETS.mo
                # Run the templating
                file_data = timeSeries_building_template.render(
                    project_name=scaffold.project_name,
                    model_name=f"B{building['building_id']}",
                    data=template_data,
                )
                with open(os.path.join(os.path.join(b_modelica_path.files_dir, "building.mo")), "w") as f:
                    f.write(file_data)

                ets_model_type = self.system_parameters.get_param_by_building_id(
                    building["building_id"], "ets.ets_properties_cooling.ets_connection_type"
                )

                ets_data = None
                if ets_model_type == "Indirect":
                    ets_data = self.system_parameters.get_param_by_building_id(
                        building["building_id"],
                        "ets.ets_properties_cooling"
                    )
                else:
                    raise Exception("Only ETS Model of type 'Indirect' type enabled currently")

                file_data = cooling_indirect_template.render(
                    project_name=scaffold.project_name,
                    model_name=f"B{building['building_id']}",
                    data=template_data,
                    ets_data=ets_data,
                )

                with open(os.path.join(os.path.join(b_modelica_path.files_dir, "CoolingIndirect.mo")), "w") as f:
                    f.write(file_data)

                full_model_name = os.path.join(
                    scaffold.project_name,
                    scaffold.loads_path.files_relative_dir,
                    f"B{building['building_id']}",
                    "TimeSeriesCouplingETS").replace(os.path.sep, '.')

                file_data = timeSeries_ets_mos_template.render(
                    full_model_name=full_model_name, model_name="TimeSeriesCouplingETS"
                )

                with open(os.path.join(b_modelica_path.scripts_dir, "RunTimeSeriesCouplingETS.mos"), "w") as f:
                    f.write(file_data)

                self.run_template(
                    timeSeries_ets_coupling_template,
                    os.path.join(b_modelica_path.files_dir, "TimeSeriesCouplingETS.mo"),
                    project_name=scaffold.project_name,
                    model_name=f"B{building['building_id']}",
                    data=template_data,
                )

                self.copy_required_mo_files(b_modelica_path.files_dir, within=f'{scaffold.project_name}.Loads')
        finally:
            os.chdir(curdir)

        # run post process to create the remaining project files for this building
        self.post_process(scaffold, building_names)

    def post_process(self, scaffold, building_names):
        """
        Cleanup the export of TimeSeries files into a format suitable for the district-based analysis. This includes
        the following:

            * Add a Loads project
            * Add a project level project

        :param scaffold: Scaffold object, Scaffold of the entire directory of the project.
        :param building_names: list, names of the buildings that need to be cleaned up after export
        :return: None
        """
        for b in building_names:
            b_modelica_path = os.path.join(scaffold.loads_path.files_dir, b)
            new_package = PackageParser.new_from_template(
                b_modelica_path, b,
                ["building", "CoolingIndirect", "TimeSeriesCouplingETS"],
                within=f"{scaffold.project_name}.Loads"
            )
            new_package.save()

        # now create the Loads level package. This (for now) will create the package without considering any existing
        # files in the Loads directory.
        package = PackageParser.new_from_template(
            scaffold.loads_path.files_dir, "Loads", building_names, within=f"{scaffold.project_name}"
        )
        package.save()

        # now create the Package level package. This really needs to happen at the GeoJSON to modelica stage, but
        # do it here for now to aid in testing.
        pp = PackageParser.new_from_template(
            scaffold.project_path, scaffold.project_name, ["Loads"]
        )
        pp.save()
