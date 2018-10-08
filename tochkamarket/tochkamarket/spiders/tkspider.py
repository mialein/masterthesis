from scrapy.spiders import Spider
import json
import logging

from io import open

class MySpider(Spider):
    name = "tkspider"
    start_urls = json.load(open('config'))['start_urls']

    def parse(self, response):
        pass

    def login(self, response):
        logging.debug("in login")
        pass

    def click_all_drugs(self, response):
        pass

    def click_all_pages(self, response):
        pass