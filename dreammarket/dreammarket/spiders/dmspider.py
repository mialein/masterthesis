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
        logging.debug("in parse()")

    def login(self, response):
        logging.debug("in login()")
        image = Image.open(BytesIO(response.body))
        top = tkinter.Tk()
        top.title("Solving Captcha")
        top.geometry("400x200")
        img = ImageTk.PhotoImage(image, size="400x200")
        imagelabel = tkinter.Label(top, image=img)
        textentry = tkinter.Entry(top, font = "Helvetica 20 bold")
        textentry.focus_set()

        original_response = response.meta['original response']
        empty_inputs = original_response.selector.xpath("//form/div[@class='formInputs']/div/input[not(@value) or @value='']").extract()
        logging.debug('empty formdata: {}'.format(empty_inputs))

        formdata = {}

        def callback(en):
            formdata['form[captcha]'] = textentry.get()
            top.destroy()

        textentry.bind("<Return>", callback)
        imagelabel.pack(side = "top", fill = "both", expand = "yes")
        textentry.pack(side = "bottom", fill = "both", expand = "yes")
        top.mainloop()

        logging.debug('applying formdata in original response {}'.format(original_response))
        yield FormRequest.from_response(original_response, formdata=formdata)