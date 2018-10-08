from scrapy.spiders import Spider
from scrapy import FormRequest, Request
from scrapy.selector import Selector
from dreammarket.items import DrugOfferItem
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

        card_bodys = response.selector.xpath("//div/div[@class='around']").extract()
        detail_path = ".//div/div[@class='oOfferBody']/table//td[@class='oOfTextDetail']"

        if not card_bodys:
            logging.debug(response.body)

        for card in card_bodys:
            selector = Selector(text=card)
            title = selector.xpath(".//div/div[@class='text oTitle']/a/text()").extract_first().strip()
            price = selector.xpath(detail_path + "/div[@class='bottom oPrice']/text()").extract_first().strip()
            price_unit = ''
            vendor = selector.xpath(detail_path + "/div[@class='oVendor']/a[1]/text()").extract_first().strip()
            ships = selector.xpath(detail_path + "/div[@class='oShips']/span/text()").extract_first()
            ships_from, ships_to = tuple(ships.split('→'))
            ships_from, ships_to = ships_from.strip(), ships_to.strip()
            date = time.strftime("%d.%m.%Y")
            timestamp = time.strftime("%H:%M:%S")

            yield DrugOfferItem(title=title, vendor=vendor, price=price, price_unit=price_unit,
                                ships_from=ships_from, ships_to=ships_to, date=date, time=timestamp,
                                drug_type=response.meta['drugname'])

        logging.debug("found {} cards".format(len(card_bodys)))

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
            yield Request(address, meta={'drugname': drug_name}, callback=self.click_all_pages)

    def click_all_pages(self, response):
        max_page = response.selector.xpath("//div[@class='pageNavContainer']/ul/li/a/text()").extract()[-2]

        for page in range(1, int(max_page)+1):
            address = response.url + '&page=' + str(page)
            yield Request(address, meta=response.meta, callback=self.parse)