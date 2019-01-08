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
    archive_gdb = "WHI_archive_" +  datetime.datetime.now().strftime('%Y%m%d')
    full_path = os.path.join(config.archive_loc, archive_gdb + ".gdb")
    if arcpy.Exists(full_path) == False:
        arcpy.CreateFileGDB_management(config.archive_loc, archive_gdb)

    # copy input files into geodatabase

    # vector sources
    for fc in config.vect_archive_list:
        if arcpy.Exists(fc) == True:
            arcpy.FeatureClassToGeodatabase_conversion(config.vect_archive_list, full_path)
            return
        else:
            return str(fc) + " not found"

    # raster sources
    for fc in config.rast_archive_list:
        if arcy.Exists(fc) == True:
            arcpy.RasterToGeodatabase_conversion(config.rast_archive_list, full_path)
        else:
            return str(fc) + " not found"

    # copy output files into geodatabase

    # table outputs
    arcpy.env.workspace = config.primary_output
    tables = arcpy.ListTables()
    arcpy.TableToGeodatabase_conversion(tables, full_path)

    # feature class outputs
    fcs = arcpy.ListFeatureClasses()
    arcpy.FeatureClassToGeodatabase_conversion(fcs, full_path)


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

def convertTo_table(input_fc):
    desc = arcpy.Describe(input_fc)
    if desc.dataElementType <> 'DETable':
        # make Table view
        table_view = arcpy.MakeTableView_management(input_fc, "in_memory" + r"\table_view")
        # table to table - put in temp
        temp = arcpy.TableToTable_conversion(table_view,config.temp_gdb,desc.basename)
        # delete original
        arcpy.Delete_management(input_fc)
        # table to table - put back in final output location
        table = arcpy.TableToGeodatabase_conversion(temp,config.primary_output)

def fishnetChop(comparison_fc):
    # Chops up the canopy fc using fishnet, intersects this with the comparison_fc,
    # then merges results back into one - seems to get around memory issues.
    # For now uses a fishnet of 3 polygons with city-wide extent.
    # canopy_combo_vect is a default input, the other is a param (comparison_fc)

    log ("Intersecting DSCs and landcover")

    log("generate list of IDs")
    IDlist = []
    with arcpy.da.SearchCursor(config.fishnet, "OID") as cursor:
        for row in cursor:
            IDlist.append(row[0])

    # chop up the canopy into 3 pieces to run through the intersect
    log("subset canopy polygons and run intersect on subsets")
    fishnet_input = arcpy.MakeFeatureLayer_management(config.fishnet, "in_memory" + r"\fishnet_input")
    canopy_input = arcpy.MakeFeatureLayer_management(config.canopy_combo_vect, "in_memory" + r"\canopy_input")
    for ID in IDlist:
        log("..." + str(ID) + " of 3 intersects")
        net_sub = arcpy.SelectLayerByAttribute_management(fishnet_input, "NEW_SELECTION", "OID = {0}".format(ID))
        canopy_sub = arcpy.SelectLayerByLocation_management(canopy_input,"HAVE_THEIR_CENTER_IN", net_sub, "", "NEW_SELECTION")
        canopy_copy = arcpy.CopyFeatures_management(canopy_sub, config.temp_gdb + r"\canopy_copy{0}".format(ID),"#","0","0","0")
        in_features = [canopy_copy,comparison_fc]
        sect_result = arcpy.Intersect_analysis(in_features, config.temp_gdb + r"\sect_result{0}".format(ID),"NO_FID","","INPUT")

    # then merge results
    log("combine results of intersects")
    arcpy.env.workspace = config.temp_gdb
    fcs = arcpy.ListFeatureClasses("sect_result*")
    sect_result = arcpy.Append_management([fcs[1], fcs[2]], fcs[0],"NO_TEST","","")

    return sect_result

def main():
    pass

if __name__ == '__main__':
    main()