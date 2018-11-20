import pymongo
import datetime as dt
import re
from collections import Counter
from forex_python.converter import CurrencyRates
from forex_python.bitcoin import BtcConverter
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


def plot(x, Ys, legends, time_format='%d.%m.%Y'):
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter(time_format))

    for y in Ys:
        plt.plot(x, y)

    plt.legend(legends, loc='lower right')
    plt.xticks(x, rotation=90)
    plt.grid(True)
    plt.tight_layout()
    plt.show()

def add_scraping_session(docs, delta_hours=3):
    for doc in docs:
        doc['datetime'] = dt.datetime.strptime(doc['date'] + ' ' + doc['time'], '%d.%m.%Y %H:%M:%S')

    docs = sorted(docs, key=lambda d: d['datetime'])

    last_time = dt.datetime(year=2000, month=1, day=1)
    for doc in docs:
        if doc['datetime'] > last_time + dt.timedelta(hours=delta_hours):
            group_time = doc['datetime']
        doc['scraping_session'] = group_time
        last_time = doc['datetime']

    return docs

def to_float(price):
    try:
        price = price.replace("'", '')
        if ',' in price:
            return float(price.replace('.', '').replace(',', '.'))
        else:
            return float(price)
    except:
        print('failed: ' + price)
        return None

class Analyzer:
    def __init__(self):
        self.docs = []
        self.bad_docs = []
        self.gram_factors = {
                'kilo': 1000, 'kg': 1000,
                'gram': 1, 'g': 1,
                'milligram': 0.001, 'mg': 0.001,
                'oz': 28.3495, 'ounce': 28.3495,
                'pound': 453.592, 'lb': 453.592, 'pd': 453.592, 'p': 453.592,
                'qp': 453.592/4,
                'hp': 453.592/2
                }
        self.units = list(self.gram_factors.keys())
        self.rates = {}

    def load_dreammarket(self):
        with pymongo.MongoClient('localhost', 27017) as client:
            db = client['drug_database']
            table = db['dreammarket-testbase']
            table1 = db['dreammarket']

            docs = list(table.find()) + list(table1.find())

        docs = add_scraping_session(docs)

        docs = {(doc['vendor'], doc['title'], doc['scraping_session'], doc['price']): doc for doc in docs}.values() #remove duplicates
        counts = sorted(Counter(d['scraping_session'] for d in docs).items())

        bad_dates = [date for date, count in counts if count < 40000]
        docs = [d for d in docs if d['scraping_session'] not in bad_dates]

        c = BtcConverter()
        start_date = min(d['scraping_session'] for d in docs)
        end_date = max(d['scraping_session'] for d in docs)
        self.btc_rates = c.get_previous_price_list('EUR', start_date, end_date)
        self.btc_rates = {dt.datetime.strptime(date, '%Y-%m-%d'): rate for date, rate in self.btc_rates.items()}

        find_unit = re.compile(r'(\d+\.?\d*)\s*({})'.format('|'.join(self.units)), re.IGNORECASE)
        find_multi = re.compile(r'(\d+)\s*x', re.IGNORECASE)
        for doc in docs:
            del doc['_id']
            doc['market'] = 'dreammarket'

            doc['ships_from'] = doc['ships_from'].strip()
            doc['ships_to'] = [s.strip() for s in doc['ships_to'].split(',')]

            match = find_unit.search(doc['title'])
            doc['price_unit'] = match.group(2).lower() if match else None

            doc['amount'] = float(match.group(1)) if match and float(match.group(1)) != 0 else 1
            multi = find_multi.search(doc['title'])
            if multi and int(multi.group(1)) != 0:
                doc['amount'] *= int(multi.group(1))

            if doc['price_unit'] not in self.gram_factors:
                self.bad_docs.append(doc)
            else:
                doc['price'] = to_float(doc['price'].strip('฿')) / doc['amount'] / self.gram_factors[doc['price_unit']]
                doc['date_mid'] = dt.datetime.combine(doc['scraping_session'].date(), dt.datetime.min.time()) # transfer dates to midnight

                doc['price'] *= self.btc_rates[doc['date_mid']]
                self.docs.append(doc)

    def load_wallstreet(self):
        with pymongo.MongoClient('localhost', 27017) as client:
            db = client['drug_database']
            table = db['wallstreet']

            docs = list(table.find())

        docs = add_scraping_session(docs)

        docs = {(doc['vendor'], doc['title'], doc['scraping_session'], doc['price']): doc for doc in docs}.values() #remove duplicates
        counts = sorted(Counter(d['scraping_session'] for d in docs).items())

        bad_dates = [date for date, count in counts if count < 3200]
        docs = [d for d in docs if d['scraping_session'] not in bad_dates]

        c = CurrencyRates()
        find_unit = re.compile(r'(\d+\.?\d*)\s*({})'.format('|'.join(self.units)), re.IGNORECASE)
        find_multi = re.compile(r'(\d+)\s*x', re.IGNORECASE)
        for doc in docs:
            del doc['_id']
            doc['market'] = 'wallstreet'

            doc['ships_from'] = ' '.join(s.replace('Ships from:', '').strip() for s in doc['ships_from'].split('\n')).strip()
            stripped = ' '.join(s.replace('Only ships to certain countries', '').strip() for s in doc['ships_to'].split('\n')).strip()
            doc['ships_to'] = [s.replace('Ships Worldwide', 'WW').replace('WW WW', 'WW').strip() for s in stripped.split(',')]

            match = find_unit.search(doc['title'])
            doc['price_unit'] = doc['price_unit'].lower().strip().replace('/', '')
            if doc['price_unit'] == 'piece':
                doc['price_unit'] = match.group(2).lower() if match else None

            multi = find_multi.search(doc['title'])
            doc['amount'] = float(match.group(1)) if match and float(match.group(1)) != 0 else 1
            if multi and int(multi.group(1)) != 0:
                doc['amount'] *= int(multi.group(1))

            is_dollar = '$' in doc['price']
            if doc['price_unit'] not in self.gram_factors:
                self.bad_docs.append(doc)
            else:
                doc['price'] = to_float(doc['price'].strip('$').strip('€')) / doc['amount'] / self.gram_factors[doc['price_unit']]
                doc['date_mid'] = dt.datetime.combine(doc['scraping_session'].date(), dt.datetime.min.time()) # transfer dates to midnight

                if is_dollar:
                    date = doc['date_mid']
                    if not date in self.rates:
                        self.rates[date] = c.get_rate('USD', 'EUR', date)
                    doc['price'] *= self.rates[date]

                self.docs.append(doc)

    def load_tochkamarket(self):
        with pymongo.MongoClient('localhost', 27017) as client:
            db = client['drug_database']
            table = db['tochkamarket']

            docs = list(table.find())

        docs = add_scraping_session(docs)
        docs = {(doc['vendor'], doc['title'], doc['scraping_session'], doc['price']): doc for doc in docs}.values() #remove duplicates
        counts = sorted(Counter(doc['scraping_session'] for doc in docs).items())

        bad_dates = [date for date, count in counts if count < 1200]
        docs = [d for d in docs if d['scraping_session'] not in bad_dates]

        c = CurrencyRates()
        find_unit = re.compile(r'(\d+\.?\d*)?\s*({})'.format('|'.join(self.units)), re.IGNORECASE)
        find_multi = re.compile(r'(\d+)\s*x', re.IGNORECASE)
        for doc in docs:
            del doc['_id']
            doc['market'] = 'tochkamarket'

            doc['ships_from'] = doc['ships_from'].strip()
            doc['ships_to'] = [s.strip() for s in doc['ships_to'].split(',')]

            match = find_unit.search(doc['amount'])
            doc['price_unit'] = match.group(2).lower() if match else None
            doc['amount'] = float(match.group(1)) if match and match.group(1) else 1
            multi = find_multi.search(doc['title'])
            if multi and int(multi.group(1)) != 0:
                doc['amount'] *= int(multi.group(1))

            if doc['price_unit'] not in self.gram_factors:
                self.bad_docs.append(doc)
            else:
                doc['price'] = to_float(doc['price'].strip('USD')) / doc['amount'] / self.gram_factors[doc['price_unit']]
                doc['date_mid'] = dt.datetime.combine(doc['scraping_session'].date(), dt.datetime.min.time()) # transfer dates to midnight

                date = doc['date_mid']
                if not date in self.rates:
                    self.rates[date] = c.get_rate('USD', 'EUR', date)
                doc['price'] *= self.rates[date]

                self.docs.append(doc)

    def get_filters(self):
        return sorted({key for doc in self.docs for key in doc})

    def get_values(self, *values, **filters):
        return sorted({tuple(doc[v] for v in values) for doc in self.filter_docs(**filters)})

    def filter_docs(self, *values, **filters):
        docs = self.docs
        if 'ships_to' in filters:
            values = filters['ships_to']
            del filters['ships_to']
            docs = [doc for doc in docs if any(v in doc['ships_to'] for v in values)]

        filtered = [doc for doc in docs if all(doc[key] == value for (key, value) in filters.items())]
        if not values:
            return filtered
        else:
            return [{v: doc[v] for v in values} for doc in filtered]
