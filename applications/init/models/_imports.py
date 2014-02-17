import urllib
import random
import datetime
import uuid
from gluon.contrib import simplejson as json
from gluon.tools import fetch
from ago import human

from math import *

def calcDist(lat_A, long_A, lat_B, long_B):
	distance = (sin(radians(lat_A)) *
		sin(radians(lat_B)) +
		cos(radians(lat_A)) *
		cos(radians(lat_B)) *
		cos(radians(long_A - long_B)))

	distance = (degrees(acos(distance))) * 69.09

	return distance