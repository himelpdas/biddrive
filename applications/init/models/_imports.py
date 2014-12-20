import urllib
import random
import datetime
from pytz import timezone
import uuid
from gluon.contrib import simplejson as json
from gluon.tools import fetch
import time
from ago import human
import simplecolor
from collections import OrderedDict #http://bit.ly/OhPhQr
OD = OrderedDict #shortcut
import platform #check the platform web2py is running from
#import lookup_hash

####ENABLE LOGGING FOR Macs AND PCs, which are probably development environments####
if platform.system() in ["Darwin", "Windows"]:
	import logging
	logger = logging.getLogger("web2py.app.biddrive")
	#handler = logging.StreamHandler() #by default logs go to stdout or stderr, you can set it to file via FileH
	#print logger.findCaller()
	logger.setLevel(logging.DEBUG) #only will show debug level and higher
######## http://goo.gl/BAU6cF

	
def quickRaise(error):
	"""
	for use with single line statements as '' or raise/exec will return syntax error
	"""
	raise Exception(error)
	
APP_NAME="BidDrive"
EDMUNDS_KEY ="qmnpjbhe9p5g5cw3yv2vaehv"
EDMUNDS_SECRET="zA6vs797nVgqGaSK58QJe2KW"
AUCTION_DAYS_EXPIRE = AUCTION_FAVS_EXPIRE = 3
AUCTION_DAYS_OFFER_ENDS = 1
GMAPS_KEY = "AIzaSyBAnNycjSMSADu5n426xjPuT9jWWhri8xI"

if not session.salt:
	session.salt = uuid.uuid4()

#regex
REGEX_TELEPHONE = '^1?((-)\d{3}-?|\(\d{3}\))\d{3}-?\d{4}$'

if request.function in ["dealer_radius_map", "winner"]:
	from motionless import DecoratedMap, AddressMarker, LatLonMarker #python google static maps generator
	#import gpolyencode #gpolyencode.py included as well
	
if request.function in ["dealership_form", "dealer_info", "pre_auction", "auction", "auction_requests", "dealer_radius_map"]: #spans default, appadmin, admin, dealer controllers #needed to convert dealership addy to proper lat long
	from geopy import geocoders #https://code.google.com/p/geopy/wiki/GettingStarted
	from geopy import distance, point
	def calcDist (lat_A, long_A, lat_B, long_B):
		return float(distance.distance(point.Point(lat_A, long_A), point.Point(lat_B, long_B)).miles)
	
"""
from math import *

def calcDist(lat_A, long_A, lat_B, long_B): #DEPRECATED USE GEOPY NOW!
	distance = (sin(radians(lat_A)) *
		sin(radians(lat_B)) +
		cos(radians(lat_A)) *
		cos(radians(lat_B)) *
		cos(radians(long_A - long_B)))

	distance = (degrees(acos(distance))) * 69.09

	return distance
"""

#color swatch
COLOR_SWATCH = lambda hex, title='': XML('<i class="fa fa-square fa-fw" style="color:#%s; text-shadow : -1px 0 black, 0 1px black, 1px 0 black, 0 -1px black;" title="%s"></i>'%(hex,title) ) #add border so that whites can show #http://goo.gl/2j2bP #http://goo.gl/R9EI3h

	