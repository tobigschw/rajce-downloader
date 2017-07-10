import argparse
import re
import urllib.request

class Rajce:
	urls = None
	path = None

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
		m = re.findall('{ (photoID: \".*)}', html)
		if not m:
			print('No photo found.')
			return


if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument('-u', '--url', nargs='+', help="display a square of a given number")
	parser.add_argument('-p', '--path', help="display a square of a given number")
	args = parser.parse_args('-u http://www.google.com/ https://docs.python.org/ http://schwarmer.rajce.idnes.cz/Montas http://angel.rajce.idnes.cz/'.split())

	downloader = Rajce(args.url, args.path)
	downloader.download()
