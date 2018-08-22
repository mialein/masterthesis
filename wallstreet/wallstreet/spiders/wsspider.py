from scrapy.spiders import Spider
from scrapy import FormRequest
from scrapy.selector import Selector
from wallstreet.items import DrugOfferItem
import logging
import json
import time

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
            logging.debug('in parse()')

            card_bodys = response.selector.xpath("//div[@class='card-body']").extract()

            for card in card_bodys:
                selector = Selector(text=card)
                title = selector.xpath(".//h4[@class='card-title']/a/text()").extract_first()
                vendor = selector.xpath(".//hr[1]/following-sibling::a/text()").extract_first()
                price = selector.xpath(".//hr[2]/following-sibling::b/text()").extract_first()
                price_unit = selector.xpath(".//hr[2]/following-sibling::b/following-sibling::text()").extract_first()
                ships_from = selector.xpath(".//i[@class='ionicons ion-log-out']/following-sibling::text()").extract_first()
                ships_to = selector.xpath(".//i[@class='ionicons ion-log-in']/following-sibling::text()").extract_first() or ''
                ships_to += selector.xpath(".//i[@class='ionicons ion-log-in']/following-sibling::div/text()").extract_first() or ''
                ships_to += selector.xpath(".//i[@class='ionicons ion-log-in']/following-sibling::div/div/text()").extract_first() or ''
                date = time.strftime("%d.%m.%Y")
                timestamp = time.strftime("%H:%M:%S")

                yield DrugOfferItem(title=title, vendor=vendor, price=price, price_unit=price_unit,
                                    ships_from=ships_from, ships_to=ships_to, date=date, time=timestamp, drug_type=response.meta['drugname'])

            logging.debug("found {} cards".format(len(card_bodys)))


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

    drug_form_data = {
        'weed': {'form[catT]': '1', 'form[catM]': '1', 'form[catB]': '1', 'form[limit]': '90'},
        'hashish': {'form[catT]': '1', 'form[catM]': '1', 'form[catB]': '2', 'form[limit]': '90'},
        'concentrates': {'form[catT]': '1', 'form[catM]': '1', 'form[catB]': '16', 'form[limit]': '90'},
        'cocaine': {'form[catT]': '1', 'form[catM]': '11', 'form[catB]': '3', 'form[limit]': '90'},
        'meth': {'form[catT]': '1', 'form[catM]': '11', 'form[catB]': '4', 'form[limit]': '90'},
        'speed': {'form[catT]': '1', 'form[catM]': '11', 'form[catB]': '5', 'form[limit]': '90'},
        'lsd': {'form[catT]': '1', 'form[catM]': '50', 'form[catB]': '7', 'form[limit]': '90'},
        'mdma': {'form[catT]': '1', 'form[catM]': '4', 'form[catB]': '0', 'form[limit]': '90'},
        'benzos': {'form[catT]': '1', 'form[catM]': '7', 'form[catB]': '0', 'form[limit]': '90'},
        'ecstasy': {'form[catT]': '1', 'form[catM]': '8', 'form[catB]': '0', 'form[limit]': '90'},
        'opiates': {'form[catT]': '1', 'form[catM]': '9', 'form[catB]': '0', 'form[limit]': '90'},
        'steroids': {'form[catT]': '1', 'form[catM]': '10', 'form[catB]': '0', 'form[limit]': '90'}
    }

    def click_drugs(self, response):
        logging.debug('in click_drugs()')

        for drugname, formdata in self.drug_form_data.items():
            yield FormRequest.from_response(response, formxpath='/html/body/div[1]/form[1]', formdata=formdata, callback=self.click_all_pages, meta={'drugname': drugname})

    def click_all_pages(self, response):
        pagenumbers = response.selector.xpath("//div[@class='row specialrow']/div[@class='col-lg-3']/div[@class='card card-body mb-2 pb-2']/ul/li[2]/text()").extract_first()
        pagecount = int(pagenumbers.split("/")[-1])

        for page in range(pagecount):
            formdata = self.drug_form_data[response.meta['drugname']]
            formdata['form[page]'] = str(page+1)
            yield FormRequest.from_response(response, formxpath='/html/body/div[1]/form[1]', formdata=formdata,
                                            callback=self.parse, meta=response.meta)