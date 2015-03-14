import gevent

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import *
from selenium.webdriver.common.action_chains import ActionChains

import pyaes, time, urllib, uuid, requests, json

class BaseSpider():
	def __init__(self, userid = None):
		"""
		Create selenium browser instance
		"""
		self.browser = webdriver.Chrome()
		self.actions = ActionChains(self.browser) #needed to make double-click http://stackoverflow.com/questions/17870528/double-clicking-in-python-selenium
		
	def __exit__(self, type, value, traceback): #dont use del http://stackoverflow.com/questions/6104535/i-dont-understand-this-python-del-behaviour
		"""
		Save memory by closing browser, regardless of success
		"""
		self.browser.close()
		
	def timeout(self, seconds):
		for second in range(30):
			self.time_remain = seconds
			gevent.sleep(1)
			yield True
			
	def decode(self):
		"""
		Convert a VIN into BidDrive compatible data via Edmund's API
		"""
		json_response = requests.get(url="https://api.edmunds.com/api/vehicle/v2/vins/{vin}?manufacturerCode=3548fmt=json&api_key={api_key}".format(vin = self.vin, api_key=EDMUNDS_KEY) )
		vehicle = json.loads(json_response)
		make = vehicle['make']
		model = vehicle['mo']
		
		
	def store(self):
		pass
		self.logout()
		