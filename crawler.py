import hashlib
import os
from pathlib import Path

import nest_asyncio
import scrapy
from atproto import Client
from dotenv import load_dotenv
from scrapy.crawler import CrawlerProcess
from url_normalize import url_normalize

load_dotenv()


class WebSpider(scrapy.Spider):
    name = "scrawling_crawler"

    def __init__(
        self,
        seed_file="seed_file.txt",
        seed_list=[],
        max_pages=999,
        max_depth=3,
        output_dir="crawled_pages",
        allowed_domains=None,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.max_pages = int(max_pages)
        # Our BFS tree depth cutoff, keep <3 for testing
        self.max_depth = int(max_depth)
        self.output_dir = output_dir
        # set for no-repeats
        # "Data structures employed"
        self.visited = set()
        self.page_count = 0
        os.makedirs(output_dir, exist_ok=True)

        self.start_urls = []
        if Path(seed_file).exists():
            with open(seed_file) as f:
                self.start_urls += [line.strip() for line in f if line.strip()]
        self.start_urls += seed_list  # append seed list to websites in seed_file.txt

        # "Does it prune pages outside the target domain?"
        if allowed_domains:
            self.allowed_domains = allowed_domains.split(",")

    def parse(self, response, depth=0):
        if self.page_count >= self.max_pages:
            return
        # "Data structures employed"
        # "how does it handle duplicate pages?"
        url = url_normalize(response.url)
        if url in self.visited:
            return

        self.visited.add(url)
        self.page_count += 1

        # "Data structures employed"
        # "how does it handle duplicate pages?"
        url_hash = hashlib.md5(url.encode()).hexdigest()
        filepath = os.path.join(self.output_dir, f"{url_hash}.html")
        with open(filepath, "wb") as f:
            f.write(response.body)
        print(f"Crawled: {url}, page {self.page_count}")

        if depth < self.max_depth:
            # Search the DOM for any and all link elements
            for href in response.css("a::attr(href)").getall():
                leaf_url = url_normalize(response.urljoin(href))
                # "how does it handle duplicate pages?"
                if leaf_url not in self.visited:
                    yield scrapy.Request(
                        leaf_url, callback=self.parse, cb_kwargs={"depth": depth + 1}
                    )


print("created WebSpider class")

# bluesky api
# grabs the MLB feed
client = Client()
handle = os.getenv("BSKY_HANDLE")
apppw = os.getenv("BSKY_APP_PASSWORD")
print(f"logging in with handle: {handle} password: {apppw} ...")
client.login(handle, apppw)
data = client.app.bsky.feed.get_feed(
    {
        "feed": "at://did:plc:hf7ezrajxadu7v3tzcyij424/app.bsky.feed.generator/aaap7dpu57ve6",
        "limit": 100,  # arbitrary just so
    }
)

feed = data.feed
next_page = data.cursor

# grabs all the links from the posts
# https://docs.bsky.app/docs/advanced-guides/post-richtext <- this documentation sux it took me forever to figure it out
bsky_uris = []

for item in feed:
    post = item.post
    if post.record.facets:
        for facet in post.record.facets:
            for feature in facet.features:
                if feature.py_type == "app.bsky.richtext.facet#link":
                    print(feature.uri)
                    bsky_uris.append(feature.uri)

print("collected bluesky urls")

# prevent runtime error https://stackoverflow.com/questions/46827007/error-runtimeerror-this-event-loop-is-already-running-in-python
nest_asyncio.apply()

# create crawling process and webspider with bsky uris
process = CrawlerProcess({})
ws = WebSpider(seed_list=bsky_uris)

# start crawling
print("starting crawler")
process.crawl(WebSpider, seed_list=bsky_uris)
process.start()
