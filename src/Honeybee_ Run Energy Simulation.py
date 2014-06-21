"""
export geometries to idf file, and run the energy simulation

    Args:
        input1: ...
    Returns:
        readMe!: ...
"""
ghenv.Component.Name = "Honeybee_ Run Energy Simulation"
ghenv.Component.NickName = 'runEnergySimulation'
ghenv.Component.Message = 'VER 0.0.53\nJUN_21_2014'
ghenv.Component.Category = "Honeybee"
ghenv.Component.SubCategory = "09 | Energy | Energy"
ghenv.Component.AdditionalHelpFromDocStrings = "2"


import Rhino as rc
import scriptcontext as sc
import rhinoscriptsyntax as rs
import os
import System
from clr import AddReference
AddReference('Grasshopper')
import Grasshopper.Kernel as gh
import math

rc.Runtime.HostUtils.DisplayOleAlerts(False)


class WriteIDF(object):

    def EPZone(self, zone):
        return '\nZone,\n' + \
        '\t' + zone.name + ',\n' + \
        '\t' + `zone.north` + ',\t!-Direction of Relative North {deg}\n' + \
        '\t' + `zone.origin.X` + ',\t!- X Origin {m}\n' + \
        '\t' + `zone.origin.Y` + ',\t!- Y Origin {m}\n' + \
        '\t' + `zone.origin.Z` + ',\t!- Z Origin {m}\n' + \
        '\t1;\t!- Type\n'
    
    def EPZoneSurface (self, surface, namingMethod = 0, coordinatesList = False):
        if not coordinatesList: coordinatesList = surface.extractPoints()
        if namingMethod == 1:
            # these walls are only there as parent surfaces for nonplanar glazing surfaces
            srfNaming = 'count_for_glazing'
        elif type(coordinatesList[0])is not list and type(coordinatesList[0]) is not tuple:
            coordinatesList = [coordinatesList]
            srfNaming = 'no_counting'
        else:
            srfNaming = 'counting'
        
        fullString = ''
        for count, coordinates in enumerate(coordinatesList):
            if srfNaming == 'count_for_glazing': surfaceName = surface.name + '_glzP_' + `count`
            elif srfNaming == 'counting': surfaceName = surface.name + '_' + `count`
            elif srfNaming == 'no_counting': surfaceName = surface.name
            
            str_1 = '\nBuildingSurface:Detailed,\n' + \
                '\t' + surfaceName + ',\t!- Name\n' + \
                '\t' + surface.srfType[int(surface.type)] + ',\t!- Surface Type\n' + \
                '\t' + surface.construction + ',\t!- Construction Name\n' + \
                '\t' + surface.parent.name + ',\t!- Zone Name\n' + \
                '\t' + surface.BC + ',\t!- Outside Boundary Condition\n' + \
                '\t' + surface.BCObject.name + ',\t!- Outside Boundary Condition Object\n' + \
                '\t' + surface.sunExposure + ',\t!- Sun Exposure\n' + \
                '\t' + surface.windExposure + ',\t!- Wind Exposure\n' + \
                '\t' + surface.groundViewFactor + ',\t!- View Factor to Ground\n' + \
                '\t' + `len(coordinates)` + ',\t!- Number of Vertices\n'
        
            str_2 = '\t';
            
            for ptCount, pt in enumerate(coordinates):
                if ptCount < len (coordinates) - 1:
                    str_2 = str_2 + `pt.X` + ',\n\t' + `pt.Y` + ',\n\t' + `pt.Z` + ',\n\t'
                else:
                    str_2 = str_2 + `pt.X` + ',\n\t' + `pt.Y` + ',\n\t' + `pt.Z` + ';\n\n'
            fullString = fullString + str_1 + str_2
        return fullString
    
    def EPNonPlanarFenSurface(self, surface):
        glzCoordinateLists = surface.extractGlzPoints()
        
        # generate walls string
        parentSrfStr = self.EPZoneSurface (surface, namingMethod = 1, coordinatesList = glzCoordinateLists)
        
        def averagePts(ptList):
            pt = rc.Geometry.Point3d(0,0,0)
            for p in ptList: pt = pt + p
            return rc.Geometry.Point3d(pt.X/len(ptList), pt.Y/len(ptList), pt.Z/len(ptList))
            
        distance = 2 * sc.doc.ModelAbsoluteTolerance
        cornerStyle = rc.Geometry.CurveOffsetCornerStyle.None
        # offset was so slow so I changed the method to this
        insetCoordinates = []
        for coordinates in glzCoordinateLists:
            pts = []
            for pt in coordinates: pts.append(rc.Geometry.Point3d(pt.X, pt.Y, pt.Z))
            cenPt = averagePts(pts)
            insetPts = []
            for pt in pts:
                movingVector = rc.Geometry.Vector3d(cenPt-pt)
                movingVector.Unitize()
                newPt = rc.Geometry.Point3d.Add(pt, movingVector * 2 * sc.doc.ModelAbsoluteTolerance)
                insetPts.append(newPt)
            insetCoordinates.append(insetPts)
            
            glzStr = self.EPFenSurface (surface, parentNamingMethod = 1, glzCoordinatesList = insetCoordinates)
        
        return parentSrfStr + glzStr
            
    def EPFenSurface (self, surface, parentNamingMethod = 0, glzCoordinatesList = False):
        if not glzCoordinatesList: glzCoordinatesList = surface.extractGlzPoints()
        
        fullString = ''
        # print len(glzCoordinatesList)
        for count, coordinates in enumerate(glzCoordinatesList):
            if parentNamingMethod == 0:
                try: parentSurfaceName = surface.childSrfs[count].parent.name
                except: parentSurfaceName = surface.childSrfs[0].parent.name
            elif parentNamingMethod == 1:
                # print surface.childSrfs
                try:
                    parentSurfaceName = surface.childSrfs[count].parent.name + '_glzP_' + `count`
                except:
                    # this is just a fix for now! There is a problem here that the number of
                    # surfaces doesn't match the number of coordinates!
                    #print "fix line 126!"
                    parentSurfaceName = surface.childSrfs[0].parent.name + '_glzP_' + `count`
                    
            
            try: childSrf = surface.childSrfs[count]
            except: childSrf = surface.childSrfs[0]
            
            str_1 = '\nFenestrationSurface:Detailed,\n' + \
                '\t' + childSrf.name + '_' + `count` + ',\t!- Name\n' + \
                '\t' + childSrf.srfType[childSrf.type] + ',\t!- Surface Type\n' + \
                '\t' + childSrf.construction + ',\t!- Construction Name\n' + \
                '\t' + parentSurfaceName + ',\t!- Surface Name\n' + \
                '\t' + childSrf.BCObject.name + ',\t!- Outside Boundary Condition Object\n' + \
                '\t' + childSrf.groundViewFactor + ',\t!- View Factor to Ground\n' + \
                '\t' + childSrf.shadingControlName + ',\t!- Shading Control Name\n' + \
                '\t' + childSrf.frameName + ',\t!- Frame and Divider Name\n' + \
                '\t' + `childSrf.Multiplier`+ ',\t!- Multiplier\n' + \
                '\t' + `len(coordinates)` + ',\t!- Number of Vertices\n'
        
            str_2 = '\t';
            for ptCount, pt in enumerate(coordinates):
                if ptCount < len (coordinates) - 1:
                    str_2 = str_2 + `pt.X` + ',\n\t' + `pt.Y` + ',\n\t' + `pt.Z` + ',\n\t'
                else:
                    str_2 = str_2 + `pt.X` + ',\n\t' + `pt.Y` + ',\n\t' + `pt.Z` + ';\n\n'
            
            fullString = fullString + str_1 + str_2
            
        return fullString

    def EPShdSurface (self, surface):
        coordinatesList = surface.extractPoints()
        if type(coordinatesList[0])is not list and type(coordinatesList[0]) is not tuple: coordinatesList = [coordinatesList]
        
        fullString = ''
        for count, coordinates in enumerate(coordinatesList):
            str_1 = '\nShading:Building:Detailed,\n' + \
                    '\t' + surface.name + '_' + `count` + ',\t!- Name\n' + \
                    '\t' + surface.TransmittanceSCH + ',\t!- Transmittance Schedule Name\n' + \
                    '\t' + `len(coordinates)` + ',\t!- Number of Vertices\n'    
    
            str_2 = '\t';
            for ptCount, pt in enumerate(coordinates):
                if ptCount < len (coordinates) - 1:
                    str_2 = str_2 + `pt.X` + ',\n\t' + `pt.Y` + ',\n\t' + `pt.Z` + ',\n\t'
                else:
                    str_2 = str_2 + `pt.X` + ',\n\t' + `pt.Y` + ',\n\t' + `pt.Z` + ';\n\n'
            
            fullString = fullString + str_1 + str_2
        
        return fullString

    def EPZoneListStr(self, zoneListName, zones):
        str_1 = 'ZoneList,\n' + \
                '\t' + zoneListName + ',\n'
                
        str_2 = ''
        for zoneCount, zone in enumerate(zones):
            if zoneCount < len(zones) - 1:
                str_2 = str_2 + '\t' + zone.name + ',\n'
            else:
                str_2 = str_2 + '\t' + zone.name + ';\n\n'
        return str_1 + str_2

    def EPHVACTemplate( self, name, zone):
        
        heatingSCHName = zone.heatingSetPtSchedule
        if zone.heatingSetPtSchedule != "":
            constantHeatingSetPoint = zone.heatingSetPtSchedule
        else:
            constantHeatingSetPoint = '' # I should add this to zones later
        
        coolingSCHName = zone.coolingSetPtSchedule
        if zone.heatingSetPtSchedule != "":
            constantCoolingSetPoint = zone.coolingSetPtSchedule
        else:
            constantCoolingSetPoint = ''
        
        return '\nHVACTemplate:Thermostat,\n' + \
                '\t' + name + ',                    !- Name\n' + \
                '\t' + heatingSCHName + ',          !- Heating Setpoint Schedule Name\n' + \
                '\t' + constantHeatingSetPoint + ', !- Constant Heating Setpoint {C}\n' + \
                '\t' + coolingSCHName + ',          !- Cooling Setpoint Schedule Name\n' + \
                '\t' + constantCoolingSetPoint + '; !- Constant Cooling Setpoint {C}\n'

    def EPIdealAirSystem(self, zone, thermostatName):
        return '\nHVACTemplate:Zone:IdealLoadsAirSystem,\n' + \
            '\t' + zone.name + ',\t!- Zone Name\n' + \
            '\t' + thermostatName + ';\t!- Template Thermostat Name\n\n'

    def EPSiteLocation(self, epw_file):
        epwfile = open(epw_file,"r")
        headline = epwfile.readline()
        csheadline = headline.split(',')
        locName = csheadline[1]+'\t'+csheadline[3]
        lat = csheadline[-4]
        lngt = csheadline[-3]
        timeZone = csheadline[-2]
        elev = csheadline[-1][:-1]
        locationString = "\nSite:Location,\n" + \
            '\t' + locName + ',\n' + \
            '\t' + lat + ',    !Latitude\n' + \
            '\t' + lngt + ',   !Longitude\n' + \
            '\t' + timeZone + ', !Time Zone\n' + \
            '\t' + elev + ';   !Elevation\n'
        epwfile.close()
        return locationString

    def EPVersion(self, version = 8.1):
        return '\nVersion, ' + `version` + ';\n'
    
    def EPTimestep(self, timestep = 6):
        return '\nTimestep, ' + `timestep` + ';\n'
    
    def EPShadowCalculation(self, calculationMethod = "AverageOverDaysInFrequency", frequency = 6, maximumFigures = 1500):
        return '\nShadowCalculation,\n' + \
               '\t' + calculationMethod + ',        !- Calculation Method\n' + \
               '\t' + str(frequency) + ',        !- Calculation Frequency\n' + \
               '\t' + str(maximumFigures) + ';    !- Maximum Figures in Shadow Overlap Calculation\n'

    def EPProgramControl(self, numT = 10):
        return '\nProgramControl,\n' + \
               '\t' + `numT` + '; !- Number of Threads AllowedNumber\n'
    
    def EPBuilding(self, name= 'honeybeeBldg', north = 0, terrain = 'City',
                    loadConvergenceTol = 0.04, tempConvergenceTol = 0.4,
                    solarDis = 'FullInteriorAndExteriorWithReflections', maxWarmUpDays = 25,
                    minWarmUpDays = 6):
                    # 'FullInteriorAndExterior'
        return '\nBuilding,\n' + \
                '\t' + name + ', !- Name\n' + \
                '\t' + `north` + ', !- North Axis {deg}\n' + \
                '\t' + terrain + ', !- Terrain\n' + \
                '\t' + `loadConvergenceTol` + ', !- Loads Convergence Tolerance Value\n' + \
                '\t' + `tempConvergenceTol` + ', !- Temperature Convergence Tolerance Value {deltaC}\n' + \
                '\t' + solarDis + ', !- Solar Distribution or maybe FullExterior\n' + \
                '\t' + `maxWarmUpDays` + ', !- Maximum Number of Warmup Days\n' + \
                '\t' + `minWarmUpDays` + '; !- Minimum Number of Warmup Days\n'
    
    def EPHeatBalanceAlgorithm(self, algorithm = 'ConductionTransferFunction'):
        return '\nHeatBalanceAlgorithm, ' + algorithm + ';\n'
    
    def EPSurfaceConvectionAlgorithm(self, insideAlg = 'TARP', outsideAlg = 'DOE-2'):
        insideStr = '\nSurfaceConvectionAlgorithm:Inside, ' + insideAlg + ';\n'
        outsideStr = '\nSurfaceConvectionAlgorithm:Outside, '+ outsideAlg + ';\n'
        return insideStr + outsideStr
    
    def EPSimulationControl(self, zoneSizing = 'No', systemSizing ='No', plantSizing = 'No',
                                runForSizing = 'No', runForWeather = 'Yes'):
        booleanToText = {
                         True : "Yes",
                         False: "No",
                         "Yes": "Yes",
                         "No" : "No"
                         }
                         
        return '\nSimulationControl,\n' + \
                '\t' + booleanToText[zoneSizing] + ',    !- Do Zone Sizing Calculation\n' + \
                '\t' + booleanToText[systemSizing] + ',  !- Do System Sizing Calculation\n' + \
                '\t' + booleanToText[plantSizing] + ',   !- Do Plant Sizing Calculation\n' + \
                '\t' + booleanToText[runForSizing] + ',  !- Run Simulation for Sizing Periods\n' + \
                '\t' + booleanToText[runForWeather] + '; !- Run Simulation for Weather File Run Periods\n'
    
    def EPRunPeriod(self, name = 'annualRun', stDay = 1, stMonth = 1, endDay = 31, endMonth = 12):
        
        return '\nRunPeriod,\n' + \
               '\t' + name + ',    !- Name\n' + \
               '\t' + `stMonth` + ',   !- Begin Month\n' + \
               '\t' + `stDay` + ',    !- Begin Day of Month\n' + \
               '\t' + `endMonth` + ', !- End Month\n' + \
               '\t' + `endDay` + ',   !- End Day of Month\n' + \
               '\t' + 'UseWeatherFile,   !- Day of Week for Start Day\n' + \
               '\t' + 'Yes,              !- Use Weather File Holidays and Special Days\n' + \
               '\t' + 'Yes,              !- Use Weather File Daylight Saving Period\n' + \
               '\t' + 'No,               !- Apply Weekend Holiday Rule\n' + \
               '\t' + 'Yes,              !- Use Weather File Rain Indicators\n' + \
               '\t' + 'Yes;              !- Use Weather File Snow Indicators\n'

    def EPGeometryRules(self, stVertexPos = 'LowerLeftCorner', direction = 'CounterClockWise', coordinateSystem = 'Absolute'):
        return '\nGlobalGeometryRules,\n' + \
                '\t' + stVertexPos + ',         !- Starting Vertex Position\n' + \
                '\t' + direction + ',        !- Vertex Entry Direction\n' + \
                '\t' + coordinateSystem + ';                !- Coordinate System\n'

    def EPDesignSpecOA(self, zone):
        """
        Returns design specification for outdoor air
        """
        return "\nDesignSpecification:OutdoorAir,\n" + \
               "\tDSOA" + zone.name + ", !- Name\n" + \
               "\tsum, !- Outdoor Air Method\n" + \
               "\t" + str(zone.ventilationPerPerson) + ", !- Outdoor Air Flow per Person {m3/s-person}\n" + \
               "\t" + str(zone.ventilationPerArea) + ", !- Outdoor Air Flow per Zone Floor Area {m3/s-m2}\n" + \
               "\t0.0; !- Outdoor Air Flow per Zone {m3/s}"


    def EPZoneInfiltration(self, zone, zoneListName = None):
        """ Methods: 
            0: Flow/Zone => Design Flow Rate -- simply enter Design Flow Rate
            1: Flow/Area => Flow per Zone Floor Area - Value * Floor Area (zone) = Design Flow Rate
            2: Flow/ExteriorArea => Flow per Exterior Surface Area - Value * Exterior Surface Area (zone) = Design Flow Rate
            3: Flow/ExteriorWallArea => Flow per Exterior Surface Area - Value * Exterior Wall Surface Area (zone) = Design Flow Rate
            4: AirChanges/Hour => Air Changes per Hour - Value * Floor Volume (zone) adjusted for m3/s = Design Volume Flow Rate "Idesign" in Equation is the result.
        """
        if zoneListName == None:
            zoneListName = zone.name
        
        name = zoneListName + "_Infiltration"
        
        # Rest of the methods are not available from the interface right now
        scheduleName = zone.infiltrationSchedule
        method = 1 
        value = zone.infiltrationRatePerArea
        
        methods = {0: 'Flow/Zone',
                   1: 'Flow/Area',
                   2: 'Flow/ExteriorArea',
                   3: 'Flow/ExteriorWallArea',
                   4: 'AirChanges/Hour'}
        
        designFlowRate = ''
        flowPerZoneArea = ''
        flowPerExteriorArea = ''
        flowPerExteriorWallArea = ''
        airChangePerHour = ''
        
        if method == 0: designFlowRate = `value`
        elif method == 1: flowPerZoneArea = `value`
        elif method == 2: flowPerExteriorArea = `value`
        elif method == 3: flowPerExteriorArea = `value`
        elif method == 4: airChangePerHour = `value`
        
        return '\nZoneInfiltration:DesignFlowRate,\n' + \
                '\t' + name + ',  !- Name\n' + \
                '\t' + zoneListName + ',  !- Zone or ZoneList Name\n' + \
                '\t' + scheduleName + ',  !- Schedule Name\n' + \
                '\t' + methods[method] + ',  !- Design Flow Rate Calculation Method\n' + \
                '\t' + designFlowRate + ',   !- Design Flow Rate {m3/s}\n' + \
                '\t' + flowPerZoneArea + ',  !- Flow per Zone Floor Area {m3/s-m2}\n' + \
                '\t' + flowPerExteriorArea + ', !- Flow per Exterior Surface Area {m3/s-m2}\n' + \
                '\t' + airChangePerHour + ',    !- Air Changes per Hour\n' + \
                '\t,                        !- Constant Term Coefficient\n' + \
                '\t,                        !- Temperature Term Coefficient\n' + \
                '\t,                        !- Velocity Term Coefficient\n' + \
                '\t;                        !- Velocity Squared Term Coefficient\n'
    
    
    def EPZoneElectricEquipment(self, zone, zoneListName = None):
            
        #name = 'largeOfficeElectricEquipment', zoneListName ='largeOffices', method = 2, value = 5.8125141276385044,
        #               scheduleName = 'Large Office_BLDG_EQUIP_SCH', endUseSub = 'ElectricEquipment'):
        
        """
        Methods:
            0: EquipmentLevel => Equipment Level -- simply enter watts of equipment
            1: Watts/Area => Watts per Zone Floor Area -- enter the number to apply.  Value * Floor Area = Equipment Level
            2: Watts/Person => Watts per Person -- enter the number to apply.  Value * Occupants = Equipment Level
        """
        
        if zoneListName == None:
            zoneListName = zone.name
        name = zoneListName + 'ElectricEquipment'
        method = 1
        value = zone.equipmentLoadPerArea
        scheduleName = zone.equipmentSchedule
        endUseSub = 'ElectricEquipment'

        methods = {0: 'EquipmentLevel',
           1: 'Watts/Area',
           2: 'Watts/Person'}

        designLevel = ''
        wattPerZoneArea = ''
        wattPerPerson = ''
        
        if method == 0: designLevel = `value`
        elif method == 1: wattPerZoneArea = `value`
        elif method == 2: wattPerPerson = `value`
        
        return '\nElectricEquipment,\n' + \
        '\t' + name + ',  !- Name\n' + \
        '\t' + zoneListName + ',  !- Zone or ZoneList Name\n' + \
        '\t' + scheduleName + ',  !- Schedule Name\n' + \
        '\t' + methods[method] + ', !- Design Level Calculation Method\n' + \
        '\t' + designLevel + ', !- Design Level {W}\n' + \
        '\t' + wattPerZoneArea + ', !- Watts per Zone Floor Area {W/m2}\n' + \
        '\t' + wattPerPerson + ',   !- Watts per Person {W/person}\n' + \
        '\t,                        !- Fraction Latent\n' + \
        '\t,                        !- Fraction Radiant\n' + \
        '\t,                        !- Fraction Lost\n' + \
        '\t' + endUseSub + ';       !- End-Use Subcategory\n'

    def EPZoneLights(self, zone, zoneListName = None):
        
        #name = 'largeOfficeLights', zoneListName ='largeOffices', method = 0, value = 9.687523546064174,
        #scheduleName = 'Large Office_BLDG_LIGHT_SCH', lightingLevel = 250):
        
        if zoneListName == None:
                zoneListName = zone.name
        name = zoneListName + 'OfficeLights'
        value = zone.lightingDensityPerArea
        scheduleName = zone.lightingSchedule
        
        if zone.daylightThreshold != "":
            method = 2
            lightingLevel = str(zone.daylightThreshold)
        else:
            method = 0
            lightingLevel = ""
        """
        Methods:
            0: Watts/Area => Watts per Zone Floor Area -- enter the number to apply.  Value * Floor Area = Equipment Level
            1: Watts/Person => Watts per Person -- enter the number to apply.  Value * Occupants = Equipment Level
        """
        
        methods = {0: 'Watts/Area',
                   1: 'Watts/Person',
                   2: 'LightingLevel'}
        
        wattPerZoneArea = ''
        wattPerPerson = ''
        
        if method == 0: wattPerZoneArea = `value`
        elif method == 1: wattPerPerson = `value`
            
        return '\nLights,\n' + \
        '\t' + name + ',  !- Name\n' + \
        '\t' + zoneListName + ',  !- Zone or ZoneList Name\n' + \
        '\t' + scheduleName + ',  !- Schedule Name\n' + \
        '\t' + methods[method] + ',       !- Design Level Calculation Method\n' + \
        '\t' + lightingLevel + ',       !- Lighting Level {W}\n' + \
        '\t' + wattPerZoneArea + ',       !- Watts per Zone Floor Area {W/m2}\n' + \
        '\t' + wattPerPerson + ',         !- Watts per Person {W/person}\n' + \
        '\t,                       !- Return Air Fraction\n' + \
        '\t,                       !- Fraction Radiant\n' + \
        '\t;                       !- Fraction Visible\n'

    
    def EPZonePeople(self, zone, zoneListName =None):
        
        # , method = 1, value = 0.053819575255912078,
        #scheduleName = 'Large Office_BLDG_OCC_SCH', activityScheduleName = 'Large Office_ACTIVITY_SCH',
        # fractionRadiant = 0.3, sensibleHeatFraction = 'autocalculate'):
            
        if zoneListName == None:
                zoneListName = zone.name
        name = zoneListName + 'OfficePeople'
        method = 1
        value = zone.numOfPeoplePerArea
        scheduleName = zone.occupancySchedule
        activityScheduleName = zone.occupancyActivitySch
        fractionRadiant = 0.3
        sensibleHeatFraction = 'autocalculate'
        
        """
        Methods:
            0: People -- simply enter number of occupants.
            1: People per Zone Floor Area -- enter the number to apply. Value * Floor Area = Number of people
            2: Zone Floor Area per Person -- enter the number to apply. Floor Area / Value = Number of people
        """
        if type(fractionRadiant) is int or type(fractionRadiant) is float: fractionRadiant = `fractionRadiant`
        if type(sensibleHeatFraction) is int or type(sensibleHeatFraction) is float: sensibleHeatFraction = `sensibleHeatFraction`
        
        methods = {0: 'People',
                   1: 'People/Area',
                   2: 'Area/Person'}
        
        numOfPeople = ''
        peoplePerArea = ''
        areaPerPerson = ''
        
        if method == 0: numOfPeople = `value`
        elif method == 1: peoplePerArea = `value`
        elif method == 2: areaPerPerson = `value`
        
        return '\nPeople,\n' + \
        '\t' + name + ',  !- Name\n' + \
        '\t' + zoneListName + ',  !- Zone or ZoneList Name\n' + \
        '\t' + scheduleName + ',  !- Number of People Schedule Name\n' + \
        '\t' + methods[method] + ', !- Number of People Calculation Method\n' + \
        '\t' + numOfPeople + ', !- Number of People\n' + \
        '\t' + peoplePerArea + ',  !- People per Zone Floor Area {person/m2}\n' + \
        '\t' + areaPerPerson + ',  !- Zone Floor Area per Person {m2/person}\n' + \
        '\t' + fractionRadiant + ',     !- Fraction Radiant\n' + \
        '\t' + sensibleHeatFraction + ',!- Sensible Heat Fraction\n' + \
        '\t' + activityScheduleName + ';!- Activity Level Schedule Name\n'
    
    def EPMaterialStr(self, materialName):
        materialData = None
        if materialName in sc.sticky ["honeybee_windowMaterialLib"].keys():
            materialData = sc.sticky ["honeybee_windowMaterialLib"][materialName]
        elif materialName in sc.sticky ["honeybee_materialLib"].keys():
            materialData = sc.sticky ["honeybee_materialLib"][materialName]
            
        if materialData!=None:
            numberOfLayers = len(materialData.keys())
            materialStr = materialData[0] + ",\n"
            
            # add the name
            materialStr =  materialStr + "  " + materialName + ",   !- name\n"
            
            for layer in range(1, numberOfLayers):
                if layer < numberOfLayers-1:
                    materialStr =  materialStr + "  " + str(materialData[layer][0]) + ",   !- " +  materialData[layer][1] + "\n"
                else:
                    materialStr =  materialStr + "  " + str(materialData[layer][0]) + ";   !- " +  materialData[layer][1] + "\n\n"
            return materialStr
       
       
    
    def EPConstructionStr(self, constructionName):
        constructionData = None
        if constructionName in sc.sticky ["honeybee_constructionLib"].keys():
            constructionData = sc.sticky ["honeybee_constructionLib"][constructionName]
    
        if constructionData!=None:
            materials = []
            numberOfLayers = len(constructionData.keys())
            constructionStr = constructionData[0] + ",\n"
            # add the name
            constructionStr =  constructionStr + "  " + constructionName + ",   !- name\n"
            
            for layer in range(1, numberOfLayers):
                if layer < numberOfLayers-1:
                    constructionStr =  constructionStr + "  " + constructionData[layer][0] + ",   !- " +  constructionData[layer][1] + "\n"
                else:
                    constructionStr =  constructionStr + "  " + constructionData[layer][0] + ";   !- " +  constructionData[layer][1] + "\n\n"
                materials.append(constructionData[layer][0])
                
            return constructionStr, materials
            
    def EPSCHStr(self, scheduleName):
        scheduleData = None
        if scheduleName in sc.sticky ["honeybee_ScheduleLib"].keys():
            scheduleData = sc.sticky ["honeybee_ScheduleLib"][scheduleName]
        elif scheduleName in sc.sticky ["honeybee_ScheduleTypeLimitsLib"].keys():
            scheduleData = sc.sticky["honeybee_ScheduleTypeLimitsLib"][scheduleName]
    
        if scheduleData!=None:
            numberOfLayers = len(scheduleData.keys())
            scheduleStr = scheduleData[0] + ",\n"
            
            # add the name
            scheduleStr =  scheduleStr  + "  " +  scheduleName + ",   !- name\n"
            
            for layer in range(1, numberOfLayers):
                if layer < numberOfLayers - 1:
                    scheduleStr =  scheduleStr + "  " + scheduleData[layer][0] + ",   !- " +  scheduleData[layer][1] + "\n"
                else:
                    scheduleStr =  scheduleStr + "  " + str(scheduleData[layer][0]) + ";   !- " +  scheduleData[layer][1] + "\n\n"
            return scheduleStr

class RunIDF(object):
    
    def writeBatchFile(self, workingDir, idfFileName, epwFileAddress, EPDirectory = 'C:\\EnergyPlusV8-1-0'):
        
        workingDrive = workingDir[:2]
        
        if idfFileName.EndsWith('.idf'):  shIdfFileName = idfFileName.replace('.idf', '')
        else: shIdfFileName = idfFileName
        
        if not workingDir.EndsWith('\\'): workingDir = workingDir + '\\'
        
        fullPath = workingDir + shIdfFileName
        
        folderName = workingDir.replace( (workingDrive + '\\'), '')
        batchStr = workingDrive + '\ncd\\' +  folderName + '\n' + EPDirectory + \
                '\\Epl-run ' + fullPath + ' ' + fullPath + ' idf ' + epwFileAddress + ' EP N nolimit N N 0 Y'
    
        batchFileAddress = fullPath +'.bat'
        batchfile = open(batchFileAddress, 'w')
        batchfile.write(batchStr)
        batchfile.close()
        
        #execute the batch file
        os.system(batchFileAddress)
        #os.system('C:\\honeybee\\runIt.bat')
            
    def readResults(self):
        pass


sc.sticky["honeybee_WriteIDF"] = WriteIDF
sc.sticky["honeybee_RunIDF"] = RunIDF


def main(north, epwFileAddress, EPParameters, analysisPeriod, HBZones, HBContext, simulationOutputs, writeIdf, runEnergyPlus, workingDir, idfFileName, meshingLevel):
    # import the classes
    w = gh.GH_RuntimeMessageLevel.Warning
    
    if not sc.sticky.has_key('ladybug_release')and sc.sticky.has_key('honeybee_release'):
        print "You should first let both Ladybug and Honeybee to fly..."
        ghenv.Component.AddRuntimeMessage(w, "You should first let both Ladybug and Honeybee to fly...")
        return -1
    
    # make sure epw file address is correct
    if not epwFileAddress.endswith(epwFileAddress) or not os.path.isfile(epwFileAddress):
        msg = "Wrong weather file!"
        print msg
        ghenv.Component.AddRuntimeMessage(w, msg)
        return -1
    
    lb_preparation = sc.sticky["ladybug_Preparation"]()
    hb_scheduleLib = sc.sticky["honeybee_DefaultScheduleLib"]()
    hb_writeIDF = sc.sticky["honeybee_WriteIDF"]()
    hb_runIDF = sc.sticky["honeybee_RunIDF"]()
    hb_hive = sc.sticky["honeybee_Hive"]()
    hb_EPScheduleAUX = sc.sticky["honeybee_EPScheduleAUX"]()
    hb_EPPar = sc.sticky["honeybee_EPParameters"]()
    
    northAngle, northVector = lb_preparation.angle2north(north)
    stMonth, stDay, stHour, endMonth, endDay, endHour = lb_preparation.readRunPeriod(analysisPeriod, True)
    conversionFac = lb_preparation.checkUnits()
    
    # check for folder and idf file address
    
    # if workingDir\
    ## check for idf file to be connected
    if idfFileName == None: idfFileName = 'unnamed.idf'
    elif idfFileName[-3:] != 'idf': idfFileName = idfFileName + '.idf'
    
    # make working directory
    if workingDir: workingDir = lb_preparation.removeBlankLight(workingDir)
    else: workingDir = "c:\\ladybug"
    
    workingDir = os.path.join(workingDir, idfFileName.split(".idf")[0], "EnergyPlus")
    
    workingDir = lb_preparation.makeWorkingDir(workingDir)
    
    # make sure the directory has been created
    if workingDir == -1: return -1
    workingDrive = workingDir[0:1]
    
    
    idfFileFullName = workingDir + "\\" + idfFileName
    idfFile = open(idfFileFullName, "w")
    
    ################## HEADER ###################
    print "[1 of 7] Writing simulation parameters..."
    
    # Version,8.1;
    idfFile.write(hb_writeIDF.EPVersion())
    
    # Read simulation parameters
    timestep, shadowPar, solarDistribution, simulationControl, ddyFile = hb_EPPar.readEPParams(EPParameters)
    
    # Timestep,6;
    idfFile.write(hb_writeIDF.EPTimestep(timestep))
    
    # ShadowCalculation
    idfFile.write(hb_writeIDF.EPShadowCalculation(*shadowPar))
    
    # NumThread
    idfFile.write(hb_writeIDF.EPProgramControl())
    
    # Building
    EPBuilding = hb_writeIDF.EPBuilding(idfFileName, math.degrees(northAngle),
                                        'City', 0.04, 0.4, solarDistribution,
                                        maxWarmUpDays =25, minWarmUpDays = 6)
                    
    idfFile.write(EPBuilding)
    
    # HeatBalanceAlgorithm
    idfFile.write(hb_writeIDF.EPHeatBalanceAlgorithm())
    
    # SurfaceConvectionAlgorithm
    idfFile.write(hb_writeIDF.EPSurfaceConvectionAlgorithm())
    
    # Location
    idfFile.write(hb_writeIDF.EPSiteLocation(epwFileAddress))
    
    # simulationControl
    idfFile.write(hb_writeIDF.EPSimulationControl(*simulationControl))
    
    # runningPeriod
    idfFile.write(hb_writeIDF.EPRunPeriod('customRun', stDay, stMonth, endDay, endMonth))
    
    # for now I write all the type limits but it can be cleaner
    scheduleTypeLimits = sc.sticky["honeybee_ScheduleTypeLimitsLib"]["List"]
    for scheduleTypeLimit in scheduleTypeLimits:
        try: idfFile.write(hb_writeIDF.EPSCHStr(scheduleTypeLimit))
        except: pass
    
    # Geometry rules
    idfFile.write(hb_writeIDF.EPGeometryRules())
    
    # Shading Surfaces
    if HBContext and HBContext[0]!=None:
        print "[2 of 6] Writing context surfaces..."
        # call the objects from the lib
        shadingPyClasses = hb_hive.callFromHoneybeeHive(HBContext)
        for shading in shadingPyClasses:
            #print shading.name
            #print hb_writeIDF.EPShdSurface(shading)
            idfFile.write(hb_writeIDF.EPShdSurface(shading))
    else:
        print "[2 of 6] No context surfaces..."
        
        
    #################  BODY #####################
    print "[3 of 6] Writing geometry..."
    # call the objects from the lib
    thermalZonesPyClasses = hb_hive.callFromHoneybeeHive(HBZones)
    EPConstructionsCollection = []
    EPMaterialCollection = []
    EPScheduleCollection = []
    ZoneCollectionBasedOnSchAndLoads = {} # This will be used to create zoneLists
    
    for zone in thermalZonesPyClasses:
        # Zone
        idfFile.write(hb_writeIDF.EPZone(zone))
        
        if zone.hasNonPlanarSrf or zone.hasInternalEdge:
            zone.prepareNonPlanarZone(meshingLevel, isEnergyPlus= True)
        
        # get the schedule and loads for the zone
        schedules = zone.getCurrentSchedules(True)
        loads = zone.getCurrentLoads(True)
        
        # create a unique key based on schedules and loads
        # zones with similar keys will be grouped
        key = ",".join(schedules.values() + loads.values())
        if key not in ZoneCollectionBasedOnSchAndLoads.keys():
            ZoneCollectionBasedOnSchAndLoads[key] = []
        
        ZoneCollectionBasedOnSchAndLoads[key].append(zone)
        
        # collect unique schedules
        for schedule in schedules.values():
            if schedule not in EPScheduleCollection:
                EPScheduleCollection.append(schedule)
                
                
        for srf in zone.surfaces:
            # check if there is an energyPlus material
            if srf.EPConstruction != None:
                srf.construction = srf.EPConstruction
            # else try to find the material based on bldg type and climate zone
            # the surface will use the default construction
            if not srf.construction in EPConstructionsCollection:
                EPConstructionsCollection.append(srf.construction)
            
            # Surfaces
            idfFile.write(hb_writeIDF.EPZoneSurface(srf))
            if srf.hasChild:
                # check the construction
                # this should be moved inside the function later
                for childSrf in srf.childSrfs:
                    # check if there is an energyPlus material
                    if childSrf.EPConstruction != None:
                        childSrf.construction = childSrf.EPConstruction
                    # else try to find the material based on bldg type and climate zone
                    # I will apply this later
                    # the surface will use the default construction
                    if not childSrf.construction in EPConstructionsCollection:
                            EPConstructionsCollection.append(childSrf.construction)
                    
                # write the glazing strings
                if srf.isPlanar: idfFile.write(hb_writeIDF.EPFenSurface(srf))
                else: idfFile.write(hb_writeIDF.EPNonPlanarFenSurface(srf))
        
    ################ Construction #####################
    print "[4 of 6] Writing materials and constructions..."
    
    # Write constructions
    for cnstr in EPConstructionsCollection:
        constructionStr, materials = hb_writeIDF.EPConstructionStr(cnstr)
        idfFile.write(constructionStr)
        
        for mat in materials:
            if not mat in EPMaterialCollection:
                idfFile.write(hb_writeIDF.EPMaterialStr(mat))
                EPMaterialCollection.append(mat)
    
    
    ################ BODYII #####################
    print "[5 of 7] Writing schedules..."
    
    # Write Schedules
    for schedule in EPScheduleCollection:
        scheduleValues, comments = hb_EPScheduleAUX.getScheduleDataByName(schedule, ghenv.Component)
        if scheduleValues!=None:
            idfFile.write(hb_writeIDF.EPSCHStr(schedule))
            
            # collect all the schedule items inside the schedule
            if scheduleValues[0] == "Schedule:Week:Daily":
                for value in scheduleValues[1:]:
                    if value not in EPScheduleCollection:
                        EPScheduleCollection.append(value)
                
            # add schedules which are referenced inside other schedules to the list
            for value in scheduleValues[1:]:
                if value.startswith("Schedule:") and value not in EPScheduleCollection:
                    EPScheduleCollection.append(value)
    
    print "[6 of 7] Writing loads and ideal air system..."
    listCount = 0
    listName = None
    for key, zones in ZoneCollectionBasedOnSchAndLoads.items():
        
        # removed for now as apparently openstudio import idf does not like lists!
        #if len(zones) > 1:
        #    listCount += 1 
        #    # create a zone list
        #    listName = "_".join([zones[0].bldgProgram, zones[0].zoneProgram, str(listCount)])
        #    
        #    idfFile.write(hb_writeIDF.EPZoneListStr(listName, zones))
        
        for zone in zones:
            #zone = zones[0]
            
            #   HAVC System
            if listName!=None:
                HAVCTemplateName = listName + "_HVAC"
                for zone in zones:
                    idfFile.write(hb_writeIDF.EPIdealAirSystem(zone, HAVCTemplateName))
                
            else:
                HAVCTemplateName = zone.name + "_HVAC"
                idfFile.write(hb_writeIDF.EPIdealAirSystem(zone, HAVCTemplateName))
        
            #   Thermostat
            idfFile.write(hb_writeIDF.EPHVACTemplate(HAVCTemplateName, zone))
                        
            #   LOADS - INTERNAL LOADS + PLUG LOADS
            idfFile.write(hb_writeIDF.EPZoneElectricEquipment(zone, listName))
        
            #   PEOPLE
            idfFile.write(hb_writeIDF.EPZonePeople(zone, listName))
        
            #   LIGHTs
            idfFile.write(hb_writeIDF.EPZoneLights(zone, listName))
        
            #   INFILTRATION
            idfFile.write(hb_writeIDF.EPZoneInfiltration(zone, listName))
            
            # Specification Outdoor Air
            idfFile.write(hb_writeIDF.EPDesignSpecOA(zone))
        
    ################## FOOTER ###################
    # write output lines
    # could be as a set of inputs
    if simulationOutputs:
        print "[7 of 7] Writing outputs..."
        idfFile.write('\n')
        for line in simulationOutputs:
            idfFile.write(line + '\n')
    else:
        print "[7 of 7] No outputs! You usually want to get some outputs when you run an analysis. Just saying..."
        
    idfFile.close()
    
    print "...\n... idf file is successfully written to : " + idfFileFullName + "\n"
    
    ######################## RUN ENERGYPLUS SIMULATION #######################
    resultFileFullName = None
    if runEnergyPlus:
        print "Analysis is running!..."
        # write the batch file
        hb_runIDF.writeBatchFile(workingDir, idfFileName, epwFileAddress)
        resultFileFullName = idfFileFullName.replace('.idf', '.csv')
        print "...\n...\n\nDone! Read below for errors and warnings:\n\n"
    else:
        print "Set runEnergyPlus to True!"
        
    return idfFileFullName, resultFileFullName 
        

if _writeIdf == True and _epwFile and _HBZones and _HBZones[0]!=None:
    
    result = main(north_, _epwFile, _energySimPar_, _analysisPeriod_, _HBZones,
                  HBContext_, simulationOutputs_, _writeIdf, runEnergyPlus_,
                  _workingDir_, _idfFileName_, meshingLevel_)
    if result!= -1:
        idfFileAddress, resultFileAddress = result
        if runEnergyPlus_:
            try:
                errorFileFullName = idfFileAddress.replace('.idf', '.err')
                errFile = open(errorFileFullName, 'r')
                for line in errFile: print line
                errFile.close()
            except:
                pass
else:
    print "At least one of the mandatory inputs in missing."