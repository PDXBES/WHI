#-------------------------------------------------------------------------------
# Name:        WHI_modules
# Purpose:     Primary function set
#
# Author:      DASHNEY
#
# Created:     20/11/2015
# modules to calculate WHI scores
#-------------------------------------------------------------------------------

import arcpy, config, calc, util, os

arcpy.env.overwriteOutput = True


# ancillary functions

def sumBy_intersect(inputFC, sectFC, groupby_list, sum_field, output):
    # intersects two feature classes then dissolves them by specified field and aggregation values
    # groupby_list can be a list of one
    # use _intersect for geometry based summaries (area, length)
    util.log("Aggregating values (sumBy)")
    util.log("   sumBy - intersecting")
    intersect = arcpy.Intersect_analysis([inputFC , sectFC],config.temp_gdb + r"\sect","NO_FID","#","INPUT")
    if arcpy.Exists(output):
        util.log("   deleting existing dissolve result")
        arcpy.Delete_management(output)
    util.log("   sumBy - dissolving")
    arcpy.Dissolve_management(intersect,output,groupby_list,sum_field,"MULTI_PART","DISSOLVE_LINES")

def sumBy_select(inputFC, selectFC, groupby_list, sum_field, output):
    # selects inputFC (centroid) using the location of the selectFC then dissolves them by specified field and aggregation values
    # use _select for pre-filled values (non geometry derived)
    util.log("Aggregating values (sumBy)")
    util.log("   sumBy - selecting")
    #input_layer = arcpy.MakeFeatureLayer_management(inputFC, "in_memory\inputFC")
    sj = arcpy.SpatialJoin_analysis(inputFC, selectFC, config.temp_gdb + r"\sj", "JOIN_ONE_TO_ONE", "KEEP_ALL", "", "HAVE_THEIR_CENTER_IN")
    # selection = arcpy.SelectLayerByLocation_management(input_layer, "HAVE_THEIR_CENTER_IN", selectFC)
    arcpy.Dissolve_management(sj,output,groupby_list,sum_field,"MULTI_PART","DISSOLVE_LINES")

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
    if arcpy.Exists(out_table):
        arcpy.Delete_management(out_table)
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

def createVeg_combo(comparison_fc, output):
    # creates a raster combining the 2007 Metro veg and a specified feature class (for WHI use = the subwatersheds)
    # converts output to vector
    # input 'comparison_fc' = the feature class to be compared - currently assumed to be vector and converted to raster
    # function that calls this uses logic go decide whether to use existing version or rerun ...
    # most likely don't need to rerun unless new veg source is used OR subwatershed bounds change

    # clip landcover to subwatersehds and Reclassify the results (because extra values are added after the clip for some reason (??) )
    util.log("Reclassifying landcover raster")
    arcpy.CheckOutExtension("Spatial")
    # assign questionable, unnecessary values to the main 4 values (built, low veg, high veg, water)
    arcpy.env.workspace = config.temp_gdb
    reclass_mapping = "0 1;1 1;2 2;3 3;4 4;5 4;6 1;7 1;8 1"
    veg_reclass = arcpy.sa.Reclassify(config.canopy,"Value", reclass_mapping,"DATA")

    # convert the comparison feature class to raster
    util.log("Converting comparison feature class to raster")
    arcpy.env.snapRaster = config.canopy
    arcpy.env.extent = "MAXOF"
    Comparison_raster = arcpy.FeatureToRaster_conversion(comparison_fc,"WATERSHED",config.temp_gdb + r"\wshed_toRast","3")
    tempComparison_raster = arcpy.sa.Raster(Comparison_raster)

    # combine landcover and comparison rasters
    util.log("Combining rasters")
    # multiply Comparison raster Value *100 so that the value can be parsed with the vegetation value
    # adding rasters results in NoData where there is not a value from BOTH therefore this step also serves to clip the raster to the subwatersheds
    combo = veg_reclass + (tempComparison_raster*100)
    combo.save(config.temp_gdb + r"\raster_combo")
    arcpy.CheckInExtension("Spatial")

    util.log("Converting the combo to vector and clipping")
    util.log("- converting")
    veg_vect = arcpy.RasterToPolygon_conversion(combo, config.canopy_combo_vect)

    # convert watershed code (int) to text
    # this takes almost an hour to run - why?
    util.log("Adding and populating WATERSHED field")
    arcpy.AddField_management(veg_vect,"WATERSHED","TEXT",'','',20)
    with arcpy.da.UpdateCursor(veg_vect, ["gridcode","WATERSHED"]) as rows:
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

    util.log("Repairing geometry")
    arcpy.RepairGeometry_management(veg_vect)
    arcpy.RepairGeometry_management(veg_vect)

def sqFoot_calc(input):
    # fills the square footage values for each type of land cover
    # uses fields that get deleted later therefore may be hard to debug (or understand what its doing)

    util.log("Adding the sqft field for each type of land cover")
    for key, value in config.vegtype_dict.iteritems():
        arcpy.AddField_management(input,value,"Double")
    util.log("Populating the main landcover sqft fields")
    for key, value in config.wshed_dict.iteritems():
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
    # Effective Impervious Area

    # !!! Q - clip all managed ImpA (coming from geometry) to mapped ImpA?  - if not might extend beyond mapped

    arcpy.env.overwriteOutput = True

    util.log("Starting EIA module")
    print arcpy.Exists(config.OSSMA)

    #subset inputs
    gs_layer = arcpy.MakeFeatureLayer_management(config.collection_lines,"gs_layer","UNITTYPE = 'CHGRSTFAC'")
    green_streets = arcpy.CopyFeatures_management(gs_layer, config.temp_gdb + r"\green_streets")
    ponds_swales = arcpy.MakeFeatureLayer_management(config.BMP_drainage,"ponds_swales","Gen_Type in ( 'CHANNEL - WATER QUALITY SWALE' , 'Detention Pond - Dry' , 'Detention Pond - Wet' , 'POND' , 'Swale' )")
    sumps =  arcpy.MakeFeatureLayer_management(config.BES_UIC,"sumps","opsStatus = 'AC'")
    private_SMF = arcpy.Copy_management(config.privateSMF, config.temp_gdb + r"\private_SMF")

    # create mapped ImpA by subwatershed
    util.log("Creating mapped ImpA")
    print arcpy.Exists(config.OSSMA)
    # intersect bonks on multipart
    util.log("...converting multipart ImpA to singlepart")
    ImpA_single = arcpy.MultipartToSinglepart_management(config.ImpA, "in_memory\ImpA_single")
    util.log("...clipping ImpA to city boundary")
    ImpA_cityclip = arcpy.Clip_analysis(ImpA_single,config.city_bound, "in_memory" + r"\ImpA_cityclip")
    ImpA_output = "in_memory" + r"\ImpA_diss"
    groupby_list = ["WATERSHED"]
    sum_field = "Shape_Area SUM"
    sumBy_intersect(ImpA_cityclip, config.subwatersheds, groupby_list, sum_field, ImpA_output)

    MIA_old = "SUM_Shape_Area"
    MIA_new = 'MIA_Area'
    old_new = {MIA_old : MIA_new}
    MIA_output_new = config.temp_gdb + r"\MIA"
    rename_fields(ImpA_output, MIA_output_new ,old_new)

    # create managed ImpA by subwatershed - for each input
    util.log("Creating managed ImpA ...")
    print arcpy.Exists(config.OSSMA)

    util.log("... green street piece")
    print arcpy.Exists(config.OSSMA)
    # uses global, assumed  value of 3500 sqft
    aa_field = "assumed_area"
    arcpy.AddField_management(green_streets, aa_field, "LONG")
    with arcpy.da.UpdateCursor(green_streets, aa_field) as rows:
        for row in rows:
            row[0] = 3500
            rows.updateRow(row)
    groupby_list = ["WATERSHED"]
    sum_field = "assumed_area SUM"
    gs_output = config.temp_gdb + r"\gs_diss"
    sumBy_select(green_streets,config.subwatersheds,groupby_list,sum_field,gs_output)
    greenstreet_old = "SUM_assumed_area"
    greenstreet_new = 'GreenStreet_Area'
    old_new = {greenstreet_old:greenstreet_new}
    gs_output_new = config.temp_gdb + r"\greenstreets"
    rename_fields(gs_output,gs_output_new , old_new)

    util.log("... BMP managed ImpA piece")
    print arcpy.Exists(config.OSSMA)
    # clip delineations to the mapped impervious area (which is already clipped to the city boundary)
    util.log("clipping BMP basins to ImpA bounds")
    BMP_ImpAclip = arcpy.Clip_analysis(ponds_swales,ImpA_cityclip, "in_memory" + r"\BMP_ImpAclip")

    BMP_output = "in_memory" + r"\bmp_diss"
    groupby_list = ["WATERSHED"]
    sum_field = "Shape_Area SUM"
    sumBy_intersect(BMP_ImpAclip, config.subwatersheds, groupby_list, sum_field, BMP_output)

    util.log("... renaming field")
    BMP_old = "SUM_Shape_Area"
    BMP_new = 'BMP_Area'
    old_new = {BMP_old : BMP_new}
    BMP_output_new = config.temp_gdb + r"\BMP"
    rename_fields(BMP_output , BMP_output_new , old_new)

    util.log("... sumped area piece")
    print arcpy.Exists(config.OSSMA)
    # clip delineations to the mapped impervious area (which is already clipped to the city boundary)
    util.log("clipping sump basins to ImpA bounds")
    sump_clip = arcpy.Clip_analysis(config.sump_delin, ImpA_cityclip, "in_memory" + r"\sump_ImpAclip")

    sump_output = "in_memory" + r"\sump_diss"
    groupby_list = ["WATERSHED"]
    sum_field = "Shape_Area SUM"
    sumBy_intersect(sump_clip, config.subwatersheds,groupby_list,sum_field, sump_output)
    sumps_old = "SUM_Shape_Area"
    sumps_new = 'Sump_Area'
    old_new = {sumps_old : sumps_new}
    sump_output_new = config.temp_gdb + r"\sumps"
    rename_fields(sump_output , sump_output_new , old_new)

    util.log("... ecoroofs piece")
    print arcpy.Exists(config.OSSMA)
    roof_output = "in_memory" + r"\roof_diss"
    groupby_list = ["WATERSHED"]
    sum_field = "SQ_FOOT SUM"
    sumBy_select(config.ecoroof_pnt,config.subwatersheds,groupby_list,sum_field,roof_output)
    ecoroof_old = "SUM_SQ_FOOT"
    ecoroof_new = 'Ecoroof_Area'
    old_new = {ecoroof_old : ecoroof_new}
    roof_output_new = config.temp_gdb + r"\ecoroof"
    rename_fields(roof_output , roof_output_new , old_new)

# ----------------------- QC
    util.log("... private SMF piece")
    print arcpy.Exists(config.OSSMA)
    # intersect OSSMA and ImpA
    ossma_impa_sect = arcpy.Intersect_analysis([config.OSSMA , config.ImpA],config.temp_gdb + r"\ossma_impa_sect","NO_FID","#","INPUT")
    # add and calc field: reduced_ImpA = OSSMA.final_red * ShapeArea
    arcpy.AddField_management(ossma_impa_sect, "reduced_ImpA", "DOUBLE")
    with arcpy.da.UpdateCursor(ossma_impa_sect, ["Final_Red", "Shape_Area", "reduced_ImpA"]) as cursor:
        for row in cursor:
            if row[0] != None:
                row[2] = (row[0]/100)*row[1] # reduce impA if there is a final reduction value
            else:
                row[2] = row[1] # if no final reduction value then use original impA
            cursor.updateRow(row)
    # run sumBy to sum reduced_ImpA area to the watershed
    util.log("Summing watershed area values")
    smf_output = config.temp_gdb + r"\smf_diss"
    groupby_list = ["WATERSHED"]
    sum_field = "assumed_value SUM"
    sumBy_select(ossma_impa_sect, config.subwatersheds, groupby_list, sum_field, smf_output)
    # rename sum field and set result = to EIA_final - all other values will be appended to this fc
    util.log("Renaming fields")
    SMF_old = "SUM_assumed_value"
    SMF_new = 'SMF_Area'
    old_new = {SMF_old : SMF_new}
    EIA_final = config.temp_gdb + r"\EIA_final"
    rename_fields(smf_output , EIA_final , old_new)
# ----------------------- QC

    sum_field = 'Shape_Area'
    subwshed_new = 'Subwshed_Area'
    old_new = {sum_field : subwshed_new}
    new_subwsheds = "in_memory" + r"\subwatersheds"
    rename_fields(config.subwatersheds, new_subwsheds ,old_new)

    # combine area fields into one location for calculation
    util.log("Adding area fields to the private SMF output")
    arcpy.Exists(config.OSSMA)
    join_field = "WATERSHED"
    arcpy.JoinField_management(EIA_final,join_field,gs_output_new,join_field,greenstreet_new)
    arcpy.JoinField_management(EIA_final,join_field,BMP_output_new,join_field,BMP_new)
    arcpy.JoinField_management(EIA_final,join_field,sump_output_new,join_field,sumps_new)
    arcpy.JoinField_management(EIA_final,join_field,roof_output_new,join_field,ecoroof_new)
    arcpy.JoinField_management(EIA_final,join_field,MIA_output_new,join_field,MIA_new)
    arcpy.JoinField_management(EIA_final,join_field,new_subwsheds,join_field,subwshed_new)

    # calc all numeric field Null values to 0 so that fields calculate correctly (calcs bonk with Nulls)
    util.log("Finding and calculating all Null values to 0")
    NullNumber_toZero(EIA_final)

    # sum the managed ImpA, subtract from the mapped ImpA then find the % effective ImpA by subwatershed area
    util.log("Adding/ calculating Pcnt EIA/ subwatershed")
    arcpy.AddField_management(EIA_final, "Pcnt_EIA", "DOUBLE")
    with arcpy.da.UpdateCursor(EIA_final, ["Pcnt_EIA", greenstreet_new , BMP_new , sumps_new , ecoroof_new , SMF_new , MIA_new ,subwshed_new]) as rows:
        for row in rows:
            row[0] = (row[6]- (row[1]+row[2]+row[3]+row[4]+row[5]))/row[7]*100
            rows.updateRow(row)

    # convert values in Pcnt EIA field to WHI codes (new field)
    util.log("Adding/ calculating WHI scores")
    arcpy.AddField_management(EIA_final, "EIA_score", "DOUBLE")
    with arcpy.da.UpdateCursor(EIA_final, ["Pcnt_EIA", "EIA_score"]) as rows:
        for row in rows:
            row[1] = calc.EIA_score(row[0])
            rows.updateRow(row)

    util.log("Cleaning up")
    arcpy.Delete_management("in_memory")

    # convert output to table
    util.tableTo_primaryOutput(EIA_final)

    util.log("Module complete ---------------------------------------------------------------")

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def streamConn():
    # FOR OPERATOR ---
    # compare total stream lengths to previous years total lengths - see #1.b in documentation
    # contact watershed group managers to update natural bottom culvert list - see #3 in documentation

    util.log("Starting streamConn module")

    # subset streams to piped only
    streams_sub = arcpy.MakeFeatureLayer_management(config.streams,"streams_sub","LINE_TYPE in ('Stormwater Pipe','Stormwater Culvert','Combined Stormwater/Sewer Pipe')")

    # intersect and group stream subset by subwatershed
    util.log("Prepping stream subset")
    groupby_list = ["WATERSHED"]
    sum_field = "Shape_Length SUM"
    piped_byWshed = config.temp_gdb + r"\streamConn_final"
    sumBy_intersect(streams_sub, config.subwatersheds, groupby_list, sum_field, piped_byWshed)

    # intersect and group full set
    util.log("Prepping full stream set")
    groupby_list = ["WATERSHED"]
    sum_field = "Shape_Length SUM"
    fullpipe = "in_memory" + r"\fullpiped_byWshed"
    sumBy_intersect(config.streams, config.subwatersheds,groupby_list, sum_field, fullpipe)
    old = "SUM_Shape_Length"
    new = 'Full_Length'
    old_new = {old : new}
    fulltemp = config.temp_gdb + r"\fullstreamstemp"
    rename_fields(fullpipe , fulltemp , old_new)

    # append full set stream length to subset
    arcpy.JoinField_management(piped_byWshed,"WATERSHED",fulltemp,"WATERSHED","Full_Length")

    # IF WE NEED TO ADJUST FOR NATURAL BOTTOM CULVERTS HERE IS WHERE IT WOULD HAPPEN - see #3 in documentation
    # JEN to create polygons which tells us where the natural bottom culverts are

    # create and populate % piped field
    util.log("Adding/ calculating Pcnt piped/ subwatershed")
    arcpy.AddField_management(piped_byWshed, "Pcnt_piped", "DOUBLE")
    with arcpy.da.UpdateCursor(piped_byWshed, ["Pcnt_piped", "SUM_Shape_Length","Full_Length"]) as rows:
        for row in rows:
            row[0] = (row[1]/row[2])*100
            rows.updateRow(row)

    # convert values in Pcnt piped field to WHI codes (new field)
    util.log("Adding/ calculating WHI scores")
    arcpy.AddField_management(piped_byWshed, "streamConn_score", "DOUBLE")
    with arcpy.da.UpdateCursor(piped_byWshed, ["Pcnt_piped", "streamConn_score"]) as rows:
        for row in rows:
            row[1] = calc.streamCon_score(row[0])
            rows.updateRow(row)

    util.tableTo_primaryOutput(piped_byWshed)
    util.log("Module complete ---------------------------------------------------------------")


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def treeCanopy():
    util.log("Starting treeCanopy module")

    # test if the "combo" canopy already exists, if not create vectorized canopy version
    veg_vect = config.canopy_combo_vect
    if arcpy.Exists(config.canopy_combo_vect) == False:
        util.log("Creating subwatershed/ vegetation raster combo")
        createVeg_combo(config.subwatersheds, veg_vect)

    # attach Landuse info here - prior to summary/ pivot table work -
    # dissolve DSC data and then intersect with landcover data
    # intersect takes about 30 min
    util.log ("Preparing landuse data and adding to the land cover data")
    dsc_layer = arcpy.MakeFeatureLayer_management(config.mst_dscs,"dsc_layer")
    dsc_select = arcpy.SelectLayerByLocation_management(dsc_layer,"INTERSECT",config.city_bound)
    dsc_city = arcpy.CopyFeatures_management(dsc_select, config.temp_gdb + r"\dsc_city")

    util.log("Unioning DSCs with City Boundary")
    in_features = [dsc_city, config.city_bound]
    city_union = arcpy.Union_analysis(in_features,config.temp_gdb + r"\city_union","NO_FID","","GAPS")
    util.log("Filling non DSC area with 'NONE' value")
    with arcpy.da.UpdateCursor(city_union, ["GenEX"]) as rows:
        for row in rows:
            if row[0] == "":
                row[0] = "NONE"
            elif row[0] is None:
                row[0] = "NONE"
            rows.updateRow(row)

    arcpy.RepairGeometry_management(city_union)
    arcpy.RepairGeometry_management(city_union)

    # chop up the canopy and intersect with the DSCs to get the zoning attached
    sect_result = util.fishnetChop(city_union)

    util.log("Creating summary table")
    summary = arcpy.Statistics_analysis(sect_result,config.temp_gdb + r"\canopy_summary_table","Shape_Area SUM", "WATERSHED;gridcode;GenEX")

    util.log("Creating pivot table")
    treeCanopy = arcpy.PivotTable_management(summary,"WATERSHED;GenEX","gridcode","SUM_Shape_Area", config.temp_gdb + r"\treeCanopy")

    # create and populate square footage for each landcover type
    sqFoot_calc(treeCanopy)

    # need to attach original wshed geometry to get total Shape_Area
    arcpy.JoinField_management(treeCanopy,"WATERSHED",config.subwatersheds,"WATERSHED","Shape_Area")

    # Calculate % canopy per subwatershed - this is for the result broken out by zoning
    util.log("Calc % vegetation")
    rate_field = "Pcnt_canopy"
    arcpy.AddField_management(treeCanopy,rate_field,"Double")
    cursor_fields = ["Built","Low_Med","High",rate_field] # Water is NOT included in final calculation
    with arcpy.da.UpdateCursor(treeCanopy,cursor_fields) as rows:
                for row in rows:
                    row[3] = (row[2]/(row[0]+row[1]+row[2]))*100
                    rows.updateRow(row)

    util.log("Cleanup")
    remove_fields = [field.name for field in arcpy.ListFields(treeCanopy,"gridcode*")]
    arcpy.DeleteField_management(treeCanopy,remove_fields)

    # group result by subwatershed
    treeCanopy_final = arcpy.Statistics_analysis(treeCanopy,config.primary_output + r"\treeCanopy_final","Built SUM; Low_Med SUM; High SUM", "WATERSHED")

    # Calculate % canopy per subwatershed
    util.log("Calc % vegetation")
    rate_field = "Pcnt_canopy"
    arcpy.AddField_management(treeCanopy_final,rate_field,"Double")
    cursor_fields = ["SUM_Built","SUM_Low_Med","SUM_High",rate_field] # Water is NOT included in final calculation
    with arcpy.da.UpdateCursor(treeCanopy_final,cursor_fields) as rows:
                for row in rows:
                    row[3] = (row[2]/(row[0]+row[1]+row[2]))*100
                    rows.updateRow(row)

    util.log("Calc WHI score")
    score_field = "treeCanopy_score"
    arcpy.AddField_management(treeCanopy_final, score_field, "DOUBLE")
    with arcpy.da.UpdateCursor(treeCanopy_final, [rate_field, score_field]) as rows:
        for row in rows:
            row[1] = calc.canopy_scores(row[0])
            rows.updateRow(row)

    util.log("Cleaning up")
    arcpy.Delete_management("in_memory")

    util.log("Module complete ---------------------------------------------------------------")

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def floodplainCon():
    # this module is dependent on the combined 100 year and 1996 floodplain to create config.floodplain_clip
    # if either of these sources were to change then the config.floodplain_clip source would need to be updated

    util.log("Starting floodplainConn module")

##    # test if the "combo" canopy already exists, if not create vectorized canopy version
##    veg_vect = config.canopy_combo_vect
##    if arcpy.Exists(config.canopy_combo_vect) == False:
##        util.log("Creating subwatershed/ vegetation raster combo")
##        createVeg_combo(config.subwatersheds, veg_vect)
##
##    # clip landcover with floodplain area
##    util.log("Clipping landcover to floodplain area")
##    floodplain_clip = arcpy.Clip_analysis(veg_vect, config.floodplain_clip, config.temp_gdb + r"\floodplain_clip")
##
##    util.log("Creating summary table")
##    summary = arcpy.Statistics_analysis(floodplain_clip,config.temp_gdb + r"\floodplain_summary_table","Shape_Area SUM", "WATERSHED;gridcode")
##
##    util.log("Creating pivot table")
##    floodplainConn_final = arcpy.PivotTable_management(summary,"WATERSHED","gridcode","SUM_Shape_Area", config.temp_gdb + r"\floodplainCon_final")
##
##    # create and populate square footage for each landcover type
##    sqFoot_calc(floodplainConn_final)
##
##    util.log("Calc % vegetation")
##    rate_field = "Pcnt_canopy"
##    arcpy.AddField_management(floodplainConn_final,rate_field,"Double")
##    cursor_fields = ["Built","Low_Med","High",rate_field] # Water is NOT included in final calculation
##    with arcpy.da.UpdateCursor(floodplainConn_final,cursor_fields) as rows:
##                for row in rows:
##                    row[3] = (row[1]+row[2])/(row[0]+row[1]+row[2])*100
##                    rows.updateRow(row)

    util.log("Clip impervious area to floodplain")
    ImpA_floodplain_clip = arcpy.Clip_analysis(config.ImpA, config.floodplain_clip, config.temp_gdb + r"\ImpA_floodplain_clip")

    util.log("Find area of floodplain per watershed")
    floodplain_sumBy = config.temp_gdb + r"\floodplain_sumBy"
    groupby_list = ["WATERSHED"]
    sum_field = "Shape_Area SUM"
    sumBy_intersect(config.floodplain_clip, config.subwatersheds, groupby_list, sum_field, floodplain_sumBy)
    # rename "SUM_Shape_Area" to "Total_Floodplain_Area"
    old_name = "SUM_Shape_Area"
    new_name = "Total_Floodplain_Area"
    old_new = {old_name : new_name}
    floodplain_sumBy_rename = config.temp_gdb + r"\floodplain_sumBy_rename"
    rename_fields(floodplain_sumBy, floodplain_sumBy_rename ,old_new)

    util.log("Find area of floodplain impervious per watershed")
    floodplainConn_final = config.temp_gdb + r"\floodplainConn_final"
    groupby_list = ["WATERSHED"]
    sum_field = "Shape_Area SUM"
    sumBy_intersect(ImpA_floodplain_clip, config.subwatersheds, groupby_list, sum_field, floodplainConn_final)
    # rename "SUM_Shape_Area" to "Floodplain_Impervious_Area"
    old_name = "SUM_Shape_Area"
    new_name = "Floodplain_Impervious_Area"
    old_new = {old_name : new_name}
    floodplainConn_final_rename = config.temp_gdb + r"\floodplainConn_final_rename"
    rename_fields(floodplain_sumBy, floodplainConn_final_rename ,old_new)

    # append floodplain area from floodplain_sumBy to floodplainConn_final  *********
    arcpy.JoinField_management(floodplainConn_final_rename, "WATERSHED", floodplain_sumBy, "WATERSHED", ["Total_Floodplain_Area"])

    util.log("Calc % impervious of the floodplain")
    rate_field = "Pcnt_ImpA"
    arcpy.AddField_management(floodplainConn_final_rename, rate_field, "Double")
    cursor_fields = ["Floodplain_Impervious_Area", "Total_Floodplain_Area", rate_field]
    with arcpy.da.UpdateCursor(floodplainConn_final_rename, cursor_fields) as cursor:
        for row in cursor:
            row[2] = (row[0]/row[1])*100
            cursor.updateRow(row)

    util.log("Calc WHI score")
    score_field = "floodplainConn_score"
    arcpy.AddField_management(floodplainConn_final_rename, score_field, "DOUBLE")

    with arcpy.da.UpdateCursor(floodplainConn_final_rename, [rate_field, score_field]) as rows:
        for row in rows:
            row[1] = calc.fpCon_score(row[0])
            rows.updateRow(row)

    util.log("Cleaning up")
    arcpy.Delete_management("in_memory")

    # convert output to table if needed
    util.tableTo_primaryOutput(floodplainConn_final_rename)

    util.log("Module complete ---------------------------------------------------------------")

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def shallowWaterRef():
    util.log("Starting shallowWaterRef module")

    #dissolve EDT reaches into 1 polygon
    reach_diss = arcpy.Dissolve_management(config.EDT_reaches,r"in_memory" + r"\reach_diss","#","#","MULTI_PART","DISSOLVE_LINES")

    util.log("Clipping depth raster to EDT reach extent")
    arcpy.CheckOutExtension("Spatial")
    depth_clip = arcpy.Clip_management(config.river_depth,"#",config.temp_gdb + r"\depth_clip",reach_diss,"-3.402823e+038","ClippingGeometry","NO_MAINTAIN_EXTENT")

    util.log("Converting depth raster to positive values and adjusting to ordinary low water mark")
    depth_raster = arcpy.sa.Raster(depth_clip)
    lowWater_conversion = 15
    raster_adj = abs(depth_raster)-lowWater_conversion

    # get rid of negative values
    raster_noNeg = arcpy.sa.SetNull(raster_adj<0,raster_adj)

    # reclassify to above and below 20'
    util.log("Reclassifying to above and below 20' depth")
    # 0-20' set to 0, > 20' set to 1
    reclass_mapping = "0 20 0;20 200 1"
    raster_reclass = arcpy.sa.Reclassify(raster_noNeg,"Value", reclass_mapping,"DATA")

    #convert to polygon
    util.log("Conveting raster to polygon")
    shallow_vect = arcpy.RasterToPolygon_conversion(raster_reclass,config.temp_gdb + r"\shallow_vect")

    #summarize data
    util.log("Creating summary table")
    summary = arcpy.Statistics_analysis(shallow_vect,config.temp_gdb + r"\shallow_summary_table","Shape_Area SUM", "gridcode")

    #pivot info
    util.log("Creating pivot table")
    arcpy.AddField_management(summary,"input_field","SHORT")
    with arcpy.da.UpdateCursor(summary,"input_field") as rows:
        for row in rows:
            row[0] = 100
            rows.updateRow(row)
    ShallowWater_final = arcpy.PivotTable_management(summary,"input_field","gridcode","SUM_Shape_Area", config.temp_gdb + r"\ShallowWater_final")

    # calculate # of total
    util.log("Calc % shallow water")
    rate_field = "Pcnt_Shallow"
    arcpy.AddField_management(ShallowWater_final,rate_field,"Double")
    cursor_fields = ["gridcode0", "gridcode1", rate_field]
    with arcpy.da.UpdateCursor(ShallowWater_final,cursor_fields) as rows:
                for row in rows:
                    row[2] = (row[0]/(row[0] + row[1]))*100
                    rows.updateRow(row)

    # WHI score
    util.log("Calc WHI score")
    score_field = "shallow_water_score"
    arcpy.AddField_management(ShallowWater_final, score_field, "DOUBLE")
    with arcpy.da.UpdateCursor(ShallowWater_final, [rate_field, score_field]) as rows:
        for row in rows:
            row[1] = calc.shallowWater_score(row[0])
            rows.updateRow(row)

    util.log("Cleaning up")
    arcpy.Delete_management("in_memory")

    # convert output to table if needed
    util.tableTo_primaryOutput(ShallowWater_final)

    util.log("Module complete ---------------------------------------------------------------")

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def streamAccess():

    util.log("Starting streamAccess module")

    # clip access polygons to subwatersheds
    util.log("Clipping access polygons to subwatersheds")
    accesspoly_clip = arcpy.Clip_analysis(config.stream_access_poly, config.subwatersheds, config.temp_gdb + r"\accesspoly_clip")

    # intersect city streams with subwatersheds
    util.log("Intersecting streams with subwatersheds")
    in_features = [config.streams,config.subwatersheds]
    streams_sect = arcpy.Intersect_analysis(in_features, config.temp_gdb + r"\streams_sect","NO_FID")

    #intersect city streams with accessiblity polygons
    util.log("Intersecting city streams with accessibility polygons")
    in_features = [streams_sect, accesspoly_clip]
    accesspoly_sect = arcpy.Intersect_analysis(in_features, config.temp_gdb + r"\accesspoly_sect","NO_FID","#","LINE")

    # intersect accessible streams with subwatersheds
    util.log("Intersecting stream accessibility with subwatersheds")
    in_features = [accesspoly_sect, config.subwatersheds]
    access_sect = arcpy.Intersect_analysis(in_features,config.temp_gdb + r"\access_sect","NO_FID")

    # add field to define access values which more explicitly align with output
    util.log("Adding streamAccess_Status field")
    arcpy.AddField_management(access_sect,"streamAccess_Status","TEXT","","",20)

    # populate streamAccess_Status field values
    util.log("Populating streamAccess_Status field")
    field_list = ["Curr_Acc","Hist_Acc","streamAccess_Status"]
    with arcpy.da.UpdateCursor(access_sect,field_list) as rows:
        for row in rows:
            if row[0] is None and row[1] == "n":
                row[2] ="Hist_Innacessible"
            elif row[0] == "n" and row[1] == "n":
                row[2] = "Hist_Innacessible"
            elif row[0] == "n" and row[1] == "y":
                row[2] = "Hist_Accessible"
            elif row[0] == "p":
                row[2] = "Curr_Partial"
            elif row[0] == "y":
                row[2] = "Curr_Full"
            else:
                row[2] = "Unknown"
            rows.updateRow(row)

    #summarize data
    util.log("Creating summary table for all streams")
    streams_summary = arcpy.Statistics_analysis(streams_sect,config.temp_gdb + r"\streams_summary_table","Shape_Length SUM", "WATERSHED")
    arcpy.AddField_management(streams_summary,"WSHED_TOTAL_LEN","DOUBLE")

    input_fields = ["SUM_Shape_Length","WSHED_TOTAL_LEN"]
    with arcpy.da.UpdateCursor(streams_summary,input_fields) as rows:
        for row in rows:
            row[1] = row[0]
            rows.updateRow(row)

    util.log("Creating summary table for accessible streams")
    access_summary = arcpy.Statistics_analysis(access_sect,config.temp_gdb + r"\access_summary_table","Shape_Length SUM", "WATERSHED;streamAccess_Status")

    # pivot info
    util.log("Creating pivot table")
    access_final = arcpy.PivotTable_management(access_summary, "WATERSHED", "streamAccess_Status", "SUM_Shape_Length", config.temp_gdb + r"\access_final")

    util.log("Adding Shape Length from city streams")
    arcpy.JoinField_management(access_final,"WATERSHED",streams_summary,"WATERSHED","WSHED_TOTAL_LEN")

    # calculate % values
    util.log("Calc % fully accessible")
    rate_field1 = "Pcnt_Full_Access"
    arcpy.AddField_management(access_final,rate_field1,"Double")
    cursor_fields = ["Curr_Full", "Curr_Partial", "WSHED_TOTAL_LEN", rate_field1]
    with arcpy.da.UpdateCursor(access_final,cursor_fields) as rows:
                for row in rows:
                    row[3] = (row[0]/row[2])*100
                    rows.updateRow(row)

    util.log("Calc % partially accessible")
    rate_field2 = "Pcnt_Partial_Access"
    arcpy.AddField_management(access_final,rate_field2,"Double")
    cursor_fields = ["Curr_Full", "Curr_Partial", "WSHED_TOTAL_LEN", rate_field2]
    with arcpy.da.UpdateCursor(access_final,cursor_fields) as rows:
                for row in rows:
                    row[3] = (row[1]/row[2])*100
                    rows.updateRow(row)

    # generate WHI scores
    util.log("Calc WHI full access score")
    score_field1 = "fully_accessible_score"
    arcpy.AddField_management(access_final, score_field1, "DOUBLE")
    with arcpy.da.UpdateCursor(access_final, [rate_field1, score_field1]) as rows:
        for row in rows:
            row[1] = calc.streamAccess1_count(row[0])
            rows.updateRow(row)

    util.log("Calc WHI full and partial access score")
    score_field2 = "all_accessible_score"
    arcpy.AddField_management(access_final, score_field2, "DOUBLE")
    with arcpy.da.UpdateCursor(access_final, [rate_field1, rate_field2, score_field2]) as rows:
        for row in rows:
            row[2] = calc.streamAccess2_count(row[0], row[1])
            rows.updateRow(row)

    util.log("Cleaning up")
    arcpy.Delete_management("in_memory")

    # convert output to table if needed
    util.tableTo_primaryOutput(access_final)

    util.log("Module complete ---------------------------------------------------------------")

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def riparianInt():
    # Find landcover breakdown for riparian buffer - sqft per subwatershed
    util.log("Starting riparianInt module")

    buffs = "150;300"

    util.log("Subsetting streams and buffering them")
    streams_sub = arcpy.MakeFeatureLayer_management(config.streams,"streams_sub", "LINE_TYPE = 'Open Channel'")
    streams_clip = arcpy.Clip_analysis(streams_sub, config.city_bound, r"in_memory\streams_clip")
    streams_buff = arcpy.MultipleRingBuffer_analysis(streams_clip, r"in_memory\streams_buff", buffs, "Feet", "Distance", "NONE", "FULL")
    streams_buff_dissolve = arcpy.Dissolve_management(streams_buff, r"in_memory\streams_buff_dissolve", "Distance")

    util.log("Subsetting water bodies and buffering them")
    hydro_sub = arcpy.MakeFeatureLayer_management(config.waterbodies,"waterbodies_sub")
    hydro_clip = arcpy.Clip_analysis(hydro_sub, config.city_bound, r"in_memory\hydro_clip")
    hydro_buff = arcpy.MultipleRingBuffer_analysis(hydro_clip, r"in_memory\hydro_buff", buffs, "Feet", "Distance", "ALL", "OUTSIDE_ONLY")

    util.log("Erasing streams buffer where it intersects waterbody buffer")
    # erase streams buffer using waterbodies and their buffer ie waterbodies win
    # create "full" watershed version to use in erase
    hydro_buff_all = arcpy.MultipleRingBuffer_analysis(hydro_clip, r"in_memory\hydro_buff_all", "300", "Feet", "Distance", "ALL", "FULL")
    streams_erase = arcpy.Erase_analysis(streams_buff_dissolve, hydro_buff_all, r"in_memory\streams_erase")

    # test if the "combo" canopy already exists, if not create vectorized canopy version
    veg_vect = config.canopy_combo_vect
    if arcpy.Exists(config.canopy_combo_vect) == False:
        util.log("Creating subwatershed/ vegetation raster combo")
        createVeg_combo(config.subwatersheds, veg_vect)

    sect_result = util.fishnetChop(streams_erase)

    #summarize data
    util.log("Creating summary table")
    summary = arcpy.Statistics_analysis(sect_result,config.temp_gdb + r"\riparian_summary_table","Shape_Area SUM", "WATERSHED;gridcode;distance")

    #pivot info
    util.log("Creating pivot table")
    Landcov_final = arcpy.PivotTable_management(summary,"WATERSHED;distance","gridcode","SUM_Shape_Area", config.temp_gdb + r"\Landcov_final")

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
    streets_erase = arcpy.Clip_analysis(config.streets, config.city_bound, "in_memory" + r"\streets_erase")
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
    sumBy_select(crossing_sect, config.subwatersheds,groupby_list, sum_field, crossing_sumBy)

    # Intersect streams with subwatersheds, group by WATERSHED and get summed area
    util.log("Intersecting streams with subwtwatersheds and grouping length by subwatershed")
    groupby_list = ["WATERSHED"]
    sum_field = "Shape_Length SUM"
    stream_sumBy = config.temp_gdb + r"\riparianInt_final"
    sumBy_intersect(streams_clip,config.subwatersheds, groupby_list, sum_field, stream_sumBy)

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

    # WHI score
    util.log("Calc WHI score")
    score_field = "riparianInt_score"
    arcpy.AddField_management(stream_sumBy, score_field, "DOUBLE")
    with arcpy.da.UpdateCursor(stream_sumBy, [rate_field1, rate_field2, score_field]) as rows:
        for row in rows:
            row[2] = calc.ripIntegrity_score(row[0], row[1])
            rows.updateRow(row)

    util.log("Cleaning up")
    arcpy.Delete_management("in_memory")

    # convert output to table if needed
    util.tableTo_primaryOutput(stream_sumBy)

    util.log("Module complete ---------------------------------------------------------------")

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def subwshed_Attach():
    # attach WHI figs to subwatershed geometry
    util.log("Starting subwshed_Attach module")

    util.log("Copying subwatersheds to output gdb")
    final_subwsheds = config.primary_output + r"\WHI_subwsheds"
    if arcpy.Exists(final_subwsheds):
        arcpy.DeleteFeatures_management(final_subwsheds)
    subwshed_copy = arcpy.CopyFeatures_management(config.subwatersheds, final_subwsheds)

    util.log("Appending WHI fields")
    arcpy.env.workspace = config.primary_output
    tablelist = arcpy.ListTables("*final")
    # don't include ShallowWater result as it is citywide, not broken out by subwatershed
    tablelist.remove('ShallowWater_final')
    join_field = "WATERSHED"
    # for each table in the gdb append the field with the suffix "score" to the subwatersheds
    for table in tablelist:
        input_fields = []
        fields = [f.name for f in arcpy.ListFields(table,"*_score")]
        for field in fields:
            input_fields.append(field)

        arcpy.JoinField_management(subwshed_copy,join_field,table,join_field,input_fields)

        # cap WHI score values at 10
        for field in input_fields:
            with arcpy.da.UpdateCursor(subwshed_copy, field) as cursor:
                for row in cursor:
                    row[0] = calc.max_score_check(row[0])
                    cursor.updateRow(row)

    util.log("Module complete")

if __name__ == '__main__':
    print ("This script is meant to be run as a module")
