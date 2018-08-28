from scrapy.spiders import Spider
from scrapy import FormRequest, Request
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
        logging.debug("in parse() {}".format(response.meta['drugname']))

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

        if len(empty_inputs) != 3:
            with open('strange.html', 'wb') as f:
                f.write(original_response.body)

        username_key = Selector(text=empty_inputs[0]).xpath(".//input/@name").extract_first()
        password_key = Selector(text=empty_inputs[1]).xpath(".//input/@name").extract_first()
        captcha_key = Selector(text=empty_inputs[2]).xpath(".//input/@name").extract_first()

        formdata = {
            username_key: json.load(open('config'))['username'],
            password_key: json.load(open('config'))['password']
        }

        def callback(en):
            formdata[captcha_key] = textentry.get()
            top.destroy()

        textentry.bind("<Return>", callback)
        imagelabel.pack(side = "top", fill = "both", expand = "yes")
        textentry.pack(side = "bottom", fill = "both", expand = "yes")
        top.mainloop()

        logging.debug('applying formdata in original response {}'.format(original_response))
        yield FormRequest.from_response(original_response, formdata=formdata, callback=self.click_all_drugs)

    def click_all_drugs(self, response):
        drug_ids = {
            'weed': '175',
            'hashish': '172',
            'concentrates': '170',
            'cocaine': '187',
            'meth': '188',
            'speed': '190',
            'lsd': '153',
            'mdma': '161',
            'benzos': '120',
            'ecstasy': '163',
            'opiates': '124',
            'steroids': '128'
        }

        base_address = self.start_urls[0] + '?category='

        for drug_name, drug_id in drug_ids.items():
            address = base_address + drug_id
            yield Request(address, meta={'drugname': drug_name})