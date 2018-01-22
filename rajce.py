import argparse
import re
import os
import urllib.request
import urllib.error
import urllib.parse
import xml.etree.ElementTree as ET
import time
from multiprocessing.dummy import Pool


class Rajce:
    urls = None
    path = None
    videoStorage = None
    securityCode = None
    storage = None
    filePath = None

    THREADS_COUNT = 15

    def __init__(self, urls, path=None):
        self.urls = urls
        self.path = path

    def download(self):
        for url in self.urls:
            url = self.correct_url(url)
            m = re.search('([\w-]+?)\.rajce\.idnes\.cz/((.*)|)', url)
            if not m:
                print(url + ' - Wrong url!')
            elif m.group(2) == '':
                self.download_gallery(url)
            else:
                self.download_album(url)

    def download_gallery(self, galleryUrl):
        html = urllib.request.urlopen(galleryUrl).read().decode('utf-8')

        pageList = [int(x) for x in re.findall('sort=\w+?&page=(\d+)', html)]
        sortType = re.search('sort=(\w+?)&page=\d+', html).group(1)
        page = int(max(pageList)) if pageList else 0

        user = re.search('([\w-]+?)\.rajce\.idnes\.cz/', galleryUrl).group(1)

        while page >= 0:
            regex = '(' + user + '\.rajce\.idnes\.cz/.*?/)\">'
            albums = re.findall(regex, html)
            if not albums:
                print(galleryUrl + ' - No albums found!')
                return

            for album in albums:
                self.download_album(self.correct_url(album))

            if page > 0:
                pageUrl = galleryUrl + '?listType=&sort=' + sortType + '&page=' + str(page)
                html = urllib.request.urlopen(pageUrl).read().decode('utf-8')

            page = page - 1

    def download_album(self, albumUrl):
        html = urllib.request.urlopen(albumUrl).read().decode('utf-8').replace("\\", "")

        storage = re.search('var storage = "(.*)";', html)
        if not storage:
            print(albumUrl + ' - No photo found or locked album!')
            return

        self.videoStorage = None
        self.storage = storage.group(1)
        self.securityCode = re.search('var albumSecurityCode = \"(.*)\";', html).group(1)

        links = re.findall('{(\"photoID\".*?)}', html)
        if not links:
            print(albumUrl + ' - No photo found!')
            return

        m = re.search('([\w-]+?)\.rajce\.idnes\.cz/(.*?)/', albumUrl)
        self.filePath = os.path.join(self.path if self.path else '', m.group(1), m.group(2).replace('.', '_'))
        os.makedirs(self.filePath, exist_ok=True)

        pool = Pool(self.THREADS_COUNT)
        pool.map(self.download_file, links)
        pool.close()
        pool.join()

        print(albumUrl + ' - OK!')

    def download_file(self, fileUrl):
        if re.search('\"isVideo\":(.*),\"desc', fileUrl).group(1) == 'false':
            fileName = re.search('\"fileName\":\"(.+?)\"', fileUrl).group(1)
            fileUrl = self.storage + 'images/' + fileName
        else:
            fileName = re.search('\"info\":\"(.+?\..+?)[\s\"]', fileUrl).group(1)
            photoID = re.search('\"photoID\":\"(\d+)', fileUrl).group(1)
            if not self.videoStorage:
                self.get_video_storage(photoID)
            fileUrl = self.videoStorage + photoID

        try:
            urllib.request.urlretrieve(fileUrl, os.path.join(self.filePath, fileName))
        except urllib.error.URLError as e:
            print("Can't receive " + fileName + " '" + fileUrl + "' with " + e.reason)

    def get_video_storage(self, photoId):
        videoUrl = 'https://www.rajce.idnes.cz/ajax/videoxml.php?id=' + photoId + '/' + self.securityCode
        xml = urllib.request.urlopen(videoUrl).read()
        root = ET.fromstring(xml)
        server = root.find('items').find('item').find('linkvideo').find('server').text
        path = root.find('items').find('item').find('linkvideo').find('path').text
        self.videoStorage = server + path

    def correct_url(self, url):
        url = urllib.parse.quote_plus(url.replace("\"", ""), ':/&?=')

        if url[0:8] != 'https://' and url[0:7] != 'http://':
            url = 'https://' + url

        if url[-1] != '/' and url.find("?") == -1:
            url = url + '/'

        return url


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--url', help="List of URLs", nargs='+', required = True)
    parser.add_argument('-p', '--path', help="Destination folder")
    args = parser.parse_args()
    downloader = Rajce(args.url, args.path)
    downloader.download()
