//within geojson_modelica_translator.model_connectors.templates;
model BuildingSpawnZ6WithCoolingIndirectETS
package MediumW = Buildings.Media.Water;
  extends PartialBuildingWithCoolingIndirectETS(
      final m1_flow_nominal=mBuiHea_flow_nominal,
      final m2_flow_nominal=mDis_flow_nominal,
      redeclare final package Medium1 =MediumW,
      redeclare final package Medium2 =MediumW,
    redeclare building bui(
      final idfName=idfName,
      final weaName=weaName,
      T_aChiWat_nominal=280.15,
      T_bChiWat_nominal=285.15,
      nPorts_aHeaWat=1,
      nPorts_bHeaWat=1,
      nPorts_bChiWat=1,
      nPorts_aChiWat=1),
    redeclare CoolingIndirect ets(
      redeclare package Medium =MediumW,
      final mDis_flow_nominal=mDis_flow_nominal,
      final mBui_flow_nominal=mBui_flow_nominal,
      dp1_nominal=500,
      dp2_nominal=500,
      use_Q_flow_nominal=true,
      Q_flow_nominal=-1*(sum(bui.terUni.QCoo_flow_nominal)),
      T_a1_nominal=273.15 + 5,
      T_a2_nominal=273.15 + 12,
      eta=0.8)
   "Spawn building connected to the indirect cooling ETS model");

  parameter String idfName=
    "modelica://Buildings/Resources/Data/ThermalZones/EnergyPlus/Validation/RefBldgSmallOffice/RefBldgSmallOfficeNew2004_Chicago.idf"
    "Name of the IDF file"
    annotation(Dialog(group="Building model parameters"));
  parameter String weaName=
    "modelica://Buildings/Resources/weatherdata/USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.mos"
    "Name of the weather file"
    annotation(Dialog(group="Building model parameters"));
  parameter Modelica.SIunits.MassFlowRate mDis_flow_nominal=bui.disFloCoo.m_flow_nominal*(bui.delTBuiCoo/bui.delTDisCoo)
   "Nominal mass flow rate of primary (district) district cooling side";
  parameter Modelica.SIunits.MassFlowRate mBuiHea_flow_nominal= bui.disFloHea.m_flow_nominal
    "Nominal mass flow rate of secondary (building) district heating side";
  parameter Modelica.SIunits.MassFlowRate mBui_flow_nominal= bui.disFloCoo.m_flow_nominal
    "Nominal mass flow rate of secondary (building) district cooling side";
  Modelica.Fluid.Sources.FixedBoundary preSou(
    redeclare package Medium = MediumW,
    nPorts=1)
    annotation (Placement(transformation(extent={{-80,-120},{-60,-100}})));

equation
  connect(preSou.ports[1],ets. port_b2) annotation (Line(points={{-60,-110},{-30,
              -110},{-30,-70}},     color={0,127,255}));
  annotation (Icon(graphics={
                      Bitmap(extent={{-72,-62},{62,74}},
                      fileName="modelica://Buildings/Resources/Images/ThermalZones/EnergyPlus/EnergyPlusLogo.png")}),
                  Diagram(coordinateSystem(extent={{-100,-140},{100,100}})));
end BuildingSpawnZ6WithCoolingIndirectETS;
