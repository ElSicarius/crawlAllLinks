import asyncio
from distutils import extension
from pyppeteer import launch
from subprocess import check_output
from loguru import logger
from urllib.parse import urlparse, urlunparse
import re
import requests
import argparse
import os
import signal

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

findAllLinksv2= '''"(?:\\"|')([\w]{2,10}:[\\\/]+[\w\d\*\_\-\.\:]+)?((([\\\/]+)([\.\w\d\_\-\:]+)((?![\.\w\d\_\-\:]+)[\\\/]+)?)+|(([\.\w\d\_\-\:]+)([\\\/]+)((?![\\\/]+)[\.\w\d\_\-\:]+)?)+)?(\?([\w\d\-\_\;{}()\[\]]+(\=([^&,\s]+(\&)?)?)?){0,})?(?:\\"|')"'''
findAllLinksv3 = '''"([\w]{2,10}:([\\\/]|[%]+(25)?2[fF])+[\w\d\*\_\-\.\:]+)?(((([\\\/]|[%]+(25)?2[fF])+)([\.\w\d\_\-\:]+)((?![\.\w\d\_\-\:]+)(([\\\/]|[%]+(25)?2[fF])+))?)+((([\.\w\d\_\-\:]+)(([\\\/]|[%]+(25)?2[fF])+)((?!([\\\/]|[%]+(25)?2[fF])+)[\.\w\d\_\-\:]+)?)+))?((\?|[%]+(25)?3[Ff])([\w\d\-\_\;{}\(\)\[\]]+((\=|[%]+(25)?3[dD])([^&,\s]+(\&)?)?)?){0,})?"'''
findAllLinksv3_quotes = '''"(?:\\"|\')([\w]{2,10}:([\\\/]|[%]+(25)?2[fF])+[\w\d\*\_\-\.\:]+)?(((([\\\/]|[%]+(25)?2[fF])+)([\.\w\d\_\-\:]+)((?![\.\w\d\_\-\:]+)(([\\\/]|[%]+(25)?2[fF])+))?)+((([\.\w\d\_\-\:]+)(([\\\/]|[%]+(25)?2[fF])+)((?!([\\\/]|[%]+(25)?2[fF])+)[\.\w\d\_\-\:]+)?)+))?((\?|[%]+(25)?3[Ff])([\w\d\-\_\;{}\(\)\[\]]+((\=|[%]+(25)?3[dD])([^&,\s]+(\&)?)?)?){0,})?(?:\\"|\')"'''

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
retrieved_links = set()

class Handlers():
    def __init__(self, new_headers={}):
        self.new_headers = {k.lower(): v for k,v in new_headers.items()}

    def request_handler(self, request):
        for k, v in self.new_headers.items():
            request.headers.setdefault(k, v)
            request.headers[k] = self.new_headers[k]
        asyncio.create_task(request.continue_({
        "headers": request.headers,
    }))

class Web_classic():

    base_headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.60 Safari/537.36"
    }

    def __init__(self, forced_headers = {}, timeout=30):
        self.page = None
        self.results = dict()
        self.forced_headers = forced_headers
        self.timeout = timeout
        self.mime_types = self.get_mime_types()
        self.load_headers()
    
    def load_headers(self):
        self.headers = self.base_headers.update(self.forced_headers)
    
    def get_mime_types(self):
        # iana mimes
        mimes_csv = requests.get("https://www.iana.org/assignments/media-types/application.csv", verify=False).text
        mimes = mimes_csv.split("\n")
        mimes = [m.split(",")[1].strip() for m in mimes if len(m.split(",")) > 1]

        # custom mimes
        mimes2_csv = requests.get("https://gist.githubusercontent.com/electerious/3d5a31a73cfd6423f835c074ab25fc06/raw/d48b8410e9aa6746cfd946bca21a1bb54c351c4e/Caddyfile", verify=False).text
        mimes2 = re.findall("[\w\d\+\-\_]+/[\w\d\+\-\_]+", mimes2_csv)
        mimes.extend(mimes2)

        # personal mimes
        mimes3 = ["text/javascript", "text/xml"]
        mimes.extend(mimes3)

        return mimes
    
    def start_browser(self,):
        self.browser = requests.Session()
    
    def page_goto(self, id, url):
        if not url:
            return False
        try:
            self.page = requests.get(url, timeout=self.timeout, headers=self.headers, verify=False)
        except Exception as e:
            logger.error(f"Error: {e}")
            if not url.startswith("https") and url.startswith("http"):
                logger.info(f"Trying https for {url}")
                return self.page_goto(id, f"https{url[4:]}")
            else:
                logger.critical("Url does not start with \"http\" :/")
            return False
        self.results["url"] = url
        return self.page
    
    def get_page_content(self, id):
        try:
            body = self.page.text
        except AttributeError:
            logger.error(f"Error :/ page is not defined ? requets failed ?")
            body= ""
        self.results["body"] = body
        return body

class Web_headless():
    def __init__(self, forced_headers = {}, 
            timeout=30,
            pyppeteer_args={"headless": True, "ignoreHTTPSErrors": True, "handleSIGTERM": False, "handleSIGINT": False, "executablePath": "/usr/bin/chromium-browser", "devtools": False, "args": ["--no-sandbox"]},):
            
        self.pyppeteer_args = pyppeteer_args
        self.pages = list()
        self.results = dict()
        self.forced_headers = forced_headers
        self.timeout = timeout
        self.Handlers = Handlers(new_headers=forced_headers)
        self.mime_types = self.get_mime_types()
    
    def get_mime_types(self):
        # iana mimes
        mimes_csv = requests.get("https://www.iana.org/assignments/media-types/application.csv", verify=False).text
        mimes = mimes_csv.split("\n")
        mimes = [m.split(",")[1].strip() for m in mimes if len(m.split(",")) > 1]

        # custom mimes
        mimes2_csv = requests.get("https://gist.githubusercontent.com/electerious/3d5a31a73cfd6423f835c074ab25fc06/raw/d48b8410e9aa6746cfd946bca21a1bb54c351c4e/Caddyfile", verify=False).text
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
        await self.pages[id_].setViewport({'width': 1920, 'height': 1080})
        # set request handler to override headers when request
        await self.pages[id_].setRequestInterception(True)
        self.pages[id_].on("request", self.Handlers.request_handler)

        self.pages[id_].setDefaultNavigationTimeout(self.timeout * 1000)

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
    def __init__(self, web, url, regex, restricted_exts=None):
        self.init_url = url
        self.web = web
        self.regex = regex
        self.fails = set()
        self.visited = set()
        self.queue = set()
        self.results_pages = dict()
        self.restricted_exts = restricted_exts
        self.queue.add(url)
    
    def find_all_links_v3(self, id_):
        # uses pcregrep to find all links in the saved page, as python's "re" is very slow (because of the [^&,\s] at the end of the regex)
        # we set bit limits to prevent error while grepping links
        return check_output(f"pcregrep --match-limit 1000000000 --buffer-size 10000000 --recursion-limit 1000000000 -ao {self.regex} /tmp/crawlalllinks/{id_}.txt | sed \"s/[\\\"|']//g\"  | sort -uV", shell=True, executable='/bin/bash').decode("utf-8")
    
    def visit_n_parse_classic(self, id_, url):
        if url is None:
            return set()
        p = self.web.page_goto(id_, url)
        if p is None:
            self.add_failed({url})
        else:
            self.add_visited({url}, status=p.status_code, headers=p.headers)
        self.queue.discard(url)
        content = self.web.get_page_content(id_)
        self.results_pages[url]["len"] = len(content)
        with open(f"/tmp/crawlalllinks/{id_}.txt", "w") as f:
            f.write(content)
        links = self.find_all_links_v3(id_)
        for link in links.splitlines():
            retrieved_links.add(link)
        return set(links.splitlines())
    
    async def visit_n_parse_headless(self, id_, url):
        p = await self.web.page_goto(id_, url)
        if not p:
            self.add_failed({url})
        else:
            self.add_visited({url}, status=p.status, headers=p.headers)
        self.queue.discard(url)
        content = await self.web.get_page_content(id_)
        self.results_pages[url]["len"] = len(content)
        with open(f"/tmp/crawlalllinks/{id_}.txt", "w") as f:
            f.write(content)
        links = self.find_all_links_v3(id_)
        for link in links.splitlines():
            retrieved_links.add(link)
        return set(links.splitlines())
    
    def add_queue(self, links: set):
        for link in links:
            if link not in self.visited and link not in self.fails :
                self.queue.add(link)
                self.results_pages.setdefault(link, dict({
                "status": 0,
                "url": link,
                "headers": {},
                "len": 0,
            }))
    
    def add_visited(self, links: set, status: int=0, headers: dict={}, len_: int=0):
        for link in links:
            self.results_pages[link] = {
                "status": status,
                "url": link,
                "headers": headers,
                "len": len_,
            }
            self.visited.add(link)
    
    def add_failed(self, links: set, status: int=0, headers: dict={}, len_: int=0):
        for link in links:
            self.results_pages[link] = {
                "status": status,
                "url": link,
                "headers": headers,
                "len": len_,
            }
            self.fails.add(link)
    
    def print_status(self):
        print(self)
    
    def write_results(self):
        with open(f"/tmp/crawlalllinks/results_{self.init_url.replace('/','_').replace(':','.')}.txt", "w+") as f:
            f.write(self.return_results_formatted())
    
    def __str__(self):
        return f"""Fails: {len(self.fails)} - Visited: {len(self.visited)} - Queue: {len(self.queue)}"""

    def return_results_formatted(self):
        content = str()
        res_sorted = {k: self.results_pages[k] for k in sorted(self.results_pages, key=lambda element: (self.results_pages[element]["status"], self.results_pages[element]["len"]))}
        for response in res_sorted.values():
            link_ = Link(response["url"], response["url"])
            link_.state = "url_absolute"
            link_.format_link()
            if self.restricted_exts is not None and link_.get_link_extension() not in self.restricted_exts:
                continue
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
        extension = self.get_link_extension()
        if extension is None:
            return False
        if len(extension) < 1:
            return False
        if extension[-1] in GARBAGE_EXTENSIONS:
            return True
        return False
    
    def get_link_extension(self):
        path = urlparse(self.recreated_link).path.lower()
        last_section = os.path.split(path)[-1]
        _, *ext = last_section.split(".")

        if len(ext) == 0:
            return None
        return ext[-1]
    
    def __str__(self) -> str:
        return self.recreated_link
    

def load_headers(headers_string):
    headers = {}

    for header in headers_string:
        header_name, value = header.split(": ")
        headers[header_name] = value
    return headers

def try_find_more_urls(link_):
    more_urls = set()
    extension_ = link_.get_link_extension()
    if extension_ == "js":
        logger.debug(f"Trying to find js.map file")
        parsed_link = urlparse(str(link_))
        js_map = urlunparse(parsed_link._replace(path=f"{parsed_link.path}.map"))
        more_urls.add(js_map)
    # elif extension_ in ["php", "asp", "aspx"]:
    #     logger.debug(f"trying to find backup files") 
    #     parsed_link = urlparse(str(link_))
    #     path_no_extension = os.path.join(os.path.split(parsed_link.path)[:-1],os.path.split(parsed_link.path)[-1].split(".")[0])
        
    #     for new_file in [
    #             f"{path_no_extension}.bak", 
    #             f"{path_no_extension}.old", 
    #             f"{path_no_extension}.old.bak", 
    #             f"{path_no_extension}.zip",
    #             f"{path_no_extension}.{extension_}~", 
    #             f"{path_no_extension}.{extension_}.bak",
    #             f"{path_no_extension}.{extension_}.old",
    #             f"{path_no_extension}.{extension_}.old.bak",
    #             f"{path_no_extension}.{extension_}.zip", 
    #             f"{path_no_extension}.{extension_}.tar.gz",
    #             f"{path_no_extension}.{extension_}.tar.bz2",
    #             f"{path_no_extension}.{extension_}.1",
    #             f"{path_no_extension}.{extension_} (1)",
    #             f"{path_no_extension}.{extension_}.save.swp"

    #             ]:
    #         more_urls.add(urlunparse(parsed_link._replace(path=new_file)))
        
    return more_urls

async def main_headless(args):
    veb = Web_headless(load_headers(args.header), timeout=args.timeout)
    regex = findAllLinksv2 if args.regex_quotes else findAllLinksv2
    crawler = Crawl(web=veb, url=args.url, regex=regex, restricted_exts=args.restrict_exts)

    init_url_parsed = urlparse(args.url)
    await veb.start_browser()

    def signal_handler(sig, frame):
        logger.warning(f"Caught ctrl+c, saving results...")
        crawler.write_results()
        if not args.quiet:
            print("================= links ===================")
            print("\n".join(sorted(retrieved_links)))
            print("================= results ===================")
        print(crawler.return_results_formatted())
        
        exit(1)
        
    signal.signal(signal.SIGINT, signal_handler)

    id_ = await veb.new_page()
    links = await crawler.visit_n_parse_headless(id_, crawler.init_url)
    
    def get_next_urls(links):
        urls = set()
        for link in links:
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

            more_urls = set()
            if args.find_more:
                more_urls = try_find_more_urls(link_)

            # print(f"{link} - {type_of_link} - {full_url}")

            if args.mode == "sub" and ".".join(urlparse(full_url).netloc.split(".")[-2:]) == ".".join(init_url_parsed.netloc.split(".")[-2:]):
                urls.add(full_url)
                urls |= more_urls
            if args.mode == "strict" and urlparse(full_url).netloc == init_url_parsed.netloc:
                urls.add(full_url)
                urls |= more_urls
            if args.mode == "lax":
                urls.add(full_url)
                urls |= more_urls
        return urls
    next_urls = get_next_urls(links)
    crawler.add_queue(next_urls)
    logger.debug("Init page crawled, crawling subpages now")
    while len(crawler.queue) > 0 and len(crawler.fails) < args.max_fails and len(crawler.visited | crawler.fails) < args.max_visits:
        url = crawler.queue.pop()
        logger.debug(f"Next page to crawl: {url}")

        links = await crawler.visit_n_parse_headless(id_, url)
        crawler.add_queue(get_next_urls(links))
        if not args.quiet:
            crawler.print_status()
    
    await veb.close_browser()

    crawler.write_results()
    if not args.quiet:
        print("================= links ===================")
        print("\n".join(sorted(retrieved_links)))
        print("================= results ===================")
    print(crawler.return_results_formatted())

def main_classic(args):
    veb = Web_classic(forced_headers=load_headers(args.header), timeout=args.timeout)
    regex = findAllLinksv2 if args.regex_quotes else findAllLinksv2
    crawler = Crawl(web=veb, url=args.url, regex=regex, restricted_exts=args.restrict_exts)

    init_url_parsed = urlparse(args.url)

    def signal_handler(sig, frame):
        logger.warning(f"Caught ctrl+c, saving results...")
        crawler.write_results()
        if not args.quiet:
            print("================= links ===================")
            print("\n".join(sorted(retrieved_links)))
            print("================= results ===================")
        print(crawler.return_results_formatted())
        
        exit(1)
        
    signal.signal(signal.SIGINT, signal_handler)

    id_ = 0
    links = crawler.visit_n_parse_classic(id_, crawler.init_url)
    
    def get_next_urls(links):
        urls = set()
        for link in links:
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
            
            more_urls = set()
            if args.find_more:
                more_urls = try_find_more_urls(link_)

            # print(f"{link} - {type_of_link} - {full_url}")
            

            if args.mode == "sub" and ".".join(urlparse(full_url).netloc.split(".")[-2:]) == ".".join(init_url_parsed.netloc.split(".")[-2:]):
                urls.add(full_url)
                urls |= more_urls
            if args.mode == "strict" and urlparse(full_url).netloc == init_url_parsed.netloc:
                urls.add(full_url)
                urls |= more_urls
            if args.mode == "lax":
                urls.add(full_url)
                urls |= more_urls
        return urls

    next_urls = get_next_urls(links)
    crawler.add_queue(next_urls)
    logger.debug("Init page crawled, crawling subpages now")
    while len(crawler.queue) > 0 and len(crawler.fails) < args.max_fails and len(crawler.visited | crawler.fails) < args.max_visits:
        url = crawler.queue.pop()
        logger.debug(f"Next page to crawl: {url}")

        links = crawler.visit_n_parse_classic(id_, url)
        crawler.add_queue(get_next_urls(links))
        if not args.quiet:
            crawler.print_status()
    
    crawler.write_results()
    if not args.quiet:
        print("================= links ===================")
        print("\n".join(sorted(retrieved_links)))
        print("================= results ===================")
    print(crawler.return_results_formatted())


def get_arguments():
    parser = argparse.ArgumentParser(description="Crawl all links from a webpage")
    parser.add_argument("url", type=str, help="URL to crawl")
    parser.add_argument("-q", "--quiet", action="store_true", help="Shut the f up and output only the urls", default=False)
    parser.add_argument("-mf", "--max-fails", type=int, help="max fails before stopping", default=10)
    parser.add_argument("-mv", "--max-visits", type=int, help="max visits before stopping", default=100)
    parser.add_argument("-m", "--mode", type=str, help="Crawling mode", default="sub", choices=["sub", "lax", "strict"])
    parser.add_argument("-H", "--header", type=str, help="Headers to send", action='append', default=[])
    parser.add_argument("--timeout", type=int, help="Timeout for fetching web page", default=35)
    parser.add_argument("-ch", "--chrome-headless", help="Use a headless browser to run the crawler", action="store_true", default=False)
    parser.add_argument("-fm", "--find-more", help="Try some techniques to get more interesting results", action="store_true", default=False)
    parser.add_argument("-r", "--restrict-exts", action="append", help="Restrict extensions to these", default=None)
    parser.add_argument("--regex-quotes", default=False, action="store_true", help="Use a specific regex that matches urls and paths only with \" or ' arround")


    return parser.parse_args()


if __name__ == "__main__":
    if not os.path.exists("/tmp/crawlalllinks"):
        os.mkdir("/tmp/crawlalllinks")
    args = get_arguments()
    if args.quiet:
        logger.remove(0)
    logger.info("Starting crawler")
    if args.chrome_headless:
        asyncio.get_event_loop().run_until_complete(main_headless(args))
    else:
        main_classic(args)
