# crawlAllLinks
A crawler based on findAllLinks


# RUN IT 
```bash
docker run -it --rm  -v "/tmp:/tmp" elsicarius/crawl_all_links:latest [--paramssss] <url> 
```

# usage

```
usage: crawlalllinks.py [-h] [-q] [-mf MAX_FAILS] [-mv MAX_VISITS] [-m {sub,lax,strict}] [-H HEADER] [--timeout TIMEOUT] [-ch] [-fm {map,bak}] [-r RESTRICT_EXTS] [-rs] url

Crawl all links from a webpage

positional arguments:
  url                   URL to crawl

options:
  -h, --help            show this help message and exit
  -q, --quiet           Shut the f up and output only the urls
  -mf MAX_FAILS, --max-fails MAX_FAILS
                        max fails before stopping
  -mv MAX_VISITS, --max-visits MAX_VISITS
                        max visits before stopping
  -m {sub,lax,strict}, --mode {sub,lax,strict}
                        Crawling mode
  -H HEADER, --header HEADER
                        Headers to send
  --timeout TIMEOUT     Timeout for fetching web page
  -ch, --chrome-headless
                        Use a headless browser to run the crawler
  -fm {map,bak}, --find-more {map,bak}
                        Try some techniques to get more interesting results
  -r RESTRICT_EXTS, --restrict-exts RESTRICT_EXTS
                        Restrict extensions to these
  -rs, --remove_siblings
                        Clean te output bu filtering statuscode and len to keep only 1 reprensative of each status-len
```

# Good example

```
docker run -it --rm -v "/tmp:/tmp" elsicarius/crawl_all_links:latest -fm map -mv 1000 https://elsicarius.fr -rs
```