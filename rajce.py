import argparse
import re
import os
import logging
import json
import urllib.request
import urllib.error
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path
from multiprocessing.dummy import Pool


class Rajce:
    urls = None
    path = None
    useHistory = False

    history = []
    videoStorage = None
    securityCode = None
    storage = None
    filePath = None
    links = {}

    THREADS_COUNT = 10

    def __init__(self, urls, path=None, archive=None):
        self.setLogger()

        self.urls = urls
        self.path = Path(path) if path else Path(__file__).resolve().parent
        if archive:
            self.useHistory = True
            self.history = self.getHistory()

    def getHistory(self) -> list:
        list = []
        try:
            with open('history', 'r+') as f:
                for line in f:
                    currentPlace = line[:-1]
                    list.append(currentPlace)
        except:
            pass

        return list

    def setLogger(self):
        logging.basicConfig(
            format='%(asctime)s %(levelname)-8s %(message)s',
            datefmt='[%Y-%m-%d %H:%M:%S] :',
            filename=Path('errors.log'),
            filemode='a+',
            level=logging.INFO
        )

        formatter = logging.Formatter(fmt='%(asctime)s %(levelname)-8s %(message)s', datefmt='[%Y-%m-%d %H:%M:%S] ')
        console = logging.StreamHandler()
        console.setFormatter(formatter)
        console.setLevel(logging.INFO)

        self.logger = logging.getLogger()
        self.logger.addHandler(console)

    def getMediaLinks(self, url) -> dict:
        m = re.search('login=(.+)&password=(.+)', url)
        data = {'login': m.group(1), 'code': m.group(2)} if m else {}

        try:
            data = urllib.parse.urlencode(data).encode()
            request = urllib.request.Request(url, data=data)
            response = urllib.request.urlopen(request).read().decode('utf-8')
        except urllib.error.URLError as e:
            self.logger.error(f'Error : "{e.reason}" for url : {url}')
            return {}

        config = {}
        for line in response.splitlines(True):
            m = re.search('var (.+?) = (.+?);$', line.strip('\n\t\r '))
            if not m or m.group(1) in config: continue
            config[m.group(1)] = m.group(2).strip('"').replace("\\", "")

        if not all(k in config for k in ('albumUserName', 'albumServerDir', 'storage')):
            self.logger.error(f'Error : Some config keys not found')
            return {}

        user, album, storage = config['albumUserName'], config['albumServerDir'], config['storage']

        if 'photos' not in config:
            self.logger.error(f'Error : {user}\'s album "{album}" is empty or password protected')
            return {}

        photos = json.loads(config['photos'])
        links_dict = {
            self.path.joinpath(user, album, elem['fileName']): elem['videoStructure']['items'][1]['video'][0]['file']
            if elem['videoStructure'] else storage + 'images/' + elem['fileName'] for elem in photos
        }

        # Create album folder
        if len(links_dict) > 0:
            try:
                self.path.joinpath(user, album).mkdir(parents=True, exist_ok=True)
            except OSError as e:
                self.logger.error(f'Error "{e}" for mkdir "{user}/{album}"')
                return {}
            self.logger.info(f"{len(links_dict)} media files found in {user}'s album '{album}'")
        else:
            self.logger.info(f"No media files found in {user}'s album '{album}'")

        return links_dict

    def getAlbumsList(self, url) -> list:
        try:
            body = urllib.request.urlopen(url + '?rss=news').read()
        except urllib.error.URLError as e:
            self.logger.error(f'Error : "{e.reason}" for url : {url}')
            return []

        root = ET.fromstring(body)

        return [x.text for x in root.findall('channel/item/link')]

    def download(self):
        for url in self.urls:
            path = urllib.parse.urlparse(url).path
            if len(path.strip('/')) > 0:
                self.links.update(self.getMediaLinks(url))
            else:
                album_urls = self.getAlbumsList(url)
                for album_url in album_urls:
                    self.links.update(self.getMediaLinks(album_url))

        fileList = [x for x in self.links.keys() if
                    self.links[x] not in self.history] if self.useHistory else self.links.keys()

        self.logger.info(f'{len(fileList)} new files found')
        if len(fileList) == 0: return

        self.logger.info('Start')
        p = Pool(self.THREADS_COUNT)
        with open('history', 'a+') as f:
            for url in p.imap(self.downloadFile, fileList):
                if self.useHistory and url:
                    f.write(f"{url}\n")
        self.logger.info('Finish')

    def downloadFile(self, file):
        url = self.links[file]
        print(f'Downloading "{url}"')
        try:
            urllib.request.urlretrieve(url, file)
        except urllib.error.HTTPError as e:
            self.logger.error(f'HTTPError : "{e.reason}" for url : {url}')
            return False
        except urllib.error.ContentTooShortError as e:
            self.logger.error(f'ContentTooShortError : "{e.reason}" for url : {url}')
            return False
        except urllib.error.URLError as e:
            self.logger.error(f'URLError : "{e.reason}" for url : {url}')
            return False

        return url


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--url', help="List of URLs", nargs='+', required=True)
    parser.add_argument('-p', '--path', help="Destination folder")
    parser.add_argument('-a', '--archive', help="Downloaded URLs archive", action='store_true')
    args = parser.parse_args()
    downloader = Rajce(args.url, args.path, args.archive)

    downloader.download()
