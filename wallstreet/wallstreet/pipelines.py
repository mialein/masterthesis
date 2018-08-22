# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://doc.scrapy.org/en/latest/topics/item-pipeline.html

import pymongo
from scrapy.conf import settings


class MongoPipeline(object):
    def open_spider(self, spider):
        self.client = pymongo.MongoClient(settings['MONGODB_SERVER'], settings['MONGODB_PORT'])
        self.db = self.client[settings['MONGODB_DB']]

    def close_spider(self, spider):
        self.client.close()

    def process_item(self, item, spider):
        self.db[settings['MONGODB_COLLECTION']].insert_one(dict(item))
        return item