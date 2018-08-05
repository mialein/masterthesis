from scrapy.spiders import Spider
import logging

class MySpider(Spider):
    name = "wsspider"
    start_urls = ["http://wallstyizjhkrvmj.onion/login"]

    def parse(self, response):
        captchas = response.selector.xpath("//img[@title='captcha']/@src").extract()
        #logging.debug('captchas: {}'.format(captchas))
        if captchas:
            yield {
                'image_urls': captchas[:1],
                'image_name': ['captcha']
            }