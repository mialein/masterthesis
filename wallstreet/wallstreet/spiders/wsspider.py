from scrapy.spiders import Spider
from scrapy import FormRequest
import logging
import json

from io import BytesIO, open
import tkinter
from PIL import ImageTk, Image

class MySpider(Spider):
    name = "wsspider"
    start_urls = json.load(open('config'))['start_urls']

    def parse(self, response):
        captchas = response.selector.xpath("//img[@title='captcha']/@src").extract()
        if captchas:
            logging.error("Response has captures, but should not.")
        else:
            with open('drugs.html', mode='wb') as f:
                f.write(response.body)
            logging.debug('wrote response to file')

    def solve_captcha(self, response):
        logging.debug("in solve_captcha()")
        image = Image.open(BytesIO(response.body))
        top = tkinter.Tk()
        top.title("Solving Captcha")
        top.geometry("400x200")
        img = ImageTk.PhotoImage(image, size="400x200")
        imagelabel = tkinter.Label(top, image=img)
        textentry = tkinter.Entry(top, font = "Helvetica 20 bold")
        textentry.focus_set()
        formdata = {}

        def callback(en):
            formdata['form[captcha]'] = textentry.get()
            top.destroy()

        textentry.bind("<Return>", callback)
        imagelabel.pack(side = "top", fill = "both", expand = "yes")
        textentry.pack(side = "bottom", fill = "both", expand = "yes")
        top.mainloop()

        logging.debug('applying formdata in original response {}'.format(response.meta['original response']))
        yield FormRequest.from_response(response.meta['original response'], formdata=formdata)

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
        formdata = {
            'form[username]': json.load(open('config'))['username'],
            'form[password]': json.load(open('config'))['password']}

        def callback(en):
            formdata['form[captcha]'] = textentry.get()
            top.destroy()

        textentry.bind("<Return>", callback)
        imagelabel.pack(side = "top", fill = "both", expand = "yes")
        textentry.pack(side = "bottom", fill = "both", expand = "yes")
        top.mainloop()

        logging.debug('applying formdata in original response {}'.format(response.meta['original response']))
        yield FormRequest.from_response(response.meta['original response'], formdata=formdata, callback=self.click_drugs)

    def click_drugs(self, response):
        logging.debug('in click_drugs()')
        formdata = {'menuCatT': '1'}
        yield FormRequest.from_response(response, formxpath='/html/body/div[1]/form[1]', formdata=formdata, callback=self.parse)
