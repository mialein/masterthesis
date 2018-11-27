import pymongo
import datetime as dt
import re
from collections import Counter
from forex_python.converter import CurrencyRates
from forex_python.bitcoin import BtcConverter
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd


drug_types = ['benzos', 'cocaine', 'concentrates', 'ecstasy', 'hashish',
        'lsd', 'mdma', 'meth', 'opiates', 'speed', 'steroids', 'weed'] 

drug_names = {'benzos': 'Benzos', 'cocaine': 'Kokain',
        'concentrates': 'Konzentrate', 'ecstasy': 'Ecstasy', 'hashish': 'Hashish',
        'lsd': 'LSD', 'mdma': 'MDMA', 'meth': 'Meth', 'opiates': 'Opiate',
        'speed': 'Speed', 'steroids': 'Steroide', 'weed': 'Marihuana'}

line_colors = {'benzos': 'red', 'cocaine': 'green',
        'concentrates': 'blue', 'ecstasy': 'orange', 'hashish': 'cyan',
        'lsd': 'black', 'mdma': 'red', 'meth': 'green', 'opiates': 'blue',
        'speed': 'orange', 'steroids': 'cyan', 'weed': 'black'}

markers = {'benzos': 'o', 'cocaine': 'v', 'concentrates': '^', 'ecstasy': '<',
        'hashish': '>', 'lsd': 's', 'mdma': 'P', 'meth': 'X', 'opiates': '*',
        'speed': 'D', 'steroids': 'h', 'weed': 'H'}

default_plot_width = {'wallstreet': 1400, 'dreammarket': 950, 'tochkamarket': 800}

def plot(Xs, Ys, xlabel, ylabel, drugs=None, time_format='%d.%m.%Y', location='best', legends=None, show=True, filename=None, market=None):
    width = default_plot_width[market] / 80 if market else 10
    f = plt.figure(figsize=(width, 6))
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter(time_format))

    if drugs:
        for x, y, d in zip(Xs, Ys, drugs):
            plt.plot(x, y, color=line_colors[d], marker=markers[d])
    else:
        for x, y, in zip(Xs, Ys):
            plt.plot(x, y, marker='o')

    if drugs or legends:
        plt.legend(legends if legends else [drug_names[d] for d in drugs], loc=location)
    plt.xticks(sorted({s for x in Xs for s in x}), rotation=90)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.grid(True)
    plt.tight_layout()
    if show:
        plt.show()
    if filename:
        f.savefig(filename+'.pdf', format='pdf')

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
                'microgram': 0.000001, 'ug': 0.000001, 'µg': 0.000001, 'mcg': 0.000001, 'mic': 0.000001,
                'oz': 28.3495, 'ounce': 28.3495,
                'pound': 453.592, 'lb': 453.592, 'pd': 453.592, 'p': 453.592,
                'qp': 453.592/4,
                'hp': 453.592/2
                }
        self.units = sorted(self.gram_factors.keys(), key=lambda u: -len(u))
        self.rates = {}

    def plot_prices(self, show=True, filename=None):
        for market in ['wallstreet', 'dreammarket', 'tochkamarket']:
            Xs, Ys = [], []
            drugs = drug_types if market != 'tochkamarket' else drug_types[:2]+drug_types[3:]
            for drug in drugs:
                pl = pd.DataFrame(self.filter_docs('date_mid', 'price', market=market, drug_type=drug))
                med = pl.groupby('date_mid').median()
                medmean = med.mean()[0]
                diff = (med / medmean - 1) * 100
                Xs.append(diff.index);
                Ys.append(diff.price)
            plt.yticks(range(-20, 21, 5))
            plot(Xs, Ys, 'Datum', 'relative Preisschwankung [%]', drugs=drugs, show=show, filename=market+'_'+filename if filename else None, market=market)

    def plot_available_dates(self, show=True, filename=None):
        labels = ['wallstreet', 'dreammarket', 'tochkamarket']
        dates = [self.get_values('date_mid', market=label) for label in labels]
        Xs = [[d[0] for d in mdates] for mdates in dates]
        Ys = [[i+1]*len(Xs[i]) for i in range(3)]

        width = default_plot_width['wallstreet'] / 80
        f = plt.figure(figsize=(width, 6))
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%d.%m.%Y'))

        for x, y in zip(Xs, Ys):
            plt.plot(x, y, linestyle='', marker='x')

        plt.xticks(sorted({s for x in Xs for s in x}), rotation=90)
        plt.yticks([1,2,3], labels)
        plt.xlabel('Datum')
        plt.ylabel('Markt')
        plt.grid(True)
        plt.tight_layout()
        if show:
            plt.show()
        if filename:
            f.savefig(filename+'.pdf', format='pdf')

    def load_cache(self):
        with pymongo.MongoClient('localhost', 27017) as client:
            db = client['analyzed']
            self.docs = list(db['docs'].find())
            self.bad_docks = list(db['bad_docs'].find())

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

        ships_dict = {
                'Afghanistan': 'AF',
                'Australia': 'AU',
                'Austria': 'AT',
                'Belgium': 'BE',
                'Brazil': 'BR',
                'Canada': 'CA',
                'China': 'CN',
                'Columbia': 'CO',
                'Denmark': 'DK',
                'Finland': 'FI',
                'France': 'FR',
                'Germany': 'DE',
                'Greece': 'GR',
                'India': 'IN',
                'Indonesia': 'ID',
                'Ireland': 'IE',
                'Italy': 'IT',
                'Japan': 'JP',
                'Luxembourg': 'LU',
                'Mexico': 'MX',
                'Netherlands': 'NL',
                'New Zealand': 'NZ',
                'Norway': 'NO',
                'Poland': 'PL',
                'Portugal': 'PT',
                'Russia': 'RU',
                'Saudi Arabia': 'SA',
                'Singapore': 'SG',
                'South Africa': 'ZA',
                'South Korea': 'RK',
                'Spain': 'ES',
                'Sweden': 'SE',
                'Switzerland': 'CH',
                'Thailand': 'TH',
                'United Kingdom': 'GB',
                'United States': 'US',
                'Worldwide': 'WW'
                }

        c = CurrencyRates()
        find_unit = re.compile(r'(\d+\.?\d*)?\s*({})'.format('|'.join(self.units)), re.IGNORECASE)
        find_multi = re.compile(r'(\d+)\s*x', re.IGNORECASE)
        for doc in docs:
            del doc['_id']
            doc['market'] = 'tochkamarket'

            ships_from = doc['ships_from'].strip()
            doc['ships_from'] = ships_dict.get(ships_from, ships_from)
            doc['ships_to'] = [ships_dict.get(s.strip(), s.strip()) for s in doc['ships_to'].split(',')]

            match = find_unit.search(doc['amount'])
            if not match:
                match = find_unit.search(doc['title'])
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

    def load_all(self):
        self.load_wallstreet()
        self.load_dreammarket()
        self.load_tochkamarket()

    def get_filters(self):
        return sorted({key for doc in self.docs for key in doc})

    def get_values(self, *values, **filters):
        return sorted({tuple(doc[v] for v in values) for doc in self.filter_docs(**filters)})

    def filter_docs(self, *values, include_bad_docs=False, **filters):
        docs = self.docs
        if include_bad_docs:
            docs += self.bad_docs

        if 'ships_to' in filters:
            st_values = filters['ships_to']
            del filters['ships_to']
            docs = [doc for doc in docs if any(v in doc['ships_to'] for v in st_values)]

        filtered = [doc for doc in docs if all(doc[key] == value for (key, value) in filters.items())]
        if not values:
            return filtered
        else:
            return [{v: doc[v] for v in values} for doc in filtered]

    def get_good_bad(self, **filters):
        good = [d for d in self.docs if all(d[key] == value for (key, value) in filters.items())]
        bad = [d for d in self.bad_docs if all(d[key] == value for (key, value) in filters.items())]
        return len(good), len(bad)

    def get_price_diffs(self, drugs=['cocaine', 'hashish', 'meth', 'speed', 'steroids', 'weed'], froms=['DE', 'NL', 'CA', 'US', 'AF', 'GB', 'JP', 'SA', 'FR', 'CH', 'MX', 'PH', 'VE', 'IE', 'CN', 'WW']):
        diffs = {}
        for market in ['wallstreet', 'dreammarket', 'tochkamarket']:
            for drug in drugs:
                for sfrom in froms:
                    df = pd.DataFrame(self.filter_docs('date_mid', 'price', market=market, drug_type=drug, ships_from=sfrom))
                    if len(df) == 0:
                        continue
                    median = df.groupby('date_mid').median()
                    counts = df.groupby('date_mid').count()
                    if counts.min()[0] < 10:
                        continue
                    pmax, pmin = None, None
                    pma, pmi = float('-inf'), float('inf') 
                    for period in range(1, 4):
                        mc = median.pct_change(periods=period)
                        if len(mc) <= period:
                            continue

                        mcm = mc.price[period:].idxmax()
                        if mc.price[mcm] > pma:
                            pmax = mcm
                            pma = mc.price[mcm]
                        mcm = mc.price[period:].idxmin()
                        if mc.price[mcm] < pmi:
                            pmin = mcm
                            pmi = mc.price[mcm]

                    if pmax is not None and pmin is not None:
                        price[(market, drug, sfrom)] = (pma, pmax, pmi, pmin)
        
        return diffs
                        
    def get_vendor_count_diffs(self):
        diffs = {}
        for market in ['wallstreet', 'dreammarket', 'tochkamarket']:
            for sfrom in [v[0] for v in self.get_values('ships_from', market=market)]:
                df = pd.DataFrame(self.filter_docs('date_mid', 'vendor', include_bad_docs=True, market=market, ships_from=sfrom))
                if len(df) == 0:
                    continue
                counts = df.drop_duplicates().groupby('date_mid').count()

                cmax, cmin = None, None
                cma, cmi = float('-inf'), float('inf') 
                for period in range(1, 4):
                    cc = counts.diff(periods=period)
                    if len(cc) <= period:
                        continue

                    ccm = cc.vendor[period:].idxmax()
                    if cc.vendor[ccm] > cma:
                        cmax = ccm
                        cma = cc.vendor[ccm]
                    ccm = cc.vendor[period:].idxmin()
                    if cc.vendor[ccm] < cmi:
                        cmin = ccm
                        cmi = cc.vendor[ccm]

                if cmax is not None and cmin is not None:
                    diffs[(market, sfrom)] = (cma, cmax, cmi, cmin)

        return diffs
