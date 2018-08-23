# -*- coding: utf-8 -*-

# Scrapy settings for dreammarket project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     https://doc.scrapy.org/en/latest/topics/settings.html
#     https://doc.scrapy.org/en/latest/topics/downloader-middleware.html
#     https://doc.scrapy.org/en/latest/topics/spider-middleware.html

import logging


BOT_NAME = 'dreammarket'

SPIDER_MODULES = ['dreammarket.spiders']
NEWSPIDER_MODULE = 'dreammarket.spiders'


LOG_ENABLED = True
LOG_LEVEL = logging.DEBUG

### More comprehensive list can be found at
### http://techpatterns.com/forums/about304.html
USER_AGENT_LIST = [
    'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/535.7 (KHTML, like Gecko) Chrome/16.0.912.36 Safari/535.7',
    'Mozilla/5.0 (Windows NT 6.2; Win64; x64; rv:16.0) Gecko/16.0 Firefox/16.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_3) AppleWebKit/534.55.3 (KHTML, like Gecko) Version/5.1.3 Safari/534.53.10'
]
HTTP_PROXY = 'http://127.0.0.1:8123'
DOWNLOADER_MIDDLEWARES = {
    'dreammarket.middlewares.RandomUserAgentMiddleware': 400,
    'dreammarket.middlewares.ProxyMiddleware': 410,
    'scrapy.contrib.downloadermiddleware.useragent.UserAgentMiddleware': None,
    'dreammarket.middlewares.CaptchaMiddleware': 420
    # Disable compression middleware, so the actual HTML pages are cached
}


# Obey robots.txt rules
ROBOTSTXT_OBEY = False
DUPEFILTER_CLASS = 'scrapy.dupefilters.BaseDupeFilter'

# Configure maximum concurrent requests performed by Scrapy (default: 16)
CONCURRENT_REQUESTS = 1

ITEM_PIPELINES = {
    'dreammarket.pipelines.MongoPipeline': 300
}

MONGODB_SERVER = "localhost"
MONGODB_PORT = 27017
MONGODB_DB = "drug_database"
MONGODB_COLLECTION = "dreammarket"

# Configure a delay for requests for the same website (default: 0)
# See https://doc.scrapy.org/en/latest/topics/settings.html#download-delay
# See also autothrottle settings and docs
DOWNLOAD_DELAY = 5
