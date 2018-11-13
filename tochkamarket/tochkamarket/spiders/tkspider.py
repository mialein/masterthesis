from scrapy.spiders import Spider
from scrapy import FormRequest, Request
import time
import logging
import json
from tochkamarket.items import DrugOfferItem

from io import BytesIO, open
import tkinter
from PIL import ImageTk, Image

class MySpider(Spider):
    name = "tkspider"
    start_urls = json.load(open('config'))['start_urls']

    def parse(self, response):
        logging.debug('in parse()')

        title = response.selector.xpath("//div[@class='twelve wide column']/div/h3/text()").extract_first().strip()
        vendor = response.selector.xpath("//div[@class='user info']/div/div[@class='content card-header']/a/text()").extract_first()
        amount = [a.strip() for a in response.selector.xpath("//table[@class='ui very basic table']//td/text()").extract() if a.strip()][-1]
        price = [a.strip() for a in response.selector.xpath("//table[@class='ui very basic table']//td/a/text()").extract() if a.strip()][-1]
        price_unit = ''
        ships_from = response.selector.xpath("//table[@class='ui celled table fluid inverted green']//th[2]/span/text()").extract_first() or ''
        ships_to = response.selector.xpath("//table[@class='ui celled table fluid inverted green']//th[3]/span/text()").extract_first() or ''
        date = time.strftime("%d.%m.%Y")
        timestamp = time.strftime("%H:%M:%S")

        yield DrugOfferItem(title=title, vendor=vendor, amount=amount, price=price, price_unit=price_unit,
                            ships_from=ships_from, ships_to=ships_to, date=date, time=timestamp,
                            drug_type=response.meta['drugname'])

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

        formdata = {
            'username': json.load(open('config'))['username'],
            'passphrase': json.load(open('config'))['password']
        }

        def callback(en):
            formdata['captcha'] = textentry.get()
            top.destroy()

        textentry.bind("<Return>", callback)
        imagelabel.pack(side = "top", fill = "both", expand = "yes")
        textentry.pack(side = "bottom", fill = "both", expand = "yes")
        top.mainloop()

        logging.debug('applying formdata in original response {}'.format(original_response))
        yield FormRequest.from_response(original_response, formdata=formdata, callback=self.click_all_drugs)

    def click_all_drugs(self, response):
        logging.debug('in click_all_drugs()')

        drug_ids = {
            'weed': ['13'],
            'hashish': ['4'],
            'cocaine': ['11'],
            'meth': ['107'],
            'speed': ['43'],
            'lsd': ['14'],
            'mdma': ['7'],
            'benzos': ['45', '46'],
            'ecstasy': ['9'],
            'opiates': ['15'],
            'steroids': ['10']
        }

        base_address = json.load(open('config'))['base_url'] + '/marketplace?category='

        for drug_name, drug_ids in drug_ids.items():
            for drug_id in drug_ids:
                address = base_address + drug_id
                yield Request(address, meta={'drugname': drug_name}, callback=self.click_all_pages)

    def click_all_pages(self, response):
        logging.debug('in click_all_pages()')

        pages = response.selector.xpath("//div[@class='ui pagination menu']/div/a/text()").extract()
        if not pages:
            self.click_all_cards(response)
        else:
            max_page = int(pages[-1])
            for page in range(1, max_page+1):
                address = response.url + '&page=' + str(page)
                yield Request(address, meta=response.meta, callback=self.click_all_cards)

    def click_all_cards(self, response):
        logging.debug('in click_all_cards()')

        card_hrefs = response.selector.xpath("//div[@class='ui grid']/div[@class='eight wide column']/div/div[@class='image']/a/@href").extract()
        logging.debug('found {} cards'.format(len(card_hrefs)))

        for card in card_hrefs:
            address = json.load(open('config'))['base_url'] + card
            yield Request(address, meta=response.meta, callback=self.parse)