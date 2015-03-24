from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import *
from selenium.webdriver.common.action_chains import ActionChains

import time, urllib, uuid, requests, json, os

#import atexit

#from gluon import current #http://www.web2pyslices.com/slice/show/1522/generate-a-thumbnail-that-fits-in-a-box

class BaseSpider():

	photos = []
	VIN=""
	description = ""
	
	def __init__(self, userid, savedir, field_a=None, field_b=None, field_c=None, field_d=None, field_e=None):
		"""
		Create selenium browser instance
		"""
		self.field_a = field_a
		self.field_b = field_b
		self.field_c = field_c
		self.field_d = field_d
		self.field_e = field_e
		self.userid = userid
		
		self.savedir = savedir
		
		self.browser = webdriver.Firefox()
		self.actions = ActionChains(self.browser) #needed to make double-click http://stackoverflow.com/questions/17870528/double-clicking-in-python-selenium
		
		#atexit.register(self.__exit__, None, None, None) #make sure browser closes	
		
	def __enter__(self): #USE WITH THE "WITH" STATEMENT http://stackoverflow.com/questions/1984325/explaining-pythons-enter-and-exit
		self.run()
		return self
		
	def __exit__(self, type, value, traceback): #dont use del http://stackoverflow.com/questions/6104535/i-dont-understand-this-python-del-behaviour
		"""
		Save memory by closing browser, regardless of success
		"""
		self.cleanup()
		self.browser.close()
		
	def cleanup(self):
		"""
		Get rid of the files saved by spider, 
		since by now web2py already uploaded them in controller
		"""
		for each_photo in self.photos:
			try:
				os.remove(self.savedir + each_photo)
			except:
				pass
		
	def timeout(self, seconds):
		for second in range(30):
			self.time_remain = seconds
			time.sleep(1)
			yield True
		