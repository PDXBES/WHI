#-------------------------------------------------------------------------------
# Name:        util
# Purpose:     Utility functions for ARC
#
# Author:      aengelmann_z, sainsbury_b
#
# Created:     09/02/2015
# Copyright:   (c) City of Portland BES 2015
# Licence:     Eclipse
#-------------------------------------------------------------------------------
import arcpy, os, datetime, config

output_dir = os.path.curdir

def archive(input):

    # create new geodatabse
    archive_gdb = arcpy.CreateFileGDB_management(config.archive_loc, "WHI_archive_" +  datetime.datetime.now().strftime('%Y%m%d'))

    # copy input files into geodatabase
    # vector sources
    for fc in config.vect_archive_list:
        if arcpy.Exists(fc) == True:
            arcpy.FeatureClassToGeodatabase_conversion(config.vect_archive_list, archive_gdb)
        else:
            return str(table) + " not found"

    #raster sources
    for fc in config.rast_archive_list:
        if arcy.Exists(fc) == True:
            arcpy.RasterToGeodatabase_conversion(config.rast_archive_list, archive_gdb)
        else:
            return str(table) + " not found"

    #copy result tables into archive - CURRENTLY SET TO WORK FOR TABLES ONLY
    arcpy.env.workspace = config.primary_output
    tables = arcpy.ListTables()
    arcpy.TableToGeodatabase_conversion(tables, archive_gdb)


def log(message):
    time_stamp = datetime.datetime.now().strftime('%x %X')
    full_message = "{0} - {1}".format(time_stamp, message)
    print full_message
    log_file = open(os.path.join(output_dir, "Swsp.Build.log"), 'a')
    log_file.write(full_message + "\n")
    log_file.close()

def create_dir(dir_path):
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)

#cleanup function - intended to release gdb locks
def clearWSLocks(inputWS):
  '''Attempts to clear locks on a workspace, returns stupid message.'''
  if all([arcpy.Exists(inputWS), arcpy.Compact_management(inputWS), arcpy.Exists(inputWS)]):
    return 'Workspace (%s) clear to continue...' % inputWS
  else:
    return '!!!!!!!! ERROR WITH WORKSPACE %s !!!!!!!!' % inputWS

def addShape_Area(inputFC):
    # add Shape_Area and calc sqft if does not exist
    sa_field = "Shape_Area"
    fields = arcpy.ListFields(inputFC)
    if sa_field not in fields:
        arcpy.AddField_management(inputFC, sa_field, "DOUBLE")
        expression = "{0}".format("!SHAPE.area@SQUAREFEET!")
        arcpy.CalculateField_management(inputFC, sa_field, expression, "PYTHON", )
        print "added and calculated Shape_Area"
    else:
        print "Shape_Area already exists"

def main():
    pass

if __name__ == '__main__':
    main()