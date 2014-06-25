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
from collections import OrderedDict as OD #http://bit.ly/OhPhQr
import lookup_hash

from math import *

def calcDist(lat_A, long_A, lat_B, long_B):
	distance = (sin(radians(lat_A)) *
		sin(radians(lat_B)) +
		cos(radians(lat_A)) *
		cos(radians(lat_B)) *
		cos(radians(long_A - long_B)))

	distance = (degrees(acos(distance))) * 69.09

	return distance
	
def quickRaise(error):
	"""
	for use with single line statements as '' or raise/exec will return syntax error
	"""
	raise Exception(error)
	
APP_NAME="BidDrive(Alpha)"
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
	from motionless import DecoratedMap, AddressMarker #python google static maps generator
	#gpolyencode.py included as well