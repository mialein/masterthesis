# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://doc.scrapy.org/en/latest/topics/item-pipeline.html

import logging

from scrapy.pipelines.images import ImagesPipeline
from scrapy import Request
from io import BytesIO
try:
    import Image
except ImportError:
    from PIL import Image


class WallstreetPipeline(ImagesPipeline):
    def get_media_requests(self, item, info):
        logging.debug('get media requests: {}'.format(item))
        filename = '{}.jpg'.format(item['image_name'][0])
        yield Request(item['image_urls'][0], meta={'filename': filename})

    def image_downloaded(self, response, request, info):
        logging.debug('response.body: {}'.format(response.body))
        image = Image.open(BytesIO(response.body))
        image.show()
