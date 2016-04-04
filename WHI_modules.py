#-------------------------------------------------------------------------------
# Name:        WHI_modules
# Purpose:
#
# Author:      DASHNEY
#
# Created:     20/11/2015
# modules to calculate WHI scores
#-------------------------------------------------------------------------------

import arcpy, config, calc, util

arcpy.env.overwriteOutput = True


# ancillary functions

def sumBy(inputFC, groupby_list, sum_field, output):
    # input FC is the feature class to intersect with the subwatersheds and sum a field by subwatershed
    # groupby_list can be a list of one
    intersect = arcpy.Intersect_analysis([inputFC , config.subwatersheds],config.temp_gdb + r"\sect","NO_FID","#","INPUT")
    arcpy.Dissolve_management(intersect,output,groupby_list,sum_field,"MULTI_PART","DISSOLVE_LINES")

def rename_fields(table, out_table, new_name_by_old_name):
    """ Renames specified fields in input feature class/table
    :table:                 input table (can be fc, table, layer, etc)
    :out_table:             output table (can be fc, table, layer, etc)
    :new_name_by_old_name (dict):  {'old_field_name':'new_field_name',...}
    """
    existing_field_names = [field.name for field in arcpy.ListFields(table)]

    field_mappings = arcpy.FieldMappings()
    field_mappings.addTable(table)

    for old_field_name, new_field_name in new_name_by_old_name.iteritems():
        if old_field_name not in existing_field_names:
            message = "Field: {0} not in {1}".format(old_field_name, table)
            raise Exception(message)

        mapping_index = field_mappings.findFieldMapIndex(old_field_name)
        field_map = field_mappings.fieldMappings[mapping_index]
        output_field = field_map.outputField
        output_field.name = new_field_name
        output_field.aliasName = new_field_name
        field_map.outputField = output_field
        field_mappings.replaceFieldMap(mapping_index, field_map)

    # use merge with single input just to use new field_mappings
    arcpy.Merge_management(table, out_table, field_mappings)
    return out_table

def NullNumber_toZero(inputFC):
    # calc all Null values in all Double type fields to 0
    fieldlist = [f.name for f in arcpy.ListFields(inputFC) if f.type == "Double"]
    for field in fieldlist:
        with arcpy.da.UpdateCursor(inputFC,field) as rows:
            for row in rows:
                if row[0] == None:
                    row[0] = 0
                    rows.updateRow(row)
"""
def Vectorize_Veg(raster_veg_input, output): # Vectorize_Veg IS LIKELY NO LONGER NEEDED, KEEP TO MAKE SURE
    # creates a vectorized, dissolved, attribute corrected version of Metro Veg

    vegtype_dict = {0: "Built", 1: "Built", 2: "Low_Med", 3: "High", 4: "Water", 5: "Water"}
    veg_clip = arcpy.Clip_management(raster_veg_input,'',config.temp_gdb + r"\veg_clip",config.subwatersheds)
    veg_vect = arcpy.RasterToPolygon_conversion(veg_clip,config.temp_gdb + r"\veg_vect")
    veg_diss = arcpy.Dissolve_management(veg_vect, output,'',"MULTI_PART","DISSOLVE_LINES")
    arcpy.AddField_management(veg_diss,"Type","TEXT",'','',10)
    with arcpy.da.UpdateCursor(veg_diss, ["gridcode","Type"]) as rows:
        for row in rows:
            row[1] = config.vegtype_dict[row[0]]
            rows.updateRow(row)

"""

def createVeg_combo(comparison_fc, output):
    # creates a raster combining the 2007 Metro veg and a specified feature class (for WHI use = the subwatersheds)
    # converts output to vector
    # input 'comparison_fc' = the feature class to be compared - currently assumed to be vector and converted to raster
    # TO DO - add test for vector/raster and only convert if required!!!

    # clip landcover to subwatersehds and Reclassify the results (because extra values are added after the clip for some reason (??) )
    util.log("Clipping/ reclassifying landcover raster")
    arcpy.CheckOutExtension("Spatial")
    print "veg clip"
    veg_clip = arcpy.Clip_management(config.canopy,'',config.temp_gdb + r"\veg_clip",comparison_fc)
    print "veg reclass"
    # assign questionable, unnecessary values to the main 4 values (built, low veg, high veg, water)
    reclass_mapping = "0 1;1 1;2 2;3 3;4 4;5 4;6 1;7 1;8 1"
    veg_reclass = arcpy.sa.Reclassify(veg_clip,"Value", reclass_mapping,"DATA")

    # convert the comparison feature class to raster
    util.log("Converting comparison feature class to raster")
    arcpy.env.snapRaster = config.canopy
    arcpy.env.extent = "MAXOF"
    Comparison_raster = arcpy.FeatureToRaster_conversion(comparison_fc,"WATERSHED",config.temp_gdb + r"\wshed_toRast","3")
    tempComparison_raster = arcpy.sa.Raster(Comparison_raster)

    # combine landcover and comparison rasters
    util.log("Combining rasters")
    # multiply Comparison raster Value *100 so that the value can be parsed with the vegetation value
    combo = veg_reclass + (tempComparison_raster*100)
    combo.save(config.temp_gdb + r"\raster_combo")
    arcpy.CheckInExtension("Spatial")

    util.log("Converting the combo to vector and clipping")
    util.log("- converting")
    veg_vect = arcpy.RasterToPolygon_conversion(combo,"in_memory" + r"\veg_vect")
    util.log("- clipping")
    # clip takes 30 minutes - why?
    arcpy.Clip_analysis(veg_vect,config.subwatersheds,output)

def wshedCode_toText(input):
    # convert watershed code (int) to text
    # this takes almost an hour to run - why?
    util.log("Adding and populating WATERSHED field")
    arcpy.AddField_management(input,"WATERSHED","TEXT",'','',20)
    with arcpy.da.UpdateCursor(input, ["gridcode","WATERSHED"]) as rows:
        for row in rows:
            if row[0] < 200:
                row[1] = config.wshed_dict[100]
            elif row[0] > 199 and row[0] < 300:
                row[1] = config.wshed_dict[200]
            elif row[0] > 299 and row[0] < 400:
                row[1] = config.wshed_dict[300]
            elif row[0] > 399 and row[0] < 500:
                row[1] = config.wshed_dict[400]
            elif row[0] > 499 and row[0] < 600:
                row[1] = config.wshed_dict[500]
            else:
                row[1] = config.wshed_dict[600]
            rows.updateRow(row)

def sqFoot_calc(input):
    # fills the square footage values for each type of land cover
    # uses fields that get deleted later therefore may be hard to debug (or understand what its doing)

    util.log("Adding the sqft field for each type of land cover")
    for key, value in config.vegtype_dict.iteritems():
        arcpy.AddField_management(input,value,"Double")
    util.log("Populating the main landcover sqft fields")
    for key, value in wshed_dict.iteritems():
        pivot_wshed_sub = arcpy.MakeTableView_management(input,"pivot_wshed_sub","WATERSHED = '{0}'".format(value))
        for key, value in config.vegtype_dict.iteritems():
            cursor_fields = [x.name for x in arcpy.ListFields(pivot_wshed_sub,'*{0}'.format(key))]
            cursor_fields.append(value)
            with arcpy.da.UpdateCursor(pivot_wshed_sub,cursor_fields) as rows:
                for row in rows:
                    row[6] = row[0] + row[1] + row[2] + row[3] + row[4] + row[5]
                    rows.updateRow(row)

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# main functions

def EIA():

    # !!! Q - clip all managed ImpA (coming from geometry) to mapped ImpA?  - if not might extend beyond mapped

    util.log("starting EIA module")

    #subset inputs
    gs_layer = arcpy.MakeFeatureLayer_management(config.collection_lines,"gs_layer","UNITTYPE = 'CHGRSTFAC'")
    green_streets = arcpy.CopyFeatures_management(gs_layer, config.temp_gdb + r"\green_streets")
    ponds_swales = arcpy.MakeFeatureLayer_management(config.BMP_drainage,"ponds_swales","Gen_Type in ( 'CHANNEL - WATER QUALITY SWALE' , 'Detention Pond - Dry' , 'Detention Pond - Wet' , 'POND' , 'Swale' )")
    sumps =  arcpy.MakeFeatureLayer_management(config.BES_UIC,"sumps","Ops_Status = 'AC'")
    private_SMF = arcpy.Copy_management(config.privateSMF, config.temp_gdb + r"\private_SMF")

    # create mapped ImpA by subwatershed
    util.log("creating mapped ImpA")
    ImpA_cityclip = arcpy.Clip_analysis(config.ImpA,config.city_bound, "in_memory" + r"\ImpA_cityclip")
    ImpA_BMPclip = arcpy.Clip_analysis(ImpA_cityclip, ponds_swales , "in_memory" + r"\ImpA_BMPclip")
    ImpA_output = "in_memory" + r"\ImpA_diss"
    groupby_list = ["WATERSHED"]
    sum_field = "Shape_Area SUM"
    sumBy(ImpA_BMPclip, groupby_list, sum_field, ImpA_output)
    MIA_old = "SUM_Shape_Area"
    MIA_new = 'MIA_Area'
    old_new = {MIA_old : MIA_new}
    MIA_output_new = "in_memory" + r"\MIA"
    rename_fields(ImpA_output, MIA_output_new ,old_new)

    # create managed ImpA by subwatershed
    util.log("creating managed ImpA ...")

    util.log("... green street piece")
    aa_field = "assumed_area"
    arcpy.AddField_management(green_streets, aa_field, "LONG")
    with arcpy.da.UpdateCursor(green_streets, aa_field) as rows:
        for row in rows:
            row[0] = 3500
            rows.updateRow(row)
    groupby_list = ["WATERSHED"]
    sum_field = "assumed_area SUM"
    gs_output = config.temp_gdb + r"\gs_diss"
    sumBy(green_streets,groupby_list,sum_field,gs_output)
    greenstreet_old = "SUM_assumed_area"
    greenstreet_new = 'GreenStreet_Area'
    old_new = {greenstreet_old:greenstreet_new}
    gs_output_new = config.temp_gdb + r"\greenstreets"
    rename_fields(gs_output,gs_output_new , old_new)

    util.log("... BMP managed ImpA piece")
    BMP_output = "in_memory" + r"\bmp_diss"
    groupby_list = ["WATERSHED"]
    sum_field = "Shape_Area SUM"
    BMP_cityclip = arcpy.Clip_analysis(ponds_swales,config.city_bound, "in_memory" + r"\BMP_cityclip")
    sumBy(BMP_cityclip, groupby_list,sum_field, BMP_output)
    BMP_old = "SUM_Shape_Area"
    BMP_new = 'BMP_Area'
    old_new = {BMP_old : BMP_new}
    BMP_output_new = "in_memory" + r"\BMP"
    rename_fields(BMP_output , BMP_output_new , old_new)

    util.log("... sumped area piece")
    sump_output = "in_memory" + r"\sump_diss"
    groupby_list = ["WATERSHED"]
    sum_field = "Shape_Area SUM"
    sump_clip = arcpy.Clip_analysis(config.ImpA,config.sump_delin, "in_memory" + r"\ImpA_sumpclip")
    sumBy(sump_clip, groupby_list,sum_field, sump_output)
    sumps_old = "SUM_Shape_Area"
    sumps_new = 'Sump_Area'
    old_new = {sumps_old : sumps_new}
    sump_output_new = "in_memory" + r"\sumps"
    rename_fields(sump_output , sump_output_new , old_new)

    util.log("... ecoroofs piece")
    roof_output = "in_memory" + r"\roof_diss"
    groupby_list = ["WATERSHED"]
    sum_field = "SQ_FOOT SUM"
    sumBy(config.ecoroof_pnt,groupby_list,sum_field,roof_output)
    ecoroof_old = "SUM_SQ_FOOT"
    ecoroof_new = 'Ecoroof_Area'
    old_new = {ecoroof_old : ecoroof_new}
    roof_output_new = "in_memory" + r"\ecoroof"
    rename_fields(roof_output , roof_output_new , old_new)

    util.log("... private SMF piece")
    smf_output = config.temp_gdb + r"\smf_diss"
    smf_field = "assumed_value"
    arcpy.AddField_management(private_SMF, smf_field, "DOUBLE")
    keylist = []
    for key, value in config.smf_dict.iteritems():
        keylist.append(key)
    with arcpy.da.UpdateCursor(private_SMF, ["Code", smf_field]) as rows:
        for row in rows:
            if str(row[0]).strip() in keylist:
                row[1] = config.smf_dict[str(row[0]).strip()]
                rows.updateRow(row)

    # this block removes records where the Code field did not match a key from config.smf_dict
    with arcpy.da.UpdateCursor(private_SMF,smf_field) as rows:
        for row in rows:
            if row[0] is None:
                rows.deleteRow()
    groupby_list = ["WATERSHED"]
    sum_field = "assumed_value SUM"
    sumBy(private_SMF,groupby_list,sum_field,smf_output)
    SMF_old = "SUM_assumed_value"
    SMF_new = 'SMF_Area'
    old_new = {SMF_old : SMF_new}
    EIA_final = config.primary_output + r"\EIA_final"
    rename_fields(smf_output , EIA_final , old_new)

    sum_field = 'Shape_Area'
    subwshed_new = 'Subwshed_Area'
    old_new = {sum_field : subwshed_new}
    new_subwsheds = "in_memory" + r"\subwatersheds"
    rename_fields(config.subwatersheds, new_subwsheds ,old_new)

    # sum area values of the managed ImpA inputs
    util.log("adding  area fields to the private SMF output")
    arcpy.JoinField_management(EIA_final,"WASHD_CODE",gs_output_new,"WASHD_CODE",greenstreet_new)
    arcpy.JoinField_management(EIA_final,"WASHD_CODE",BMP_output_new,"WASHD_CODE",BMP_new)
    arcpy.JoinField_management(EIA_final,"WASHD_CODE",sump_output_new,"WASHD_CODE",sumps_new)
    arcpy.JoinField_management(EIA_final,"WASHD_CODE",roof_output_new,"WASHD_CODE",ecoroof_new)
    arcpy.JoinField_management(EIA_final,"WASHD_CODE",MIA_output_new,"WASHD_CODE",MIA_new)
    arcpy.JoinField_management(EIA_final,"WASHD_CODE",new_subwsheds,"WASHD_CODE",subwshed_new)

    # calc all numeric field Null values to 0 so that fields calculate correctly
    util.log("finding and calculating all Null values to 0")
    NullNumber_toZero(EIA_final)

    # sum the managed ImpA, subtract from the mapped ImpA then find the % effective ImpA by subwatershed area
    util.log("adding/ calculating Pcnt EIA/ subwatershed")
    arcpy.AddField_management(EIA_final, "Pcnt_EIA", "DOUBLE")
    with arcpy.da.UpdateCursor(EIA_final, ["Pcnt_EIA", greenstreet_new , BMP_new , sumps_new , ecoroof_new , SMF_new , MIA_new ,subwshed_new]) as rows:
        for row in rows:
            row[0] = (row[6]- row[1]+row[2]+row[3]+row[4]+row[5])/row[7]*100
            rows.updateRow(row)

    # convert values in Pcnt EIA field to WHI codes (new field)
    util.log("adding/ calculating WHI scores")
    arcpy.AddField_management(EIA_final, "EIA_score", "DOUBLE")
    with arcpy.da.UpdateCursor(EIA_final, ["Pcnt_EIA", "EIA_score"]) as rows:
        for row in rows:
            row[1] = calc.EIA_score(row[0])
            rows.updateRow(row)

    util.log("Cleaning up")
    arcpy.Delete_management("in_memory")

    util.log("Module complete")

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def streamConn():
    # FOR OPERATOR ---
    # compare total stream lengths to previous years total lengths - see #1.b in documentation
    # contact watershed group managers to update natural bottom culvert list - see #3 in documentation

    util.log("Starting streamConn module")

    # subset streams to piped only
    streams_sub = arcpy.MakeFeatureLayer_management(config.streams,"streams_sub","LINE_TYPE in ('Stormwater Pipe','Stormwater Culvert','Combined Stormwater/Sewer Pipe')")

    # intersect and group subset
    util.log("Prepping stream subset")
    groupby_list = ["WATERSHED"]
    sum_field = "Shape_Length SUM"
    piped_byWshed = config.primary_output + r"\piped_byWshed"
    sumBy(streams_sub, groupby_list, sum_field, piped_byWshed)

    # intersect and group full set
    util.log("Prepping full stream set")
    groupby_list = ["WATERSHED"]
    sum_field = "Shape_Length SUM"
    fullpipe = "in_memory" + r"\fullpiped_byWshed"
    sumBy(config.streams, groupby_list, sum_field, fullpipe)
    old = "SUM_Shape_Length"
    new = 'Full_Length'
    old_new = {old : new}
    fulltemp = config.temp_gdb + r"\fullstreamstemp"
    rename_fields(fullpipe , fulltemp , old_new)

    # append full set stream length to subset
    arcpy.JoinField_management(piped_byWshed,"WATERSHED",fulltemp,"WATERSHED","Full_Length")

    # IF WE NEED TO ADJUST FOR NATURAL BOTTOM CULVERTS HERE IS WHERE IT WOULD HAPPEN - see #3 in documentation

    # create and populate % piped field
    util.log("adding/ calculating Pcnt piped/ subwatershed")
    arcpy.AddField_management(piped_byWshed, "Pcnt_piped", "DOUBLE")
    with arcpy.da.UpdateCursor(piped_byWshed, ["Pcnt_piped", "SUM_Shape_Length","Full_Length"]) as rows:
        for row in rows:
            row[0] = (row[1]/row[2])*100
            rows.updateRow(row)

    # convert values in Pcnt piped field to WHI codes (new field)
    util.log("adding/ calculating WHI scores")
    arcpy.AddField_management(piped_byWshed, "streamConn_score", "DOUBLE")
    with arcpy.da.UpdateCursor(piped_byWshed, ["Pcnt_piped", "streamConn_score"]) as rows:
        for row in rows:
            row[1] = calc.streamCon_score(row[0])
            rows.updateRow(row)

    util.log("Cleaning up")
    arcpy.Delete_management("in_memory")

    util.log("Module complete")

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def treeCanopy():
    util.log("Starting treeCanopy module")

    # test if the "combo" canopy already exists, if not create vectorized canopy version
    if arcpy.Exists(config.canopy_combo_vect) == False:
        util.log("Creating subwatershed/ vegetation raster combo")
        veg_vect = config.canopy_combo_vect
        createVeg_combo(config.subwatersheds, veg_vect)
        # populate WATERSHED field based on codes
        wshedCode_toText(veg_vect)

    #attach Landuse info here - prior to summary/ pivot table work -
    # dissolve DSC data and then intersect with landcover data
    # intersect takes about 30 min
    util.log ("Preparing landuse data and adding to the land cover data")
    dsc_layer = arcpy.MakeFeatureLayer_management(config.mst_dscs,"dsc_layer")
    dsc_city = arcpy.SelectLayerByLocation_management(dsc_layer,"INTERSECT",config.city_bound)
    util.log ("Dissolveing DSCs")
    dsc_diss = arcpy.Dissolve_management(dsc_city,"in_memory" + r"\diss_result","GenEX")
    in_features = [config.canopy_combo_vect,dsc_diss]
    util.log ("Intersecting DSCs and landcover")
    sect_result = arcpy.Intersect_analysis(in_features,"in_memory" + r"\sect_result","NO_FID","","POINT")

    util.log("Creating summary table")
    summary = arcpy.Statistics_analysis(sect_result,config.temp_gdb + r"\canopy_summary_table","Shape_Area SUM", "WATERSHED;gridcode;Landuse")

    util.log("Creating pivot table")
    treeCanopy_final = arcpy.PivotTable_management(summary,"WATERSHED;Landuse","gridcode","SUM_Shape_Area", config.primary_output + r"\treeCanopy_final")

    # create and populate square footage for each landcover type
    sqFoot_calc(treeCanopy_final)

    # need to attach original wshed geometry to get total Shape_Area
    arcpy.JoinField_management(treeCanopy_final,"WATERSHED",config.subwatersheds,"WATERSHED","Shape_Area")

    # Calculate % canopy per subwatershed
    util.log("Calc % vegetation")
    rate_field = "Pcnt_canopy"
    arcpy.AddField_management(treeCanopy_final,rate_field,"Double")
    cursor_fields = ["Built","Low_Med","High",rate_field] # Water is NOT included in final calculation
    with arcpy.da.UpdateCursor(treeCanopy_final,cursor_fields) as rows:
                for row in rows:
                    row[3] = (row[2]/(row[0]+row[1]+row[2]))*100
                    rows.updateRow(row)

    util.log("calc WHI score")
    score_field = "treeCanopy_score"
    arcpy.AddField_management(treeCanopy_final, score_field, "DOUBLE")
    with arcpy.da.UpdateCursor(treeCanopy_final, [rate_field, score_field]) as rows:
        for row in rows:
            row[1] = calc.canopy_scores(row[0])
            rows.updateRow(row)

    util.log("cleanup")
    remove_fields = [field.name for field in arcpy.ListFields(treeCanopy_final,"gridcode*")]
    arcpy.DeleteField_management(treeCanopy_final,remove_fields)

    util.log("Cleaning up")
    arcpy.Delete_management("in_memory")

    util.log("Module complete")

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def floodplainCon():
    # this module is dependent on the combined 100 year and 1996 floodplain
    # if either of these sources changes then the config.floodplain_clip source would need to be updated

    util.log("starting floodplainConn module")

    # test if the "combo" canopy already exists, if not create vectorized canopy version
    if arcpy.Exists(config.canopy_combo_vect) == False:
        util.log("Creating subwatershed/ vegetation raster combo")
        veg_vect = config.canopy_combo_vect
        createVeg_combo(config.subwatersheds, veg_vect)
        # populate WATERSHED field based on codes
        wshedCode_toText(veg_vect)

    util.log("Creating summary table")
    summary = arcpy.Statistics_analysis(floodplain_clip,config.temp_gdb + r"\floodplain_summary_table","Shape_Area SUM", "WATERSHED;gridcode")

    util.log("Creating pivot table")
    floodplainConn_final = arcpy.PivotTable_management(summary,"WATERSHED","gridcode","SUM_Shape_Area", config.primary_output + r"\floodplainCon_final")

    # create and populate square footage for each landcover type
    sqFoot_calc(floodplainConn_final)

    util.log("Calc % vegetation")
    # join back to clipped wshed geometry to get total Shape_Area - DON'T THINK THIS ACTUALLY GETS USED, REMOVE IF NOT
    # arcpy.JoinField_management(floodplainConn_final,"WATERSHED",floodplain_clip,"WATERSHED","Shape_Area")
    rate_field = "Pcnt_canopy"
    arcpy.AddField_management(floodplainConn_final,rate_field,"Double")
    cursor_fields = ["Built","Low_Med","High",rate_field] # Water is NOT included in final calculation
    with arcpy.da.UpdateCursor(floodplainConn_final,cursor_fields) as rows:
                for row in rows:
                    row[3] = (row[1]+row[2])/(row[0]+row[1]+row[2])*100
                    rows.updateRow(row)

    util.log("calc WHI score")
    score_field = "floodplainConn_score"
    arcpy.AddField_management(floodplainConn_final, score_field, "DOUBLE")
    with arcpy.da.UpdateCursor(floodplainConn_final, [rate_field, score_field]) as rows:
        for row in rows:
            row[1] = calc.fpCon_score(row[0])
            rows.updateRow(row)

    util.log("Cleaning up")
    arcpy.Delete_management("in_memory")

    util.log("Module complete")

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def shallowWaterRef():
    util.log("Starting shallowWaterRef module")

    #dissolve EDT reaches into 1 polygon
    reach_diss = arcpy.Dissolve_management(config.EDT_reaches,r"in_memory" + r"\reach_diss","#","#","MULTI_PART","DISSOLVE_LINES")

    util.log("Clipping depth raster to EDT reach extent")
    arcpy.CheckOutExtension("Spatial")
    depth_clip = arcpy.sa.ExtractByMask(config.river_depth,reach_diss)

    #doc at #5 says convert raster to Int but I'll leave it for now

    util.log("Converting depth raster to positive values and adjusting to ordinary low water mark")
    depth_raster = arcpy.sa.Raster(depth_clip)
    lowWater_conversion = 15
    raster_adj = abs(depth_raster)-lowWater_conversion

    # get rid of negative values
    raster_noNeg = arcpy.sa.SetNull(raster_adj<0,raster_adj)

    # reclassify to above and below 20'
    util.log("Reclassifying to above and below 20' depth")
    reclass_mapping = "0 20 0;20 200 1"
    raster_reclass = arcpy.sa.Reclassify(raster_noNeg,"Value", reclass_mapping,"DATA")

    #convert to polygon
    util.log("Conveting raster to polygon")
    shallow_vect = arcpy.RasterToPolygon_conversion(raster_reclass,"in_memory" + r"\veg_vect")

    # intersect with subwatersheds to get their values - not sure if needed as this is all in stream
    # if so do I calc % based on subwateshed total or overall total area? - run on TOTAL AREA per Jen and Chris
    #in_features = [shallow_vect,config.subwatersheds]
    #shallow_sect = arcpy.Intersect_analysis(in_features,"in_memory" + r"\sub_sect","NO_FID")

    #summarize data
    util.log("Creating summary table")
    summary = arcpy.Statistics_analysis(shallow_vect,config.temp_gdb + r"\shallow_summary_table","Shape_Area SUM", "WATERSHED;gridcode")

    #pivot info
    util.log("Creating pivot table")
    ShallowWAter_final = arcpy.PivotTable_management(summary,"WATERSHED","gridcode","SUM_Shape_Area", config.primary_output + r"\ShallowWAter_final")

    # calculate # of total
    util.log("Calc % shallow water")
    rate_field = "Pcnt_Shallow"
    arcpy.AddField_management(access_final,rate_field1,"Double")
    #cursor_fields = ["gridcode", rate_field] # NEED ACTUAL NAMES OF FIELDS DERIVED FROM 'gridcode' AFTER PIVOT
    with arcpy.da.UpdateCursor(ShallowWater_final,cursor_fields) as rows:
                for row in rows:
                    row[2] = row[0]/(row[0] + row[1])
                    rows.updateRow(row)

    # WHI score
    util.log("calc WHI score")
    score_field = "shallow_water_score"
    arcpy.AddField_management(ShallowWAter_final, score_field, "DOUBLE")
    with arcpy.da.UpdateCursor(ShallowWAter_final, [rate_field, score_field]) as rows:
        for row in rows:
            row[1] = calc.shallowWater_score(row[0])
            rows.updateRow(row)

    util.log("Cleaning up")
    arcpy.Delete_management("in_memory")

    util.log("Module complete")

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def streamAccess():
    # major concern with this module: stream accesibily polylines created by SciFiWi are based on older geometry
    # which introduces an inconsistency when comparing "accessible" length to total length
    # Chris Prescott is going to work on updating this source (3/24/2016)

    util.log("Starting streamAccess module")

    # intersect city streams with subwatersheds
    util.log("Intersecting streams with subwatersheds")
    in_features = [config.streams,config.subwatersheds]
    streams_sect = arcpy.Intersect_analysis(in_features,"in_memory" + r"\streams_sect","NO_FID")

    # intersect accessible streams with subwatersheds
    util.log("Intersecting stream accessibility with subwatersheds")
    in_features = [config.stream_access, config.subwatersheds]
    access_sect = arcpy.Intersect_analysis(in_features,config.temp_gdb + r"\access_sect","NO_FID")

    # add field to define access values which more explicitly align with output
    util.log("Adding Status field")
    arcpy.AddField_management(access_sect,"Status","TEXT","","",20)

    # populate Status field values
    util.log("Populating Status field")
    field_list = ["Curr_Acc","Hist_Acc","Status"]
    with arcpy.da.UpdateCursor(access_sect,field_list) as rows:
        for row in rows:
            if row[0] == "n" and row[1] == "":
                row[2] ="Hist_Innacessible"
            elif row[0] == "n" and row[1] == "n":
                row[2] = "Hist_Innacessible"
            elif row[0] == "p":
                row[2] = "Curr_Partial"
            elif row[0] == "y":
                row[2] = "Curr_Full"
            else:
                row[2] = "Unknown"
            rows.updateRow(row)

    #summarize data
    util.log("Creating summary table for streams")
    streams_summary = arcpy.Statistics_analysis(streams_sect,config.temp_gdb + r"\streams_summary_table","Shape_Leng SUM", "WATERSHED")
    arcpy.AddField_management(streams_summary,"WSHED_TOTAL_LEN","DOUBLE")

    input_fields = ["SUM_Shape_Leng","WSHED_TOTAL_LEN"]
    with arcpy.da.UpdateCursor(streams_summary,input_fields) as rows:
        for row in rows:
            row[1] = row[0]
            rows.updateRow(row)

    util.log("Creating summary table for accessible streams")
    access_summary = arcpy.Statistics_analysis(access_sect,config.temp_gdb + r"\access_summary_table","Shape_Leng SUM", "WATERSHED_1;Status")

    # pivot info
    util.log("Creating pivot table")
    access_final = arcpy.PivotTable_management(access_summary, "WATERSHED_1", "Status", "SUM_Shape_Leng", config.primary_output + r"\access_final")

    util.log("Adding Shape Length from city streams")
    arcpy.JoinField_management(access_final,"WATERSHED_1",streams_summary,"WATERSHED","WSHED_TOTAL_LEN")

    # calculate % values
    util.log("Calc % fully accessible")
    rate_field1 = "Pcnt_Full_Access"
    arcpy.AddField_management(access_final,rate_field1,"Double")
    cursor_fields = ["Curr_Full", "Curr_Partial", "Hist_Innacessible","WSHED_TOTAL_LEN", rate_field1]
    with arcpy.da.UpdateCursor(access_final,cursor_fields) as rows:
                for row in rows:
                    row[4] = row[0]/(row[3]-row[2])
                    rows.updateRow(row)

    util.log("Calc % partially accessible")
    rate_field2 = "Pcnt_Partial_Access"
    arcpy.AddField_management(access_final,rate_field2,"Double")
    cursor_fields = ["Curr_Full", "Curr_Partial", "Hist_Innacessible","WSHED_TOTAL_LEN", rate_field2]
    with arcpy.da.UpdateCursor(access_final,cursor_fields) as rows:
                for row in rows:
                    row[4] = row[1]/(row[3]-row[2])
                    rows.updateRow(row)

    # generate WHI scores
    util.log("calc WHI full access score")
    score_field1 = "fully_accessible_score"
    arcpy.AddField_management(access_final, score_field1, "DOUBLE")
    with arcpy.da.UpdateCursor(access_final, [rate_field1, score_field1]) as rows:
        for row in rows:
            row[1] = calc.streamAccess1_count(row[0])
            rows.updateRow(row)

    util.log("calc WHI full and partial access score")
    score_field2 = "all_accessible_score"
    arcpy.AddField_management(access_final, score_field2, "DOUBLE")
    with arcpy.da.UpdateCursor(access_final, [rate_field1, rate_field2, score_field2]) as rows:
        for row in rows:
            row[2] = calc.streamAccess2_count(row[0], row[1])
            rows.updateRow(row)

    util.log("Cleaning up")
    arcpy.Delete_management("in_memory")

    util.log("Module complete")

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def riparianInt():
    util.log("Starting riparianInt module")

    # Find landcover breakdown for riparian buffer - sqft per subwatershed

    buffs = "150;300"

    util.log("Subsetting streams and buffering them")
    streams_sub = arcpy.MakeFeatureLayer_management(config.streams,"streams_sub", "LINE_TYPE = 'Open Channel'")
    streams_clip = arcpy.Clip_analysis(streams_sub, config.city_bound, "in_memory" + "r\streams_clip")
    streams_buff = arcpy.MultipleRingBuffer_analysis(streams_clip, "in_memory" + "r\streams_buff", buffs, "Feet", "Distance", "ALL", "FULL")

    util.log("Subsetting water bodies and buffering them")
    hydro_sub = arcpy.MakeFeatureLayer_management(config.waterbodies,"waterbodies_sub")
    hydro_clip = arcpy.Clip_analysis(hydro_sub, config.city_bound, "in_memory" + "r\hydro_clip")
    hydro_buff = arcpy.MultipleRingBuffer_analysis(hydro_clip, "in_memory" + "r\hydro_buff", buffs, "Feet", "Distance", "ALL", "OUTSIDE_ONLY")

    util.log("Erasing streams buffer where it intersects waterbody buffer")
    # erase streams buffer using waterbodies and their buffer ie waterbodies win
    # create "full" watershed version to use in erase
    hydro_buff_all = arcpy.MultipleRingBuffer_analysis(hydro_clip, "in_memory" + "r\hydro_buff_all", "300", "Feet", "Distance", "ALL", "FULL")
    streams_erase = arcpy.Erase_analysis(streams_buff, hydro_buff_all, "in_memory" + "r\streams_erase")

    # test if the "combo" canopy already exists, if not create vectorized canopy version
    if arcpy.Exists(config.canopy_combo_vect) == False:
        util.log("Creating subwatershed/ vegetation raster combo")
        veg_vect = config.canopy_combo_vect
        createVeg_combo(config.subwatersheds, veg_vect)
        # populate WATERSHED field based on codes
        wshedCode_toText(veg_vect)

    util.log("Intersecting riparian buffers with vectorized landcover")
    sect_result = arcpy.Intersect_analysis([streams_erase,config.canopy_combo_vect],"in_memory" + r"\sect_result","NO_FID","","INPUT")

    #summarize data
    util.log("Creating summary table")
    summary = arcpy.Statistics_analysis(sect_result,config.temp_gdb + r"\riparian_summary_table","Shape_Area SUM", "WATERSHED;gridcode;distance")

    #pivot info
    util.log("Creating pivot table")
    Landcov_final = arcpy.PivotTable_management(summary,"WATERSHED;distance","gridcode","SUM_Shape_Area", config.primary_output + r"\Landcov_final")

    # create and populate square footage for each landcover type
    sqFoot_calc(Landcov_final)

    # Calculate % canopy per subwatershed
    rate_field1 = "Pcnt_Canopy"
    arcpy.AddField_management(Landcov_final,rate_field1,"DOUBLE")
    cursor_fields = ["Built","Low_Med","High",rate_field1]
    with arcpy.da.UpdateCursor(Landcov_final, cursor_fields) as rows:
        for row in rows:
                    row[3] = (row[2]/(row[0]+row[1]+row[2]))*100
                    rows.updateRow(row)


    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    # Find count of stream/ street intersection per subwatershed

    # Subset and intersect the streams and roads - generate points from this
    util.log("Subsetting and intersecting streams/ roads")
    stream_subset = arcpy.MakeFeatureLayer_management(config.streams, "in_memory" + r"\stream_subset", "LINE_TYPE in ( 'Open Channel' , 'Stormwater Culvert' , 'Stormwater Pipe' , 'Water Body' )")
    streets_erase = arcpy.Clip_analysis(config.streets, config.city_bound, "in_memory" + "r\streets_erase")
    crossing_sect = arcpy.Intersect_analysis([stream_subset,streets_erase], "in_memory" + r"\crossing_sect", "NO_FID", "", "POINT")

    # Add Count field and populate with value = 1
    util.log("Adding and Populating Count field")
    arcpy.AddField_management(crossing_sect, "Sect_Count","SHORT")
    with arcpy.da.UpdateCursor(crossing_sect,"Sect_Count") as rows:
                for row in rows:
                    row[0] = 1
                    rows.updateRow(row)

    # Intersect crossings with subwatersheds, group by WATERSHED and get summed count of crossings
    groupby_list = ["WATERSHED"]
    sum_field = "Sect_Count SUM"
    crossing_sumBy = "in_memory" + r"\sect_sumBy"
    sumBy(crossing_sect, groupby_list, sum_field, crossing_sumBy)

    # Convert Crossing info to table?

    # Intersect streams with subwatersheds, group by WATERSHED and get summed area
    util.log("Intersecting streams with subwtwatersheds and grouping length by subwatershed")
    groupby_list = ["WATERSHED"]
    sum_field = "Shape_Length SUM" #VERIFY FIELD NAME
    stream_sumBy = config.temp_gdb + r"\sect_streams"
    sumBy(streams_clip, groupby_list, sum_field, stream_sumBy)

    # Append information into one place
    util.log("Add crossing counts to stream length data")
    arcpy.JoinField_management(stream_sumBy,"WATERSHED",crossing_sumBy,"WATERSHED","SUM_Sect_Count")

    # Calculate # of crossings per kilometer of stream
    util.log("Calculating # of crossings per km of stream")
    rate_field2 = "Crossings_km"
    feet_perKm = 3280.1
    arcpy.AddField_management(stream_sumBy,rate_field2,"DOUBLE")
    cursor_fields = ["SUM_Sect_Count", "SUM_Shape_Length", rate_field2]
    with arcpy.da.UpdateCursor(stream_sumBy,cursor_fields) as rows:
                for row in rows:
                    row[2] = row[0]/(row[1]/feet_perKm)
                    rows.updateRow(row)

    # Combine info from % canopy and # of crossings per kilometer into one place
    util.log("Add % canopy data to crossings per stream km info")
    arcpy.JoinField_management(stream_sumBy,"WATERSHED",Landcov_final,"WATERSHED","Pcnt_Canopy")

    # ZERO OUT ANY NULLS IN DATA

    # WHI score
    util.log("calc WHI score")
    score_field = "riparianInt_score"
    arcpy.AddField_management(stream_sumBy, score_field, "DOUBLE")
    with arcpy.da.UpdateCursor(stream_sumBy, [rate_field1, rate_field2, score_field]) as rows:
        for row in rows:
            row[2] = calc.ripIntegrity_score(row[0], row[1])
            rows.updateRow(row)

    util.log("Cleaning up")
    arcpy.Delete_management("in_memory")

    util.log("Module complete")


if __name__ == '__main__':
    print ("This script is meant to be run as a module")