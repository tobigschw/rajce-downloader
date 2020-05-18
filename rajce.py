import argparse
import re
import sys
import logging
import json
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path
from multiprocessing.dummy import Pool
from time import gmtime, strftime


class Rajce:
    urls = None
    path = None
    useHistory = False
    useBruteForce = False

    history = []
    videoStorage = None
    securityCode = None
    storage = None
    filePath = None
    links = {}
    root = Path(__file__).resolve().parent

    THREADS_COUNT = 10

    def __init__(self, urls, path=None, archive=None, bruteforce=None):
        self.setLogger()

        self.urls = urls
        self.path = Path(path) if path else self.root
        self.useBruteForce = bruteforce
        if archive:
            self.useHistory = True
            self.history = self.getHistory()

    def getHistory(self) -> list:
        list = []
        try:
            with open(self.root.joinpath('history'), 'r+') as f:
                for line in f:
                    currentPlace = line[:-1]
                    list.append(currentPlace)
        except:
            return []

        return list

    def setLogger(self):
        logging.basicConfig(
            format='%(asctime)s %(levelname)-8s %(message)s',
            datefmt='[%Y-%m-%d %H:%M:%S] :',
            filename=self.root.joinpath('errors.log'),
            filemode='a+',
            level=logging.INFO
        )

        formatter = logging.Formatter(fmt='%(asctime)s %(levelname)-8s %(message)s', datefmt='[%Y-%m-%d %H:%M:%S] ')
        console = logging.StreamHandler()
        console.setFormatter(formatter)
        console.setLevel(logging.INFO)

        self.logger = logging.getLogger()
        self.logger.addHandler(console)

    def getAlbumConfig(self, response) -> dict:
        config = {}
        for line in response.splitlines(True):
            m = re.search('var (.+?) = (.+?);$', line.strip('\n\t\r '))
            if not m or m.group(1) in config: continue
            config[m.group(1)] = m.group(2)

        return config

    def bruteForce(self, url) -> str:
        url = urllib.request.urlopen(url).geturl()
        url = url.split('?')[0].strip('/')

        self.logger.info(f'Try bruteforcing url "{url}"')

        nameList = [
            urllib.parse.urlsplit(url).netloc.split('.')[0],
            urllib.parse.urlsplit(url).path.strip('/'),
        ]
        # nameList += urllib.parse.urlsplit(url).path.strip('/').split('_')
        # nameList += [x.lower() for x in urllib.parse.urlsplit(url).path.strip('/').split('_')]

        pwrdList = nameList = list(set(nameList))

        for login in nameList:
            for password in pwrdList:
                try:
                    response = self.getUrl(url + f'/?login={login}&password={password}')
                except urllib.error.URLError as e:
                    self.logger.error(f'Bruteforce error : "{e.reason}" for url : {url}')
                    continue

                config = self.getAlbumConfig(response)
                if 'photos' in config:
                    self.logger.info(f'Bruteforce success with {login}:{password}')
                    return response

        return ''

    def getUrl(self, url) -> str:
        data = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query))
        data = urllib.parse.urlencode(data).encode()
        request = urllib.request.Request(url, data=data)

        return urllib.request.urlopen(request).read().decode('utf-8')

    def getMediaLinks(self, url) -> dict:
        try:
            response = self.getUrl(url)
        except urllib.error.URLError as e:
            self.logger.error(f'Error : "{e.reason}" for url : {url}')
            return {}
        config = self.getAlbumConfig(response)

        if 'photos' not in config and self.useBruteForce:
            response = self.bruteForce(url)
            config = self.getAlbumConfig(response) if len(response) > 0 else config

        # Parse user, album, storage
        if not all(k in config for k in ('albumUserName', 'albumServerDir', 'storage')):
            self.logger.error(f'Error : Config keys not found')
            return {}
        user, album, storage = config['albumUserName'], config['albumServerDir'], config['storage']

        # Parse photos array
        if 'photos' not in config:
            self.logger.error(f'Error : {user}\'s album "{album}" is empty or password protected')
            return {}
        photos = json.loads(config['photos'])

        links_dict = {
            self.path.joinpath(user, album, elem['info'].split(' | ')[0]): elem['videoStructure']['items'][1]['video'][0]['file']
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

    def getMediaRatings(self, url) -> tuple:
        try:
            urlopen = urllib.request.urlopen(url)
            url = urlopen.geturl()
            response = urlopen.read().decode('utf-8')
        except urllib.error.URLError as e:
            self.logger.error(f'Error : "{e.reason}" for url : {url}')
            return {}, {}
        config = self.getAlbumConfig(response)

        if 'photos' not in config and self.useBruteForce:
            response = self.bruteForce(url)
            config = self.getAlbumConfig(response) if len(response) > 0 else config

        # Parse user, album, storage
        if not all(k in config for k in ('albumUserName', 'albumServerDir', 'storage')):
            self.logger.error(f'Error : Config keys not found')
            return {}, {}
        user, album, storage = config['albumUserName'], config['albumServerDir'], config['storage']

        # Parse photos array
        if 'photos' not in config:
            self.logger.error(f'Error : {user}\'s album "{album}" is empty or password protected')
            return {}, {}
        photos = json.loads(config['photos'].encode('utf-8'))

        links_dict = {url.strip('/') + '/' + elem['photoID']: int(elem['rating']) for elem in photos}

        # Create album folder
        if len(links_dict) > 0:
            self.logger.info(f"{len(links_dict)} media files found in {user}'s album '{album}'")
        else:
            self.logger.info(f"No media files found in {user}'s album '{album}'")

        config['albumRating'] = int(config['albumRating'])
        return {url: config['albumRating']}, links_dict

    def getAlbumsList(self, url) -> list:
        url = urllib.parse.urljoin(url, 'services/web/get-albums.json')
        offset = 1
        limit = 50
        albums = []

        while True:
            data = {'offset' : offset - 1, 'limit' : limit}

            data = urllib.parse.urlencode(data).encode()
            request = urllib.request.Request(url, data=data)
            try:
                content = urllib.request.urlopen(request).read().decode('utf-8')
            except urllib.error.URLError as e:
                self.logger.error(f'Error : "{e.reason}" for url : {url}')
                break

            content = json.loads(content)

            if len(content['result']['data']) == 0:
                break

            albums += [x['permalink'] for x in content['result']['data']]

            offset += limit

        return albums

    def downloadFile(self, file):
        url = self.links[file]
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

    def downloadAlbum(self, url):
        self.links = self.getMediaLinks(url)
        if len(self.links) == 0: return

        fileList = [x for x in self.links.keys() if
                    self.links[x] not in self.history] if self.useHistory else self.links.keys()

        self.logger.info(f'{len(fileList)} new files found')
        if len(fileList) == 0: return

        self.logger.info('Begin downloading')
        ttl = len(fileList)
        dld = 0
        barLen = 50
        timestamp = strftime("%Y-%m-%d %H:%M:%S", gmtime())

        p = Pool(self.THREADS_COUNT)
        with open(self.root.joinpath('history'), 'a+') as f:
            for url in p.imap(self.downloadFile, fileList):
                if url:
                    dld += 1
                    block = int(barLen * dld / ttl)
                    sys.stdout.write(f"\r[{timestamp}] [{dld}/{ttl}] [{'#'*block}{'-'*(barLen-block)}]")
                    sys.stdout.flush()
                if self.useHistory and url:
                    f.write(f"{url}\n")
        print("\r")
        self.logger.info('Finish downloading')

    def isAlbum(self, url):
        return len(urllib.parse.urlparse(url).path.strip('/')) > 0

    def download(self):
        for url in self.urls:
            if self.isAlbum(url):
                self.downloadAlbum(url)
            else:
                albumUrls = self.getAlbumsList(url)
                for albumUrl in albumUrls:
                    self.downloadAlbum(albumUrl)

    def analyze(self, albumCount = 10, mediaCount = 50):
        albums = {}
        media = {}
        for url in self.urls:
            if self.isAlbum(url):
                ta, tm = self.getMediaRatings(url)
                albums.update(ta)
                media.update(tm)
            else:
                albumUrls = self.getAlbumsList(url)
                for albumUrl in albumUrls:
                    ta, tm = self.getMediaRatings(albumUrl)
                    albums.update(ta)
                    media.update(tm)

        print(f'Album\'s top {albumCount}')

        for url, rating in sorted(albums.items(), reverse=True, key=lambda item: item[1])[:albumCount]:
            print(rating , url)

        print(f'Photos and videos top {mediaCount}')

        for url, rating in sorted(media.items(), reverse=True, key=lambda item: item[1])[:mediaCount]:
            print(rating , url)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--url', help="List of URLs", nargs='+', required=True)
    parser.add_argument('-p', '--path', help="Destination folder")
    parser.add_argument('-a', '--archive', help="Downloaded URLs archive", action='store_true')
    parser.add_argument('-b', '--bruteforce', help="Use bruteforce", action='store_true')
    parser.add_argument('-i', '--info', help="Analyze URL", action='store_true')
    args = parser.parse_args()

    if args.info: Rajce(args.url, args.path, args.archive, args.bruteforce).analyze(10,50)
    else: Rajce(args.url, args.path, args.archive, args.bruteforce).download()