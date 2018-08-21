# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class DrugOfferItem(scrapy.Item):
    title = scrapy.Field()
    vendor = scrapy.Field()
    price = scrapy.Field()
    price_unit = scrapy.Field()
    ships_from = scrapy.Field()
    ships_to = scrapy.Field()
    date = scrapy.Field()
    time = scrapy.Field()
    # drug_type = scrapy.Field()