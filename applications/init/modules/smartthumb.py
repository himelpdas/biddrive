#!/usr/bin/env python
# coding: utf8
from gluon import current #http://www.web2pyslices.com/slice/show/1522/generate-a-thumbnail-that-fits-in-a-box
import os
import urllib2
import cStringIO
import mimetypes

try:
	from PIL import Image
except:
	import Image
 
def SMARTHUMB(image, name, box=(80,80), fit=True, ext='.jpg'): #custom box initializer, name no longer initialized
	'''Downsample the image.
	 @param img: Image -  an Image-object
	 @param box: tuple(x, y) - the bounding box of the result image
	 @param fit: boolean - crop the image to fill the box
	'''
	if image: #goal get image file from url and make it compatible with image.open
		request = current.request
		#CUSTOM
		try:
			is_url = False
			image.seek(0)
			img = Image.open(cStringIO.StringIO(image.read()))#ALREADY BINARY #Try to see if it's already a upload (request.body)
		except KeyError:
			is_url = True
			img = Image.open(#OPEN A IMAGE FROM BINARY
				cStringIO.StringIO(#CONVERT STRING OBJECT TO BINARY
					urllib2.urlopen(image #OPEN URL FROM STRING #else it must be a url
						).read()# TURN TO STRING	
					)
				) #constructs a StringIO holding the image #http://osdir.com/ml/python.image/2004-04/msg00052.html
		#CUSTOM END
		#preresize image with factor 2, 4, 8 and fast algorithm
		factor = 1
		while img.size[0] / factor > 2 * box[0] and img.size[1] * 2 / factor > 2 * box[1]:
			factor *= 2
		if factor > 1:
			img.thumbnail((img.size[0] / factor, img.size[1] / factor), Image.NEAREST)
 
		#calculate the cropping box and get the cropped part
		if fit:
			x1 = y1 = 0
			x2, y2 = img.size
			wRatio = 1.0 * x2 / box[0]
			hRatio = 1.0 * y2 / box[1]
			if hRatio > wRatio:
				y1 = int(y2 / 2 - box[1] * wRatio / 2)
				y2 = int(y2 / 2 + box[1] * wRatio / 2)
			else:
				x1 = int(x2 / 2 - box[0] * hRatio / 2)
				x2 = int(x2 / 2 + box[0] * hRatio / 2)
			img = img.crop((x1, y1, x2, y2))
 
		#Resize the image with best quality algorithm ANTI-ALIAS
		img.thumbnail(box, Image.ANTIALIAS)
		#CUSTOM #goal determine the file extension for a image from URL. it is not the same as getting files from disk b/c urls sometimes don't mention the file name, only mimetype does. MIME~meda type
		if is_url:
			extention = mimetypes.guess_extension(mimetypes.guess_type(image)[0]) #mimetypes.guess_type returns ('image/pjpeg', None) so [0] index has to be passed for guess_extension
		else: #android automatically compresses to jpg
			extention = ext
		#name the thumbnail
		thumb = '%s_thumb%s' % (name, extention)
		#make sure folder path exists or it will be IOError: [Errno 2] No such file or directory: 'applications\\init\\uploads\\thumbnails\\833668e3-8384-42b0-91a2-fdd27083ac51_thumb.jpg'
		folder =  '\\static\\thumbnails\\' if os.name == 'nt' else '/static/thumbnails/'
		path = request.folder + folder
		try: 
			os.makedirs(path)
		except OSError: #prevents race condition http://goo.gl/je7JNF
			if not os.path.isdir(path): #make sure that path is a file
				raise #
		img.save(path + thumb) #custom folder
		#CUSTOM END
		return thumb
		
"""
THIS MODULE WILL TAKE ANY IMAGE URL AND CONVERT IT TO A THUMBNAIL
"""
