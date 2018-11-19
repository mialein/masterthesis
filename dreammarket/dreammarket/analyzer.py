if __name__ == '__main__':
    import pymongo
    from scrapy.conf import settings
    import numpy as np
    import datetime as dt
    import sys
    import argparse
    import re
    from collections import Counter
    from forex_python.bitcoin import BtcConverter
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates

    def add_scraping_session(docs):
        for doc in docs:
            doc['datetime'] = dt.datetime.strptime(doc['date'] + ' ' + doc['time'], '%d.%m.%Y %H:%M:%S')

        docs = sorted(docs, key=lambda d: d['datetime'])

        last_time = dt.datetime(year=2000, month=1, day=1)
        for doc in docs:
            if doc['datetime'] > last_time + dt.timedelta(hours=1):
                group_time = doc['datetime']
            doc['scraping_session'] = group_time
            last_time = doc['datetime']

        return docs

    def plot(x, y, legend, time_format='%d.%m.%Y %H:%M:%S'):
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter(time_format))
        plt.plot(x, y)

        plt.legend([legend], loc='lower right')
        plt.xticks(x, rotation=90)
        plt.grid(True)
        plt.tight_layout()
        plt.show()

    parser = argparse.ArgumentParser()

    drug_list = ['weed', 'hashish', 'concentrates', 'cocaine', 'meth', 'speed',
            'lsd', 'mdma', 'benzos', 'ecstasy', 'opiates', 'steroids']

    parser.add_argument('--drug', choices=drug_list, default='weed')
    parser.add_argument('--ships_from', help='one of US, DE, NL, etc...')
    parser.add_argument('--ships_to', help='one of WW, US, DE, NL, etc...')

    args = parser.parse_args()

    with pymongo.MongoClient(settings['MONGODB_SERVER'], settings['MONGODB_PORT']) as client:
        db = client[settings['MONGODB_DB']]
        table = db[settings['MONGODB_COLLECTION']]
        table1 = db['dreammarket']

        docs = list(table.find()) + list(table1.find())

    docs = add_scraping_session(docs)
    docs = {(doc['title'], doc['scraping_session'], doc['price']): doc for doc in docs}.values() #remove duplicates
    groups = Counter(doc['scraping_session'] for doc in docs)
    #plot([g for g,i in sorted(groups.items())], [i for g,i in sorted(groups.items())], 'counts')

    counts = [(dt.datetime.strftime(session, '%d.%m.%Y %H:%M:%S'), count) for session, count in groups.items()]
    #print(counts)

    bad_dates = [date for date, count in groups.items() if count < 40000]
    docs = [d for d in docs if d['scraping_session'] not in bad_dates and d['drug_type'] == args.drug]
    print('removed dates: {}'.format(bad_dates))

    find_unit = re.compile(r'(\d+\.?\d*)\s*(kilo|kg|g|mg|oz|ounce|pound|lb)', re.IGNORECASE)
    find_multi = re.compile(r'(\d+)\s*x', re.IGNORECASE)
    for doc in docs:
        match = find_unit.search(doc['title'])
        multi = find_multi.search(doc['title'])
        doc['price_unit'] = match.group(2) if match else None
        doc['amount'] = float(match.group(1)) if match and float(match.group(1)) != 0 else 1
        if multi and int(multi.group(1)) != 0:
            doc['amount'] *= int(multi.group(1))
        doc['ships_from'] = doc['ships_from'].strip()
        doc['ships_to'] = [s.strip() for s in doc['ships_to'].split(',')]
        del doc['_id']

    print('{} docs'.format(len(docs)))
    unrecognized = [doc for doc in docs if doc['price_unit'] is None]
    print('{} docs with unrecognized price units:'.format(len(unrecognized)))
    for doc in unrecognized[:30]:
        print(doc['title'])

    print(Counter(d['price_unit'] for d in docs))
    print(Counter(re.sub(r'[^\$\€\฿\£]', '', d['price']) for d in docs))
    print(Counter(d['ships_from'] for d in docs))
    print(Counter(t for d in docs for t in d['ships_to']))

    filtered_docs = [doc for doc in docs if doc['price_unit'] is not None and
            (args.ships_from is None or args.ships_from == doc['ships_from']) and
            (args.ships_to is None or args.ships_to in doc['ships_to'])]
    print('{} docs with price unit /gram shipping from {} to {}'.format(len(filtered_docs), args.ships_from, args.ships_to))

    def to_float(price):
        try:
            return float(price)
        except:
            print('failed: ' + price)
            return None

    gram_factors = {'kilo': 1000, 'kg': 1000, 'g': 1, 'mg': 0.001, 'oz': 28.3495, 'ounce': 28.3495, 'pound': 453.592, 'lb': 453.592}

    filtered_docs = [{
        'title': d['title'],
        'date': dt.datetime.combine(d['scraping_session'].date(), dt.datetime.min.time()), # transfer dates to midnight
        'price': to_float(d['price'].strip('฿')) / d['amount'] / gram_factors[d['price_unit'].lower()]}
        for d in filtered_docs]

    c = BtcConverter()
    start_date = min(d['date'] for d in filtered_docs)
    end_date = max(d['date'] for d in filtered_docs)

    print('getting exchange rates...')
    rates = c.get_previous_price_list('EUR', start_date, end_date)
    rates = {dt.datetime.strptime(date, '%Y-%m-%d'): rate for date, rate in rates.items()}

    for doc in filtered_docs:
        doc['price'] *= rates[doc['date']]

    print('DONE')

    dates = sorted({d['date'] for d in filtered_docs})

    prices_per_date = {date: [p['price'] for p in filtered_docs if p['date'] == date] for date in dates} # group by dates

    labels = ['Anzahl Angebote', 'Preis €/g (Median)']

    data_per_date = {date: {labels[0]: len(prices), labels[1]: np.median(prices)}
                     for date, prices in prices_per_date.items()}

    for label in labels:
        y = [data[label] for date, data in sorted(data_per_date.items())]

        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%d.%m.%Y'))
        plt.plot(dates, y)

        legend = '{} für {}'.format(label, args.drug)
        if args.ships_from:
            legend += '\nvon ' + args.ships_from
        if args.ships_to:
            legend += '\nnach ' + args.ships_to
        plt.legend([legend], loc='lower right')
        plt.xticks(dates, rotation=90)
        plt.grid(True)
        plt.tight_layout()
        plt.show()
