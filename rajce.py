import argparse
import re
import os
import urllib.request
import xml.etree.ElementTree as ET

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
			m = re.search('(\w*)\.rajce.idnes.cz/(\w*)', url)
			if not m:
				print('Wrong url!')
			elif not m.group(2):
				self.download_gallery(url)
			else:
				self.download_album(url)

	def download_gallery(self, galleryUrl):
		print(galleryUrl)

	def download_album(self, albumUrl):
		html = urllib.request.urlopen(albumUrl).read().decode('utf-8')

		storage = re.findall('var storage = "(.*)";', html)[0]
		self.securityCode = re.findall('var albumSecurityCode = \"(.*)\";', html)[0]

		links = re.findall('{ (photoID: \".*)}', html)
		if not links:
			print('No photo found.')
			return

		m = re.search('(\w*)\.rajce.idnes.cz/(\w*)', albumUrl)
		filePath = os.path.join(m.group(1), m.group(2))
		os.makedirs(filePath, exist_ok=True)

		for link in links:
			fileName = re.search('info: \"(.+?\..+?)[\s\"]', link).group(1)

			if re.search('isVideo: (.*), desc', link).group(1) == 'false':
				fileUrl = storage + 'images/' + fileName
			else:
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


if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument('-u', '--url', nargs='+', help="display a square of a given number")
	parser.add_argument('-p', '--path', help="display a square of a given number")
	args = parser.parse_args('-u https://pytlak-mvc.rajce.idnes.cz/2017-07-06%2C_Mikulov%2C_MCR_a_Velka_cena_WI-CZ_Pytlak/'.split())

	downloader = Rajce(args.url, args.path)
	downloader.download()
