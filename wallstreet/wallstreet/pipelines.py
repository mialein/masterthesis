# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://doc.scrapy.org/en/latest/topics/item-pipeline.html

import logging
import tkinter
from PIL import ImageTk
from PIL import Image

from scrapy.pipelines.images import ImagesPipeline
from scrapy import Request
from io import BytesIO


class WallstreetPipeline(ImagesPipeline):
    def get_media_requests(self, item, info):
        yield Request(item['image_urls'][0])

    def image_downloaded(self, response, request, info):
        image = Image.open(BytesIO(response.body))
        top = tkinter.Tk()
        top.title("Solving Captcha")
        top.geometry("400x200")
        img = ImageTk.PhotoImage(image, size="400x200")
        imagelabel = tkinter.Label(top, image=img)
        textentry = tkinter.Entry(top, font = "Helvetica 20 bold")
        textentry.focus_set()
        def callback(en):
            self.text = textentry.get()
            top.destroy()
        textentry.bind("<Return>", callback)
        imagelabel.pack(side = "top", fill = "both", expand = "yes")
        textentry.pack(side = "bottom", fill = "both", expand = "yes")
        top.mainloop()
        logging.debug('text = {}'.format(self.text))