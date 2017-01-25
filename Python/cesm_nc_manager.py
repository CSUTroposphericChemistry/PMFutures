#!/usr/bin/env python2

###############################################################################
# ------------------------- Description --------------------------------------- 
###############################################################################
# This script will evantually be a class to be used to help analyze CESM air
# quality data. 

# NOTE on NC variables vertical dimensions: Z3 is the height of the middle
# model layers above sea level. The model uses hybrid vertical coordinates
# which are terrain-following, sigma coordinates in most of the troposphere
# and then gradually become pure pressure coordinates somewhere around 100 hPa

# TODO: Change every instance of adding paths together to using 
#       os.path.join(a, b)

import os
import numpy as np
import sys
from mpl_toolkits.basemap import Basemap, cm
from netCDF4 import Dataset 
import matplotlib.pyplot as plt
#import pickle
import numpy.ma as ma
from datetime import date
import matplotlib.ticker as tkr
from datetime import date

###############################################################################
# -----------------Air Quality File functions ---------------------------------
###############################################################################

#scenario = '2000Base'
#AQ_or_fire = 'AirQuality' # TODO: Decide if this is needed 
#NCVariable = 'HEIGHT'
#analysisDay = date(2005, 3, 1) # will be something that is eventually looped over 
#analysisLevel = 100 # mb

# TODO: Make these functions into a class

def KtoF(T):
	F = T * 9/5. - 459.67
	return F	

def KtoC(T):
	C = T - 273.15
	return C

def dateNumToDate(dateNum):
	"""This function takes dates of the form YYYYMMDD and turns them into python
	date objects.
        	Parameters:
             dateNum: A single date string in the format YYYYMMDD or an 
                      array of datestring containing YYYYMMDD
	"""
	n = len(dateNum)
	Dates = []
	for i in range(n):    
		DS = str(dateNum[i])
		yearInt = int(DS[0:4])
		monthInt = int(DS[4:6])
		dayInt = int(DS[6:8])
		Dates.append(date(yearInt, monthInt, dayInt))
	Dates = np.array(Dates)
	return(Dates)


def makeAQNCFile(NCVariable, scenario):
	"""Function for getting path of desired AirQuality variable nc file path.
     """

	scenDec = scenario[0:4]
	scenarioEmissions = scenario[4:len(scenario)]	
	scenDate = {}
	scenDate['2000tail']   = '200001-201012'
	scenDate['2000center'] = '2000'
	scenDate['2050tail']   = '204001-205012'
	scenDate['2050center'] = '2050'
	scenDate['2100tail']   = '209001-209912'
	scenDate['2100center'] = '2100'	

	rcp = {}
	rcp['2000Base']  = ''
	rcp['2050RCP45'] = 'rcp45'
	rcp['2050RCP85'] = 'rcp85'
	rcp['2100RCP45'] = 'rcp45'
	rcp['2100RCP85'] = 'rcp85'
	
	# Data will always live in the same place on Yellowstone, static. 
	dataDirBase = '/fischer-scratch/sbrey/outputFromYellowstone/'
	fileHead = 'cesm122_fmozsoa_f09f09_' 
	fileMid  =  scenDate[scenDec+'center']+'_'+rcp[scenario]+'fires_00.'+ NCVariable
	fileTail = '.daily.' + scenDate[scenDec+'tail'] + '.nc'
	ncFile   = dataDirBase + "AirQualityData/" + scenario + '/' + fileHead + fileMid + fileTail

	return ncFile
 
def makeEmissionNCFile(NCVariable, scenario, year):
	"""function for getting path of desired variable nc file path"""

	dateSpan = {}
	dateSpan['2010']   = '20000101-20101231'
	dateSpan['2050']   = '20400101-20501231'
	dateSpan['2100']   = '20900101-21001231'
	
	# Data will always live in the same place on Yellowstone, static. 
	dataDirBase = '/fischer-scratch/sbrey/outputFromYellowstone/FireEmissions/'
	fileHead = 'cesm130_clm5_firemodule_' 
	fileMid  =  scenario + '_02.' + NCVariable
	fileTail = '.daily.NA.' + dateSpan[year] + '.nc'
	ncFile   = dataDirBase + fileHead + fileMid + fileTail

	return ncFile 


def getNCVarDims(ncFile, NCVariable):
	""""Function takes NCVariable and RCP scenario and returns the dimensions 
     of that variable in a dictionary."""	
	
	nc     = Dataset(ncFile, 'r')
	ncDims = nc.variables[NCVariable].dimensions
	
	# Assign each dimension variable to a datastructure (list?) with keys 
	dimDict = {}	
	for dim in ncDims:
		dimDict[dim] = nc.variables[dim][:]

	nc.close()

	# Datefile is the same as ncFile only NCVariable needs to be replaced with 
	# 'date'
	nc = Dataset(ncFile.replace(NCVariable, 'date'), 'r')
	numDate = nc.variables[u'date'][:]
	Dates = dateNumToDate(numDate)
	nc.close()
	# Append nicely formatted dates of these data 
	dimDict['Dates'] = Dates
	
	return dimDict
	
 
def getNCData(NCVariable, scenario, analysisDay, analysisLevel):
	"""Get the data for a selected level of NCVariable. This function will 
     automatically determine if the dataset has multiple levels. If there
     is only one dimension in the vertical analysisLevel arugment is ignored.
     TODO: Make this work for a passed time mask instead of a single date.
         Parameters:
             NCVarialbe:     String , the variable to be loaded. 
             scemario:       String, RCP scenario, helps select data 
             analysisDay:    String, YYYYMMDD for which to get data
             analysisLevel:  Float, the pressure surface of interest for data
                             defined on pressure surfaces.
	
	"""

	# Get model dimension information from other functions 
	dimDict = getNCVarDims(NCVariable, scenario)
	
	# Find date of interest index in the data 
	dt=np.abs(analysisDay - dimDict['Dates']) 
	dayIndex = np.argmin(dt)
	
	# Load desired layer 
	ncFile = makeNCFile(NCVariable, scenario)	
	nc = Dataset(ncFile, 'r')
	dimDict['units'] = nc.variables[NCVariable].units
	dimDict['longName'] = nc.variables[NCVariable].long_name
	
	print nc.variables

	# Find the ilev to pull from the data, if relevent
	# TODO: Make dynamic based on what dimensions exist and in that order
    # subcalls 

		
	if 'ilev' in dimDict.keys():
		diff = np.abs(dimDict['ilev'] - analysisLevel)
		levIndex = np.argmin(diff)
		data = nc.variables[NCVariable][dayIndex, levIndex, :, :]
	elif 'lev' in dimDict.keys():
		diff = np.abs(dimDict['lev'] - analysisLevel)
		levIndex = np.argmin(diff)
		data = nc.variables[NCVariable][dayIndex, levIndex, :, :]
	else:
		data = nc.variables[NCVariable][dayIndex, :, :]

	nc.close()

	print 'the level chosen is: ' + str(levIndex)
	
	# Now get the land mask
	fireBase = '/fischer-scratch/sbrey/outputFromYellowstone/FireEmissions/'
	nc = Dataset(fireBase + 'cesm130_clm5_firemodule_landmask_f09x125.nc')
	landMask = nc.variables[u'landmask'][:]
	nc.close

	dimDict[NCVariable] = data
	dimDict['landMask'] = landMask

	return dimDict


def getUSGSTopo():
	"""This function returns USGS ncobject"""
	
	baseDir = '/fischer-scratch/sbrey/outputFromYellowstone/'
	ncFile= baseDir + 'USGS-gtopo30_0.9x1.25_remap_c051027.nc'
		
	nc = Dataset(ncFile,'r')
	srf_geo = {}
	srf_geo['PHIS'] = nc.variables[u'PHIS'][:]
	srf_geo['units'] = nc.variables[u'PHIS'].units
	srf_geo['longName'] = nc.variables[u'PHIS'].long_name
	nc.close()
	
	srf_geo['topo'] = srf_geo['PHIS'] / 9.81 # (m**2/s**2) / (m/s**2)
	
	return srf_geo


def getCESMPHIS():
	"""This function extracts and returns surface geopotential 
	   m**2/s**2."""

	baseDir = '/fischer-scratch/sbrey/outputFromYellowstone/'
	ncFile= baseDir + 'cesm122_fmozsoa_f09f09_2000_fires_00.PHIS.monthly.200001-201012.nc'
		
	nc = Dataset(ncFile,'r')
	srf_PHIS = {}
	# All times are the same, does not change, so just grab first
	srf_PHIS['PHIS'] = nc.variables[u'PHIS'][0,:,:] 
	srf_PHIS['Z_srf'] = srf_PHIS['PHIS'] / 9.81 # (m**2/s**2) / (m/s**2) = [m]
	srf_PHIS['units'] = nc.variables[u'PHIS'].units
	srf_PHIS['longName'] = nc.variables[u'PHIS'].long_name
	nc.close()

	return srf_PHIS

def getZ3():
	"""This function gets a month geopotential heights"""
	
	baseDir = '/fischer-scratch/sbrey/outputFromYellowstone/'
	ncFile= baseDir + 'cesm122_fmozsoa_f09f09_2000_fires_00.Z3.monthly.200001-201012.nc'
		
	nc = Dataset(ncFile,'r')
	Z = {}
	Z['Z3'] = nc.variables[u'Z3'][0,:,:,:] 
	Z['units'] = nc.variables[u'Z3'].units
	Z['longName'] = nc.variables[u'Z3'].long_name
	nc.close()

	return Z	

def contourPlot(Z, titleText, units):
	"""Plots a Single date model layer on global projection centered over NA"""
	# TODO: PLACE ALL ARGUMENTS INTO DICTIONARY

	# set up orthographic map projection with
	# perspective of satellite looking down at 50N, 100W.
	# use low resolution coastlines.

	fig = plt.figure(figsize=(6, 6))

	m = Basemap(projection='ortho',lat_0=45,lon_0=-100,resolution='l')
	# draw coastlines, country boundaries, fill continents.
	m.drawcoastlines(linewidth=0.25)
	m.drawcountries(linewidth=0.25)
	m.fillcontinents(color='coral',lake_color='aqua')
	# draw the edge of the map projection region (the projection limb)
	m.drawmapboundary(fill_color='aqua')
	# draw lat/lon grid lines every 30 degrees.
	m.drawmeridians(np.arange(0,360,30))
	m.drawparallels(np.arange(-90,90,30))

	# make up some data on a regular lat/lon grid.
	lons, lats = np.meshgrid(data['lon'], data['lat']) 
	x, y = m(lons, lats) # compute map proj coordinates.

	# contour data over the map.
	cs = m.contourf(x, y, Z, 16,linewidths=3)
	csFill = m.pcolor(x, y, Z, visible=False)
	cbar = m.colorbar(csFill, location='bottom', pad="1%")
	cbar.set_label(units, fontsize=17)
	#titleText= dateLab+' '+scenario + ' ' + str(analysisLevel) + 'hPa ' +NCVariable
	plt.title(titleText, fontsize=15)
	#plt.draw()
	plt.show(block=False)

###############################################################################
# ------------------------- Description --------------------------------------- 
###############################################################################
# These functions are used to identify meteorogy events 
# relevent for air quality and climate change impact assesment in the EPA
# "Planning for an uncertain future" project (dubbed PMFutures). 

def detectStringInList(string, some_list):
    matching = [s for s in some_list if string in s]   
    return matching

def getGroundAirQaulityData(variable, ncFile, scenario):
    """This function loads nc data of given variable and scenario into
    the working environment using numpy arrays.
        Parameters:
            variable:   The AQ variable to be loaded (T, U, V, Precip?)
            ncFile:     The path of the ncFile to be loaded
            scenario:   The RCP scenario of the data to be loaded
            
        return: M, MUnits, MLongName, t, lat, lon     
    """
        
    nc = Dataset(ncFile, 'r')
    
    # Need to determine if variable on ilev or lev dimension
    ncDims = nc.variables[variable].dimensions
    test   = detectStringInList('lev', ncDims)
    if test == ['lev']:
        levelDim = 'lev'
    elif test == ['ilev']:
        levelDim = 'ilev'
    elif test == ['Pressure']: 
        levelDim = 'Pressure'
    else:
        print 'unknown dimension type for variable '
    
    # Find the index of the levelDim that is closest to surface
    print 'levelDim being used is : ' + levelDim    
    print ncDims    
    
    lev = nc.variables[levelDim][:]
    surface_index = np.where(lev == lev.max())[0][0]
    
    print 'loading large file.....'
    # Get the data and the units 
    M         = nc.variables[variable][:, surface_index, :, :] 
    MUnits    = nc.variables[variable].units
    MLongName = nc.variables[variable].long_name
    print 'done loading large file'
    
    # get the spatial dims
    lat = nc.variables['lat'][:]
    lon = nc.variables['lon'][:]
    
    nc.close()
    
    # Get the time dimension 
    ncTimeFile = makeAQNCFile('date', scenario)
    ncTime = Dataset(ncTimeFile, 'r')
    date = ncTime['date'][:] # Gets date string
    ncTime.close()
    
    t = dateNumToDate(date) # converts date string to date object 
    
    return M, MUnits, MLongName, t, lat, lon 
    

def findHighValueDays(M, t, percentile):
    """This function accepts a numeric array (t, lat, lon) and returns
    an equal size array of 1s and 0s. The 1s indicate dates where M exceeded
    monthly percentile threshold for that location and 0s dates when they did
    not.
        Parameters:
            M:           Met variuable array to be passed. format (t, lat, lon)
            t:           datetime.date array that defines time diemsion of T
            percentile:  value between 0 and 100 that determines value used for
                         a given month and grid cells threshold. 
                         
        return: 
            mask:       True and False values indicating if temperature for day 
                        and location exceeds percentile threshold value for 
                        that month. True equals high T days. 
            threshold:  An array (month, lat, lon) that contains the percentile
                        threshold value for each month and location used to 
                        make 'mask'.    
    """
    # set the size of output based on the size of passed temperature array
    nDays = len(t)
    nLat = M.shape[1]
    nLon = M.shape[2]    
    
    # make arrray that is month of t    
    mon = np.zeros(nDays,dtype=int)
    for i in range(nDays):
        mon[i] = t[i].month
        
    # monthly threshold array
    threshold = np.zeros((12, nLat, nLon))
    mask      = np.zeros(M.shape, dtype=bool) 
    
    # Loop through each month of the year and each grid cell to find
    # that months locations percentile thresh value. Create a mask.
    for i in range(12):
        month = i + 1
        monthMask = np.where(mon == month)[0]       
        
        for LAT in range(nLat):
            for LON in range(nLon):
                M_cell = M[monthMask, LAT, LON]
                threshValue = np.percentile(M_cell, percentile)
                threshold[i, LAT, LON] = threshValue 
                mask[monthMask, LAT, LON] = M_cell >= threshValue
                
    return mask, threshold
    
def getSurfaceWindScaler(scenario):
    """This function uses getGroundAirQaulityData() to load u and v winds and
    make a scaler wind for threshold analysis threshold. 
        Parameters:
            scenario: The year and RCP scenario for the wind data 
    """
    
    uFile = makeAQNCFile("U", scenario)
    u, MUnits, MLongName, t, lat, lon = getGroundAirQaulityData("U", \
                                                                uFile,\
                                                                scenario)
    
    vFile = makeAQNCFile("V", scenario)
    v, MUnits, MLongName, t, lat, lon = getGroundAirQaulityData("V", \
                                                                vFile,\
                                                                scenario)
    
    # Now make a scaler wind from the vector coomponents
    scaler = np.sqrt(v**2 + u**2)

    return scaler, MUnits, 'Scaler Wind', t, lat, lon      

###############################################################################
# ------------------------- Description --------------------------------------- 
###############################################################################
# This script will be used to summarize and plot emissions from CESM. 
# A Multipanel plot will sumarize the present day, 2050, 2100 emissions for a 
# selected variable. Later on, this script will be able to make the standard 
# plots for desired time and season subsets. Much later, this code will be
# incorperated into a shiny app that will allow easy exploration of the model 
# output. 

def getEmissionVariableData(variable, scenario, year):
	"""This function loads the emission 'variable' for the given secenario
     and year (ending decade of 11 year period of data). The time variable
	is transformed to a python datetime.date object and assumes that there
     are no leap years in the model output (tested). 
         Paremeters: 
             variable:  The emission variable to be loaded
             scenario:  The RCP scenario to load data for 
             year:      The decade to load data for 

   
         return value: bb, bbUnits, t, lat, lon

	"""

	# Load the data
	ncFile     = makeEmissionNCFile(variable, scenario, year)
	nc         = Dataset(ncFile, 'r')
	bb         = nc.variables['bb'][:]
	bbUnits    = nc.variables['bb'].units
	bbLongName = nc.variables['bb'].long_name

	# Handle the massive fill_value for bb so math does not go crazy later
	bbMask = bb.mask
	bb.data[bbMask==1] = 0 # changes locations of data fill value from huge to 0

	# Handle time dimension. NOTE: Leap years do not exist in the model. 
	daysSincet0 = nc.variables['time'][:]   # only used for length of time dim
	 
	months      = [1,2,3,4,5,6,7,8,9,10,11,12]
	daysInMonth = [31,28,31,30,31,30,31,31,30,31,30,31] # Never a 29 day February
	nMonth      = len(daysInMonth)
	daysInYear  = np.sum(daysInMonth)
	nYears      = len(daysSincet0) / daysInYear 

	# start year is always 10 years before year selection string. 
	# start month and day are always Jan 1 for emissions
	startYear = int(year) - 10
	t0        = date(startYear, 1, 1) 

	t = [] # where time will be appended
	for deltaYear in range(nYears):
		# Advance the year
		YEAR = t0.year + deltaYear
		for m in range(nMonth):
			dim = daysInMonth[m]
			for d in np.linspace(1, dim, dim, dtype='int'):
				newDate = date(YEAR, months[m], d)
				t.append(newDate)
			
	# Make useful array
	t = np.array(t)

	# Get spacial dimensions
	lon = nc.variables['lon'][:]
	lat = nc.variables['lat'][:]

	nc.close()

	return bb, bbUnits, bbLongName, t, lat, lon

def loadEmissionGridAttributes(lat, lon):
	"""Load model grid cell atributes. These do not depend on time. Must be 
     subset to match bb grid that is already loaded into workspace.
   	   Parameters:
           lon: longitude that defines the grid of emission data.
           lat: latitude that defines the grid of emission data. 
	
           return value: area of grid cells in units of m^2
	"""

	dataDir = '/fischer-scratch/sbrey/outputFromYellowstone/FireEmissions/'
	moduleLayers = ['area','landfrac','landmask']
	layer = {}
	for f in moduleLayers:
		fileName = dataDir + 'cesm130_clm5_firemodule_'+ f + '_f09x125.nc'
		nc = Dataset(fileName, 'r')
		layer[f] = nc.variables[f][:]
		allLons = nc.variables['lon'][:]
		allLats = nc.variables['lat'][:]
		nc.close()

	# Get area from km**2 to m*2
	m2Perkm2 = 1e6 * 1.
	area = layer['area']
	area = area * m2Perkm2
	landMask = layer['landmask']

	# Get rid of the insanely large fill value that messes up multiplication. 
	area.data[landMask==0] = 0

	# Subset based on the dimensions where lat and lon match
	lonI = np.where(np.in1d(allLons, lon))[0]
	latI = np.where(np.in1d(allLats, lat))[0]

	# TODO: Handle this masking in a non horrible way. The plus one in the max
	#       end of indexing is required to include that maximum index. 
	areaSubset = area[latI.min():(latI.max()+1) , lonI.min():(lonI.max()+1)]
	#fill_value = area.fill_value
	area = areaSubset

	return area # later others may be needed as well. 

def makeTotalEmissions(bb, area, t): 
	"""This function takes change the units of emissions from kg/sec/m^2 to 
	an equal size array that returns kg/day/gridcell and another array
	that returns total emissions (kg) in time period, shape=(lat, lon). 	
        	Parameters:
             bb:      data in kg/sec/m^2 to be changed. 
             area:    associated grid showing the area of each cell in m^2. 
             t:       the time array. Datetime object that describes time 
                     dimension
			      of bb. 
		
          return vaue: kgPerDay, kgTotal
	"""

	# Get emissions from kg/m2/sec to kg in time period of interest
	secondsPerDay = 24. * 60**2
	kgPerDay = np.zeros(bb.shape)
	for i in range(len(t)):
		kgPerDay[i, :, :] = bb[i,:,:] * (area.data * secondsPerDay)

	# Now sum over time to come up with maximum values
	kgTotal = np.sum(kgPerDay,0) * len(t)

	return kgPerDay, kgTotal


# TODO: add extent arg so that all have same limit
def makePcolorFig(ax, m, x, y, z, titleText, maxVal): 
    '''Creates a simple pcolor image of the NxM array passed in z. 
           Parameters:
               m: The map object to be plotted on.
               x: The x coords of m.
               y: The y coords of m.
               z: NxM array to be plotted using pColor
               titleText: The title of the figure returned by this func. 
    '''

    # Create the figure on the passes axis
    ax
    
    m.drawcoastlines()
    m.drawstates()
    m.drawcountries()
    
    #parallels = np.arange(0.,90,15.)
    #meridians = np.arange(180.,360.,15.)
    
    #m.drawparallels(parallels,labels=[1,0,0,0], fontsize=10)
    #m.drawmeridians(meridians,labels=[0,0,0,1],fontsize=10)
    
    z = ma.masked_where(z == 0, z)
    cs = m.pcolor(x, y, z, cmap='Reds', vmin=0, vmax = maxVal)
    
    # add colorbar.
    cbar = m.colorbar(cs, location='bottom', pad='5%')
    cbar.set_label(variable, fontsize=11)
    cbar.set_ticks([0, maxVal])    

    # add title
    ax.set_title(titleText, fontsize=16)

    		    
    return(ax) 



def subsetModelEmissions(data, t, lat, lon, startMonth=1, endMonth=12, 
                         minLat=11., maxLat=90., minLon=190., maxLon=320.):
    '''This function subsets a three dimensional grid (time, lat, lon) based
    on the passed spatial and temporal arguments.
    Parameters:
        data:       The array(time, lat, lon) to be subset. 
        t:          data time dimension as datetime.date object
        lat:        The latitude of data
        lon:        The longitude of data
        startMonth: The first month to be considered for all years.
        endMonth:   The last month to be consider for all years. 
        minLat:     These four parameters subset the passed data array
        maxLat:
        minLon:
        maxLon: 
        
        return Value: dataSubset, tSubset, latSubset, lonSubset

    '''
    # NOTE:masks do not work on multidimensional arrays
    latMask = (lat >= minLat) & (lat <= maxLat)
    lonMask = (lon >= minLon) & (lon <= maxLon)
    lati = np.where(latMask == True)[0]
    loni = np.where(lonMask == True)[0]
    
    # TODO: Figure out qwhy the TODO is needed for last index,
    #       this is a strange python thing I do not understand. 
    lonSubset = lon[loni[0]:(loni[-1]+1)]
    latSubset = lat[lati[0]:(lati[-1]+1)]
    
    # Make the time subset 
    nt = len(t)
    mon = np.zeros(nt, dtype='int')
    timeMask = np.zeros(nt, dtype='bool')
    for i in range(nt):
        mon[i] = t[i].month
        
    tMask = (mon >= startMonth) & (mon <= endMonth)
    ti = np.where(tMask == True)[0] # you can have whatever you like
    tSubset = t[ti[0]:(ti[-1]+1)]
    
    # Super ugly statement for getting the subset of lat and lon
    dataSubset = data[ti[0]:(ti[-1]+1), lati[0]:(lati[-1]+1), loni[0]:(loni[-1]+1)]

    return dataSubset, tSubset, latSubset, lonSubset    
    
    
    
def timeSeries(ax1, s1, s2, s1Label, s2Label, t, maxValue, titleText):    
    '''kgPerDay1 and kgPerDay2 are emissions data (time, lat, lon). This 
    function will sum over time and lon to plot total emissions vs. time in
    the entire spatial domain of the passed arrays. '''
  
    ax1
        
    ax1.plot(t, s1, 'b-', linewidth=1, label=s1Label)
    ax1.tick_params(axis='x', labelsize=11)
    ax1.tick_params(axis='y', labelsize=11)
    ax1.set_ylim([0, maxValue])
    
    ax1.plot(t, s2, 'r-', linewidth=1, label=s2Label)
    ax1.tick_params(axis='y', labelsize=11)
    ax1.tick_params(axis='x', labelsize=11)
        
    # shared x-axis 
    ax1.set_xlabel('Time', fontsize=11)
    # Label y axes	
    ax1.set_ylabel('[kg]', fontsize=11)
    
    plt.title(titleText, fontsize=18)
    
    ax1.legend(frameon=False, loc='upper left')
    
    return(ax1)


def monthlyTotals(s, t):
	"""Counts monthly totals of s for all months of the year. Returns
	   an array that contains s totals for each month. 
    """

	# Create a place to store monthly total
	sMonthTotal = np.zeros(12)
	for i in range(len(t)):
		day = t[i]
		dayMonth                = day.month  # what month is this date in?
		monIndex                = dayMonth-1 # the index is month# - 1
		sMonthTotal[monIndex]  += s[i]       # add to ongoing month total 

	return sMonthTotal
		
		
def makeHist(ax, s1MonthTotal, s2MonthTotal, s1Label, s2Label, maxValue, titleText):
    """Function makes lovely histogram (bar plot) for two series of data
    TODO: Make histogram actually lovely
    TODO: startMonth endMonth dynamic argument accept. 
    """
    n_groups = len(s1MonthTotal)
 
    ax

    index = np.arange(n_groups)
    bar_width = 0.35

    opacity = 1

    rects1 = plt.bar(index, s1MonthTotal, bar_width,
                 	  alpha=opacity,
                	  color='b',
                 	  label=s1Label
					  )
    plt.ylim(0, maxValue)
	
    rects2 = plt.bar(index + bar_width, s2MonthTotal, bar_width,
                 	  alpha=opacity,
                 	  color='r',
                 	  label=s2Label)

    plt.xlabel('Month')
    plt.ylabel('Emissions [passed units argument]')
    plt.title(titleText)
    plt.xticks(index + bar_width, ('1', '2', '3', '4', '5', '6', '7', '8', \
                                    '9', '10', '11', '12'))
    plt.legend()

    plt.tight_layout()

    return(ax)



                                              
	
