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

"""
util.delete_gdb_contents(config.temp_gdb)

modules = [
WHI_modules.EIA(),
WHI_modules.treeCanopy(),
WHI_modules.riparianInt(),
WHI_modules.streamConn(),
WHI_modules.floodplainCon(),
WHI_modules.streamAccess(),
WHI_modules.shallowWaterRef()
]

for module in modules:
    try:
        module()
    except Exception as e:
        arcpy.Delete_management("in_memory")

        msg1 = e.message
        msg2 = str(module.__name__) + " failed - Exiting module"
        msg3 = "----------------------------------------------------------------------------------"

        util.log(msg1)
        util.log(msg2)
        util.log(msg3)
"""

# if other modules successful, run these
#WHI_modules.subwshed_Attach()
#util.archive() # - last run of this the outputs did not copy for some reason, check to see if this is working



