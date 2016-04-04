#-------------------------------------------------------------------------------
# Name:        WHI_main
# Purpose:
#
# Author:      dashney
#
# Created:     02/12/2015

#-------------------------------------------------------------------------------

import arcpy, config, util, calc, os, datetime, sys
import WHI_modules

arcpy.env.overwriteOutput = True

if __name__ == '__main__':

    if not arcpy.Exists(config.temp_gdb):
        arcpy.CreateFileGDB_management(os.path.dirname(config.temp_gdb), os.path.basename(config.temp_gdb))

    #WHI_modules.EIA()
    #WHI_modules.streamConn()
    WHI_modules.treeCanopy()
    #WHI_modules.floodplainCon()
    #WHI_modules.shallowWaterRef()
    #WHI_modules.streamAccess()
    #WHI_modules.riparianInt()

    #WHI_modules.combine() - does not yet exist

    #util.archive() # should be run after every full process run to create a date stampted archive of inputs and results