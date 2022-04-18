# crawlAllLinks
A crawler based on findAllLinks


# RUN IT 
```bash
docker run -it --rm  -v "/tmp:/tmp" elsicarius/crawl_all_links:latest <url> [--paramssss]
```

# usage

```
usage: crawlalllinks.py [-h] [--max-fails MAX_FAILS] [--max-visits MAX_VISITS] [-m {sub,lax,strict}] url

Crawl all links from a webpage

positional arguments:
  url                   URL to crawl

optional arguments:
  -h, --help            show this help message and exit
  --max-fails MAX_FAILS
                        max fails before stopping (default: 10)
  --max-visits MAX_VISITS
                        max visits before stopping (default: 100)
  -m {sub,lax,strict}, --mode {sub,lax,strict}
                        Crawling mode (default: sub)
```