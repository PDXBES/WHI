#-------------------------------------------------------------------------------
# Name:        config
# Purpose:     Automate Watershed Health Index process
#
# Author:      DASHNEY
#
# Created:     02/11/2015
# WHI config file
# inputs
#-------------------------------------------------------------------------------

# connections to city gis hub data
egh_public = r"\\oberon\grp117\DAshney\Scripts\connections\egh_public on gisdb1.rose.portland.local.sde"
egh_raster = r"\\oberon\grp117\DAshney\Scripts\connections\egh_raster on gisdb1.rose.portland.local.sde"

# data in these locations will be overwritten with each process run
primary_input = r"\\besfile1\grp104\Watersheds-All\WSHIndex\Data\WHI_primary_input.gdb"
primary_output = r"\\besfile1\grp104\Watersheds-All\WSHIndex\Data\WHI_primary_output.gdb"
temp_gdb = r"C:\Temp\WHI_working.gdb"

# data in the archive location will be date stamped and appended, not overwritten
archive_loc = r"\\besfile1\grp104\Watersheds-All\WSHIndex\Data\Archive"

city_bound = egh_public + r"\EGH_PUBLIC.ARCMAP_ADMIN.portland_pdx"

# aggregation boundaries
# Q - might the subwatersheds change with the 10th floor re-org?
subwatersheds = r"\\besfile1\grp104\Watersheds-All\WSHIndex\Data\Shapefiles\Watersheds with Willamette Mainstem and Tribs\Portland_Watersheds_Willamette_Tribs_and_Mainstem.shp"
EDT_reaches = egh_public + r"\EGH_Public.ARCMAP_ADMIN.willamette_reaches_pdx"

# sources
collection_lines = egh_public + r"\EGH_PUBLIC.ARCMAP_ADMIN.collection_lines_bes_pdx"
ImpA = egh_public + r"\EGH_PUBLIC.ARCMAP_ADMIN.impervious_area_bes_pdx"
BES_UIC = egh_public + r"\EGH_PUBLIC.ARCMAP_ADMIN.uic_bes_pdx"
BMP_drainage = r"\\besfile1\Modeling\GridMaster\BMP\PRF\ARC\Working\Drainage_Delineation\DelineationFinal_results.gdb\Delineation_04_2015"
ecoroof_pnt = egh_public + r"\EGH_PUBLIC.ARCMAP_ADMIN.ecoroof_pts_bes_pdx"
privateSMF = egh_public + r"\EGH_PUBLIC.ARCMAP_ADMIN.priv_mip_strm_facs_bes_pdx"
streams = egh_public + r"\EGH_PUBLIC.ARCMAP_ADMIN.stream_lines_pdx"
canopy = egh_raster + r"\EGH_Raster.ARCMAP_ADMIN.VEGETATION_2007_METRO"
floodplain_clip = r"\\besfile1\grp104\Watersheds-All\WSHIndex\Data\Shapefiles\Floodplain\Floodplain_clip.shp"
river_depth = egh_raster + r"\EGH_Raster.ARCMAP_ADMIN.river_depths_ohw_pdx"
stream_access = r"\\oberon\grp104\Watersheds-All\WSHIndex\Data\Geodatabase\Stream_Accessibility.mdb\Stream_Accessibility"
waterbodies = egh_public + r"\EGH_PUBLIC.ARCMAP_ADMIN.waterbodies_pdx"
sump_delin = r'\\besfile1\StormWaterProgram\System_Plan\Risk_Assessment\ARC\ReviewDataSources\Task6_working.gdb\PublicSumpBasins'
mst_dscs = egh_public + r"\EGH_PUBLIC.ARCMAP_ADMIN.mst_dsc_bes_pdx"
streets = egh_public + r"\EGH_PUBLIC.ARCMAP_ADMIN.streets_pdx"

canopy_combo_rast = temp_gdb + r"\canopy_combo_raster"
canopy_combo_vect = primary_input + r"\canopy_combo_vector"

# other - lists and dictionaries
# CHECK ARCHIVE_LIST TO MAKE SURE IT HAS ALL SOURCES WE WANT ARCHIVED
vect_archive_list = [subwatersheds,EDT_reaches,ImpA, BES_UIC, BMP_drainage, ecoroof_pnt, privateSMF, streams, canopy_combo_vect, floodplain_clip, stream_access, waterbodies]
rast_archive_list = [canopy, river_depth]
smf_dict = {'Constructed Treatment Wetland': 43560, 'Detention Pond - Dry': 43560, 'Detention Pond - Wet': 43560, 'Drywell': 2000, 'Infiltration Trench': 2000, 'Soakage Trench': 2000, 'Flow Through Planter Box': 2000, 'Infiltration Planter Box': 2000, 'Infiltration Baxin': 2000, 'Swale': 2000, 'Stormwater Reuse System': 2000, 'Porous Pavement': 27500}
wshed_dict = {100: "Columbia Slough", 200: "Johnson Creek", 300: "Fanno Creek", 400: "Tryon Creek", 500: "Willamette Mainstem", 600: "Willamette Tribs"}
vegtype_dict = {1:"Built",2:"Low_Med",3:"High",4:"Water"}