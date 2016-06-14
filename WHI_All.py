#-------------------------------------------------------------------------------
# Name:        WHI_All
# Purpose:
#
# Author:      DASHNEY
#
# Created:     14/04/2016
# Copyright:
# Licence:     <your licence>
#-------------------------------------------------------------------------------

import arcpy, config, util, calc, os, datetime, sys
import WHI_modules

arcpy.env.overwriteOutput = True


if not arcpy.Exists(config.temp_gdb):
    arcpy.CreateFileGDB_management(os.path.dirname(config.temp_gdb), os.path.basename(config.temp_gdb))

# run ALL modules in the order specified in the following list
# if one fails, print the error and move on to the next until done

modules = [WHI_modules.treeCanopy, WHI_modules.riparianInt, WHI_modules.EIA, WHI_modules.streamConn, WHI_modules.floodplainCon, WHI_modules.shallowWaterRef, WHI_modules.streamAccess, WHI_modules.subwshed_Attach, util.archive]
for module in modules:
    try:
        module()
    except Exception as e:
        arcpy.Delete_management("in_memory")
        print e.message
        print str(module.__name__) + " failed - Exiting module"
        print "----------------------------------------------------------------------------------"
