import asyncio
from pyppeteer import launch
from subprocess import check_output
from loguru import logger
from urllib.parse import urlparse, urlunparse
import re
import requests
import argparse
import os
import signal
import sys

findAllLinksv2= '''"(?:\\"|')([\w]{2,10}:[\\\/]+[\w\d\*\_\-\.\:]+)?((([\\\/]+)([\.\w\d\_\-\:]+)((?![\.\w\d\_\-\:]+)[\\\/]+)?)+|(([\.\w\d\_\-\:]+)([\\\/]+)((?![\\\/]+)[\.\w\d\_\-\:]+)?)+)?(\?([\w\d\-\_\;{}()\[\]]+(\=([^&,\s]+(\&)?)?)?){0,})?(?:\\"|')"'''

GARBAGE_EXTENSIONS = [
    "ico",
    "woff",
    "woff2",
    "ttf",
    "otf",
    "eot",
    "jpg",
    "jpeg",
    "png",
    "gif",
    "svg",
    "pdf",
    "doc",
    "docx",
    "xls",
    "xlsx",
    "ppt",
    "pptx",
    "zip",
    "rar",
    "7z",
    "tar",
    "gz",
    "bz2",
    "tgz",
    "xz",
]

class Web():
    def __init__(self, pyppeteer_args={"headless": True, "ignoreHTTPSErrors": True, "handleSIGTERM": False, "handleSIGINT": False, "devtools": True, "args": ['--no-sandbox']},):
        self.pyppeteer_args = pyppeteer_args
        self.pages = list()
        self.results = dict()
        self.mime_types = self.get_mime_types()
    
    def get_mime_types(self):
        # iana mimes
        mimes_csv = requests.get("https://www.iana.org/assignments/media-types/application.csv").text
        mimes = mimes_csv.split("\n")
        mimes = [m.split(",")[1].strip() for m in mimes if len(m.split(",")) > 1]

        # custom mimes
        mimes2_csv = requests.get("https://gist.githubusercontent.com/electerious/3d5a31a73cfd6423f835c074ab25fc06/raw/d48b8410e9aa6746cfd946bca21a1bb54c351c4e/Caddyfile").text
        mimes2 = re.findall("[\w\d\+\-\_]+/[\w\d\+\-\_]+", mimes2_csv)
        mimes.extend(mimes2)

        # personal mimes
        mimes3 = ["text/javascript", "text/xml"]
        mimes.extend(mimes3)

        return mimes
    
    async def start_browser(self,):
        self.browser = await launch(self.pyppeteer_args)
    
    async def new_page(self):
        self.pages.append(await self.browser.newPage())
        id_ = len(self.pages) - 1
        self.results.setdefault(id_, dict())
        return id_
    
    async def page_goto(self, id, url):
        try:
            p = await self.pages[id].goto(url, waitUntil="networkidle2")
        except Exception as e:
            logger.error(f"Error: {e}")
            return False
        self.results[id]["url"] = url
        return p
    
    async def get_page_content(self, id):
        body = await self.pages[id].content()
        self.results[id]["body"] = body
        return body
    
    async def close_browser(self):
        await self.browser.close()
    
    async def screenshot_page(self, id, path):
        await self.pages[id].screenshot({'path': f"/tmp/{path}.png"})

class Crawl():
    def __init__(self, web, url):
        self.init_url = url
        self.web = web
        self.fails = set()
        self.visited = set()
        self.queue = set()
        self.results_pages = dict()
        self.queue.add(url)
    
    def find_all_links_v2(self, id_):
        # uses grep to find all links in the saved page, as python's "re" is very slow (because of the [^&,\s] at the end of the regex)
        return check_output(f"grep -Pao {findAllLinksv2} /tmp/crawlalllinks/{id_}.txt | sed \"s/[\\\"|']//g\"  | sort -uV", shell=True, executable='/bin/bash').decode("utf-8")
    
    async def visit_n_parse(self, id_, url):
        p = await self.web.page_goto(id_, url)
        if not p:
            self.fails.add(url)
            self.results_pages[url] = {
                "status": "000",
                "url": url,
                "headers": {},
                "len": 0,
            }
        else:
            self.visited.add(url)
        self.queue.discard(url)
        content = await self.web.get_page_content(id_)
        self.results_pages[url] = {
                "status": p.status,
                "url": p.url,
                "headers": p.headers,
                "len": len(content),
            }
        with open(f"/tmp/crawlalllinks/{id_}.txt", "w") as f:
            f.write(content)
        links = self.find_all_links_v2(id_)
        self.web.results[id_]["links"] = links
        return links
    
    def add_queue(self, links: set):
        for link in links:
            if link not in self.visited and link not in self.fails :
                self.queue.add(link)
    
    def print_status(self):
        print(self)
    
    def write_results(self):
        with open(f"/tmp/crawlalllinks/results_{self.init_url.replace('/','_').replace(':','.')}.txt", "w+") as f:
            f.write(self.return_results_formatted())
    
    def __str__(self):
        cr = "\n"
        return f"""Fails: {len(self.fails)} - Visited: {len(self.visited)} - Queue: {len(self.queue)}"""

    def return_results_formatted(self):
        content = str()
        res_sorted = {k: self.results_pages[k] for k in sorted(self.results_pages, key=lambda element: (self.results_pages[element]["status"], self.results_pages[element]["len"]))}
        for url, response in res_sorted.items():
            content += f"""{response["status"]} | {response["len"]} | {response["url"]}\n"""
        return content
    
class Link(object):

    def __init__(self, link, base_url):
        self.link = link
        self.full_url = base_url
        self.full_url_parsed = urlparse(self.full_url)
        self.recreated_link = str()


    def get_link_type(self):
        self.state = "unknown"
        if self.link.startswith("http"):
            self.state = "url_absolute"
        elif re.findall("^[\w\d\-]+\.[\w\-\d](:[\d]+)?([/\\\]+.*)?", self.link):
            self.state = "url_relative"
        elif re.findall("^[/\\\]+", self.link):
            self.state = "path_absolute"
        elif re.findall("^[\.\w\d\-\_]+", self.link):
            self.state = "path_relative"
        return self.state
    
    def format_link(self):
        if self.state == "url_absolute":
            self.recreated_link = self.link
        elif self.state == "url_relative":
            self.recreated_link = f"{self.full_url.split('://')[0]}://{self.link}"
        elif self.state == "path_absolute":
            self.recreated_link = urlunparse(self.full_url_parsed._replace(path=self.link))
        elif self.state == "path_relative":
            sep = "/" if not self.full_url_parsed.path.endswith("/") and not self.link.startswith("/") else ""
            self.recreated_link = urlunparse(self.full_url_parsed._replace(path=f'{self.full_url_parsed.path}{sep}{self.link}'))
        return self.recreated_link
    
    def has_garbage_extension(self):

        path = urlparse(self.recreated_link).path.lower()
        if len(path.split(".")) < 1:
            return False
        ext = path.split(".")[-1]
        if ext in GARBAGE_EXTENSIONS:
            return True
        return False


async def main(args):
    veb = Web()
    crawler = Crawl(web=veb, url=args.url)

    init_url_parsed = urlparse(args.url)
    await veb.start_browser()

    def signal_handler(sig, frame):
        logger.warning(f"Caught ctrl+c, saving results...")
        crawler.write_results()
        print(crawler.return_results_formatted())
        exit(1)
        
    signal.signal(signal.SIGINT, signal_handler)

    id_ = await veb.new_page()
    await crawler.visit_n_parse(id_, crawler.init_url)
    
    def get_next_urls():
        urls = set()
        for link in veb.results[id_]["links"].split("\n"):
            link = link.strip()
            if link in veb.mime_types:
                # logger.warning(f"Link looks like a mime type: {link}, ignoring")
                continue
            
            link_ = Link(link, crawler.init_url)
            type_of_link = link_.get_link_type()
            if type_of_link == "unknown":
                # logger.warning(f"Link type is unknown: {link}, ignoring")
                continue
            
            full_url = link_.format_link()

            if link_.has_garbage_extension():
                logger.warning(f"Link has a garbage extension: {link}, ignoring")
                # adding to visited to keep track of links that are not useful
                crawler.visited.add(full_url)
                continue

            # print(f"{link} - {type_of_link} - {full_url}")

            if args.mode == "sub" and ".".join(urlparse(full_url).netloc.split(".")[-2:]) == ".".join(init_url_parsed.netloc.split(".")[-2:]):
                urls.add(full_url)
            if args.mode == "strict" and urlparse(full_url).netloc == init_url_parsed.netloc:
                urls.add(full_url)
            if args.mode == "lax":
                urls.add(full_url)
        return urls
    
    crawler.add_queue(get_next_urls())
    logger.debug("Init page crawled, crawling subpages now")
    while len(crawler.queue) > 0 and len(crawler.fails) < args.max_fails and len(crawler.visited | crawler.fails) < args.max_visits:
        url = crawler.queue.pop()
        logger.debug(f"Next page to crawl: {url}")

        await crawler.visit_n_parse(id_, url)
        crawler.add_queue(get_next_urls())
        crawler.print_status()
    
    await veb.close_browser()

    crawler.write_results()
    print(crawler.return_results_formatted())

def get_arguments():
    parser = argparse.ArgumentParser(description="Crawl all links from a webpage")
    parser.add_argument("url", type=str, help="URL to crawl")
    parser.add_argument("--max-fails", type=int, help="max fails before stopping", default=10)
    parser.add_argument("--max-visits", type=int, help="max visits before stopping", default=100)
    parser.add_argument("-m", "--mode", type=str, help="Crawling mode", default="sub", choices=["sub", "lax", "strict"])

    return parser.parse_args()


if __name__ == "__main__":
    if not os.path.exists("/tmp/crawlalllinks"):
        os.mkdir("/tmp/crawlalllinks")
    args = get_arguments()
    asyncio.get_event_loop().run_until_complete(main(args))
