from gevent import monkey; monkey.patch_all()

from basespider import *
		
class AutoManager(BaseSpider):
	logged_in_phrase = "Log out of WebManager"
	edmunds_vin_decode_url = "https://api.edmunds.com/api/vehicle/v2/vins/4T1BK1EB6DU056165?manufacturerCode=3548fmt=json&api_key={api_key}"

	def __init__(self, login_clientid, login_username, login_password, scrape_stockid):
	
		BaseSpider.__init__(self)
		
		self.login_clientid = login_clientid

		self.login_username = login_username

		self.login_password = login_password
		
		self.scrape_stockid = scrape_stockid
		
		self.no_crash = self.timeout(30)
		
	def login(self):
		self.browser.get('https://wm.automanager.com/login.aspx')
		
		username = self.browser.find_element_by_id("ctl00_cphMain_txtUsername")
		password = self.browser.find_element_by_id("ctl00_cphMain_txtPassword")
		clientid = self.browser.find_element_by_id("ctl00_cphMain_txtClientID")
		
		username.send_keys(self.login_username)
		clientid.send_keys(self.login_clientid)
		password.send_keys(self.login_password)
		
		self.browser.find_element_by_id("btnLogin").click()

		while self.no_crash.next():
			source = (self.browser.page_source).encode('utf-8') #http://stackoverflow.com/questions/16823086/selenium-webdriver-and-unicode
			if self.logged_in_phrase in source:
				#self.dashboard = source
				return
			elif "Duplicate Login" in source:
				try:
					self.browser.find_element(By.XPATH, '//span[text()="OK"]/..').click()
				except (ElementNotVisibleException, NoSuchElementException, StaleElementReferenceException):
					pass
					
	def navigate(self):
		for link in self.browser.find_elements(By.XPATH, "//div[@class='menu-panel']//a"):
			href = link.get_attribute('href')
			if "?View=Live" in href: #http://stackoverflow.com/questions/19664253/selenium-how-to-get-the-content-of-href-within-some-targeted-class
				self.browser.get(href)
				return
		
	def find(self):
		page = 1
		while self.no_crash.next():
			try:
				for vehicle in self.browser.find_elements_by_xpath("//tr[@class='new']"):
					if self.scrape_stockid in vehicle.get_attribute('innerHTML').encode('utf-8'): #http://stackoverflow.com/questions/7263824/get-html-source-of-webelement-in-selenium-webdriver
						link = vehicle.find_element_by_xpath(".//div[@class='vehicle-link']//a")
						href = link.get_attribute('href')
						self.browser.get(href)
						return #return to break external loop
				page+=1
				self.browser.find_element_by_xpath("//a[@pageid='%s']"%page).click()
			except (ElementNotVisibleException, NoSuchElementException, StaleElementReferenceException):
				pass
				
		
	def scrape(self):
		#get vin
		self.VIN = self.browser.find_element_by_id("ctl00_cphMain_txtVIN").get_attribute("value") or ''
		print self.VIN
		
		#navigate to description page
		link = self.browser.find_element_by_link_text('Description')
		href = link.get_attribute('href')
		self.browser.get(href)
		
		#get description
		self.description = self.browser.find_element_by_id("ctl00_cphMain_txtPlainDesc").get_attribute("value") or ''
		print self.description
		
		#navigate to photos page
		link = self.browser.find_element_by_link_text('Photos')
		href = link.get_attribute('href')
		self.browser.get(href)
		
		#make a list of thumbnails
		thumbnails = self.browser.find_elements_by_xpath("//img[@class='gallery-photo']")
		thumb_urls = []
		for thumbnail in thumbnails:
			thumb_urls.append(thumbnail.get_attribute("src"))
			
		#get the large size number 
		self.actions.double_click(thumbnail).perform()
		photo = self.browser.find_element_by_id("frmDynamicDialog").get_attribute("src")
		photo_size = int(photo.split("_")[-1].split(".")[0])

		#convert them to large and download
		#from http://photos2.automanager.com/027852/1c264532de754d32aa5181c56d033723/14a9498a08_105.jpg?TS=130657930160000000
		#to http://photos2.automanager.com/027852/1c264532de754d32aa5181c56d033723/14a9498a08_640.jpg
		for i, each_url in enumerate(thumb_urls):
			split1 = each_url.split("_")
			split2 = split1[1].split(".")
			photo_ext = split2[1].split("?")[0]
			photo_url = split1[0] + "_%s."%photo_size + photo_ext
			photo_uid = '%s_%s'%(i, str(uuid.uuid4() ) ) 
			urllib.urlretrieve(photo_url, "%s.%s"%(photo_uid, photo_ext) ) #http://stackoverflow.com/questions/3042757/downloading-a-picture-via-urllib-and-python
			gevent.sleep(0.5)
		
	def run(self):
		spider.login()
		spider.navigate()
		spider.find()
		spider.scrape()

if __name__ == "__main__":
	key = raw_input("Decrypt test account info: ") #DH password + .
	
	spider = AutoManager(
		login_clientid = pyaes.AESModeOfOperationCTR(key).decrypt('G\x98\x84\x9a!.'),  
		login_username = pyaes.AESModeOfOperationCTR(key).decrypt('\x16\xce\xde\xcbz'), 
		login_password = pyaes.AESModeOfOperationCTR(key).decrypt('F\x98\x80\x96!*\x8d\xb6'),
		scrape_stockid = "P0079"
	)
	spider.run()