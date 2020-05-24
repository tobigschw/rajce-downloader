# Rajce Downloader and Analyzer
Command-line program to download photos and videos from rajce.idnes.cz. 
```
rajce.py [OPTIONS] -u URL [URL ...]
```

## Options
    -h, --help                                        Show this help message and exit
    -u, --url URL [URL ...]                           URLs to download or to analyze
    -p, --path PATH                                   Destination folder
    -b, --bruteforce                                  Use brute force            
    -H, --history                                     Download only videos not listed in the
                                                      history file. Record the IDs of all
                                                      downloaded photos and videos in it
    -a, --analyze [ALBUM_TOP_SIZE, [MEDIA_TOP_SIZE]]  Analyze URLs and show, by default, top10
                                                      albums and Top50 photos based on rating. 
                                                      You can change Top sizes.    
    
## How to use
    
#### Allowed URLs for `--url` option. 
Quotes are required when URL has album credentials.
```
https://userName.rajce.idnes.cz
https://userName.rajce.idnes.cz/albumName
"https://username.rajce.idnes.cz/albumName/?login=login&code=password"
```

#### Using `--analyze` flag.  
By default, `ALBUM_TOP_SIZE` = 10 and `MEDIA_TOP_SIZE` = 50.  
So, `-a` is the same as `-a 10 50`.  
Show albums Top3 and photos Top10 - `-a 3 10`.  
Show only photos Top13 - `-a 0 13`  
```
NOTE! When you use --analyze flag script will not download files
```

## Requirements
* [Python 3.6.1+](https://www.python.org/downloads)