#-------------------------------------------------------------------------------
# Name:        calc
# Purpose:     WHI equations
#
# Author:      DASHNEY
#
# Created:     02/11/2015
#
# equations for WHI score calculations
#-------------------------------------------------------------------------------


def max_score_check(input):
    if input > 10:
        return 10
    else:
        return input

def EIA_score(input):
    if input > 10:
        output = 10.5-25*(input/100)
    else:
        output = 10-(input/5)
    if output > 0:
        return output
    else:
        return 0

def streamCon_score(input):
    if input > 5:
        output = 9.25-(input/4)
    else:
        output = 10-(input/2.5)
    return output

def canopy_scores(input):
    output = 0.2195* input
    return output

def fpCon_score(input):
    if input < 20:
        output = 0
    else:
        output = -0.000009*(input**3)+0.00206*(input**2)-0.0092*(input)-0.57
    return output

def shallowWater_score(input):
    output = -0.0014*(input**2)+0.2546*input-1.2381
    return output

def streamAccess1_count(full):
    output = full/10
    return output

def streamAccess2_count(full,partial):
    output = (full/10)+(0.5*(partial/10))
    return output

def ripIntegrity_score(pcnt_canopy,crossNum):

    # WHI score = lowest of the two (pcnt_canopy vs crossNum) OR only score if one not available for a given subwatershed

    ripcanopy = pcnt_canopy * 0.1
    crossings = 12 - (crossNum * 2)
    if ripcanopy < crossings:
        return ripcanopy
    else:
        return crossings




