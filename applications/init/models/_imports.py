import urllib
import random
import datetime
import uuid
from gluon.contrib import simplejson as json
from gluon.tools import fetch
from ago import human
import simplecolor
from collections import OrderedDict as OD #http://bit.ly/OhPhQr

from math import *

def calcDist(lat_A, long_A, lat_B, long_B):
	distance = (sin(radians(lat_A)) *
		sin(radians(lat_B)) +
		cos(radians(lat_A)) *
		cos(radians(lat_B)) *
		cos(radians(long_A - long_B)))

	distance = (degrees(acos(distance))) * 69.09

	return distance
	
APP_NAME="carbid"
EDMUNDS_KEY ="qmnpjbhe9p5g5cw3yv2vaehv"
EDMUNDS_SECRET="zA6vs797nVgqGaSK58QJe2KW"
AUCTION_DAYS_EXPIRE = 3
