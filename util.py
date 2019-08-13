#-------------------------------------------------------------------------------
# Name:        util
# Purpose:     Utility functions for ARC
#
# Author:
#
# Created:     09/02/2015
# Copyright:   (c) City of Portland BES 2015
# Licence:     Eclipse
#-------------------------------------------------------------------------------
import arcpy, os, datetime, config, xlrd


def archive():

    # DCA - this should really be broken out into inputs vs outputs folders so its not all lumped together

    log("Archiving WHI inputs and outputs")

    # create new geodatabse
    archive_gdb = "WHI_archive_" +  datetime.datetime.now().strftime('%Y%m%d')
    full_path = os.path.join(config.archive_loc, archive_gdb + ".gdb")
    if arcpy.Exists(full_path) == False:
        arcpy.CreateFileGDB_management(config.archive_loc, archive_gdb)

    # copy input files into geodatabase
    log("...archiving inputs")

    # vector sources
    for fc in config.vect_archive_list:
        if arcpy.Exists(fc) == True:
            log("......vectors")
            arcpy.FeatureClassToGeodatabase_conversion(config.vect_archive_list, full_path)
            return
        else:
            return str(fc) + " not found"

# exclude these for now - they are going to be pretty static and take forever to copy
##    # raster sources
##    for fc in config.rast_archive_list:
##        if arcpy.Exists(fc) == True:
##            log("......rasters")
##            arcpy.RasterToGeodatabase_conversion(config.rast_archive_list, full_path)
##        else:
##            return str(fc) + " not found"

    # copy output files into geodatabase
    log("...archiving outputs")

    # table outputs
    log("......tables")
    arcpy.env.workspace = config.primary_output
    tables = arcpy.ListTables()
    arcpy.TableToGeodatabase_conversion(tables, full_path)

    # feature class outputs
    log("......feature class(es)")
    fcs = arcpy.ListFeatureClasses()
    arcpy.FeatureClassToGeodatabase_conversion(fcs, full_path)

    log("Archiving complete")


def log(message):
    output_dir = r"\\besfile1\asm_projects\Watershed_Health_Index\Dev"
    time_stamp = datetime.datetime.now().strftime('%x %X')
    full_message = "{0} - {1}".format(time_stamp, message)
    print full_message
    log_file = open(os.path.join(output_dir, "WHI_Build.log"), 'a')
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

def tableTo_primaryOutput(input_object):
    log("Copy result table to primary output gdb")
    desc = arcpy.Describe(input_object)
    if desc.dataElementType <> 'DETable':
        # if not a table - convert fc to table
        table_view = arcpy.MakeTableView_management(input_object, desc.basename)
        # move table to primary output gdb
        full_output_name = os.path.join(config.primary_output, desc.basename)
        arcpy.TableToGeodatabase_conversion(table_view, config.primary_output)
    else:
        # if already a table - copy table to primary output gdb
        full_output_name = os.path.join(config.primary_output, desc.basename)
        arcpy.Copy_management(input_object, full_output_name)

def delete_gdb_contents(target_gdb):
    msg = "Deleting contents of gdb: " + target_gdb
    log(msg)
    arcpy.env.workspace = target_gdb
    fcs = arcpy.ListFeatureClasses()
    if len(fcs) > 0 or len(fcs) != None:
        for fc in fcs:
            arcpy.Delete_management(fc)
    tables = arcpy.ListTables()
    if len(tables) > 0 or len(tables) != None:
        for table in tables:
            arcpy.Delete_management(table)
    rasters = arcpy.ListRasters()
    if len(rasters) > 0 or len(rasters) != None:
        for raster in rasters:
            arcpy.Delete_management(raster)

def get_wshed_vals_from_xls(xls_file_loc):
    # pulls values from excel file
    wb = xlrd.open_workbook(xls_file_loc)
    sheet = wb.sheet_by_name("Percent Piped Deduction") # this changes if the sheet name changes
    value_dict = {}
    n = 0
    while n < 6: # this value (number of rows) would change if more records were added to input
        n = n + 1
        value_dict[sheet.cell_value(n,0)] = sheet.cell_value(n,1)
    return value_dict

def main():
    pass

if __name__ == '__main__':
    main()