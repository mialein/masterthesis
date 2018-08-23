from scrapy.spiders import Spider
from scrapy import FormRequest
from scrapy.selector import Selector
import logging
import json
import time

from io import BytesIO, open
import tkinter
from PIL import ImageTk, Image

class MySpider(Spider):
    name = "dmspider"
    start_urls = json.load(open('config'))['start_urls']

    def parse(self, response):
        pass