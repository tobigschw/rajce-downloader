import argparse
import re
import os
import urllib.request
import xml.etree.ElementTree as ET
import time

class Rajce:

	urls = None
	path = None
	videoStorage = None
	securityCode = None

	def __init__(self, urls, path=None):
		self.urls = urls
		self.path = path

	def download(self):
		for url in self.urls:
			url = self.validate_url(url)
			m = re.search('([\w-]+?)\.rajce\.idnes\.cz/(.*)\/', url)
			if not m:
				print('Wrong url!')
			elif m.group(2) == '':
				self.download_gallery(url)
			else:
				self.download_album(url)

	def download_gallery(self, galleryUrl):
		html = urllib.request.urlopen(galleryUrl).read().decode('utf-8')

		pageList = [int(x) for x in re.findall('sort=createDate.+?page=(\d+)', html)]
		page = int(max(pageList)) if pageList else 0

		user = re.search('([\w-]+?)\.rajce\.idnes\.cz/', galleryUrl).group(1)

		while page >= 0:
			regex = '(' + user + '\.rajce\.idnes\.cz/.*?/)\">'
			albums = re.findall(regex, html)
			if not albums:
				print('No albums found.')
				return

			for album in albums:
				print(album)
				self.download_album(self.validate_url(album))

			if page > 0:
				pageUrl = galleryUrl + '?listType=&sort=createDate&page=' + str(page)
				html = urllib.request.urlopen(pageUrl).read().decode('utf-8')

			page = page - 1

	def download_album(self, albumUrl):
		html = urllib.request.urlopen(albumUrl).read().decode('utf-8')

		storage = re.search('var storage = "(.*)";', html).group(1)
		self.securityCode = re.search('var albumSecurityCode = \"(.*)\";', html).group(1)

		links = re.findall('{ (photoID: \".*)}', html)
		if not links:
			print('No photo found.')
			return

		m = re.search('([\w-]+?)\.rajce\.idnes\.cz/(.*?)/', albumUrl)
		filePath = os.path.join(m.group(1), m.group(2).replace('.','_'))
		os.makedirs(filePath, exist_ok=True)

		for link in links:
			if re.search('isVideo: (.*), desc', link).group(1) == 'false':
				fileName = re.search('fileName: \"(.+?)\"', link).group(1)
				fileUrl = storage + 'images/' + fileName
			else:
				fileName = re.search('info: \"(.+?\..+?)[\s\"]', link).group(1)
				photoID = re.search('photoID: \"(\d{10})', link).group(1)
				fileUrl = self.get_video_storage(photoID) + photoID

			try:
				urllib.request.urlretrieve(fileUrl, os.path.join(filePath, fileName))
			except ValueError:
				print("Can't receive file.")

	def get_video_storage(self, photoId):
		if self.videoStorage:
			return self.videoStorage

		videoUrl = 'https://www.rajce.idnes.cz/ajax/videoxml.php?id=' + photoId + '/' + self.securityCode
		xml = urllib.request.urlopen(videoUrl).read()
		root = ET.fromstring(xml)
		server = root.find('items').find('item').find('linkvideo').find('server').text
		path = root.find('items').find('item').find('linkvideo').find('path').text
		self.videoStorage = server + path
		return self.videoStorage

	def validate_url(self, url):
		if url[0:8] != 'https://' and url[0:7] != 'http://':
			url = 'https://' + url

		if url[-1] != '/':
			url = url + '/'

		return url


if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument('-u', '--url', nargs='+', help="display a square of a given number")
	parser.add_argument('-p', '--path', help="display a square of a given number")
	args = parser.parse_args('-u https://pytlak-mvc.rajce.idnes.cz/2017-07-06%2C_Mikulov%2C_MCR_a_Velka_cena_WI-CZ_Pytlak/'.split())
	# args = parser.parse_args('-u http://vsevily.rajce.idnes.cz/'.split())
	# args = parser.parse_args('-u http://dolfik88.rajce.idnes.cz/'.split())

	start = time.time()
	downloader = Rajce(args.url, args.path)
	downloader.download()
	print('It took', time.time() - start, 'seconds.')
