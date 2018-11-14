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

    parser = argparse.ArgumentParser()

    drug_list = ['weed', 'hashish', 'concentrates', 'cocaine', 'meth', 'speed',
            'lsd', 'mdma', 'benzos', 'ecstasy', 'opiates', 'steroids']
    unit_list = ['gram', 'piece']

    parser.add_argument('--drug', choices=drug_list, default='weed')
    #parser.add_argument('--price_unit', choices=unit_list, default='gram')
    parser.add_argument('--ships_from', help='one of US, DE, NL, etc...')
    parser.add_argument('--ships_to', help='one of WW, US, DE, NL, etc...')

    args = parser.parse_args()

    with pymongo.MongoClient(settings['MONGODB_SERVER'], settings['MONGODB_PORT']) as client:
        db = client[settings['MONGODB_DB']]
        table = db[settings['MONGODB_COLLECTION']]
        table1 = db['dreammarket']

        docs = list(table.find()) + list(table1.find())

    docs = add_scraping_session(docs)
    groups = Counter(doc['scraping_session'] for doc in docs)

    #x = [date for date, counts in sorted(groups.items())]
    #y = [counts for date, counts in sorted(groups.items())]

    #plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%d.%m.%Y %H:%M:%S'))
    #plt.plot(x, y)

    #legend = 'items per scraping start'
    #plt.legend([legend], loc='lower right')
    #plt.xticks(x, rotation=90)
    #plt.grid(True)
    #plt.tight_layout()
    #plt.show()

    counts = [(dt.datetime.strftime(session, '%d.%m.%Y %H:%M:%S'), count) for session, count in groups.items()]
    print(counts)

    bad_dates = [date for date, count in groups.items() if count < 49000]
    docs = [d for d in docs if d['scraping_session'] not in bad_dates and d['drug_type'] == args.drug]

    find_unit = re.compile(r'(\d+)\s*(gram|gr|g)', re.I) #case insensitive
    for doc in docs:
        match = find_unit.search(doc['title'])
        doc['price_unit'] = match.group(2) if match and int(match.group(1)) != 0 else None
        doc['amount'] = int(match.group(1)) if match else 1
        doc['ships_from'] = doc['ships_from'].strip()
        doc['ships_to'] = [s.strip() for s in doc['ships_to'].split(',')]
        del doc['_id']

    print('{} docs'.format(len(docs)))

    print(Counter(d['price_unit'] for d in docs))
    print(Counter(re.sub(r'[^\$\€\฿\£]', '', d['price']) for d in docs))
    print(Counter(d['ships_from'] for d in docs))
    print(Counter(t for d in docs for t in d['ships_to']))

    filtered_docs = [doc for doc in docs if doc['price_unit'] is not None and
            (args.ships_from is None or args.ships_from == doc['ships_from']) and
            (args.ships_to is None or args.ships_to in doc['ships_to'])]
    print('{} docs with price unit /gram shipping from {} to {}'.format(len(filtered_docs), args.ships_from, args.ships_to))

    #filtered_docs = {(doc['title'], doc['scraping_session']): doc for doc in filtered_docs}.values() #remove duplicates
    #print('{} docs (without duplicates) with price unit /gram shipping from {} to {}'.format(len(filtered_docs), args.ships_from, args.ships_to))

    def to_float(price):
        try:
            return float(price)
        except:
            print('failed: ' + price)
            return None

    filtered_docs = [{
        'title': d['title'],
        'date': d['scraping_session'].date(),
        'price': to_float(d['price'].strip('฿')) / d['amount']}
        for d in filtered_docs]

    #c = BtcConverter()
    #start_date = min(d['date'] for d in filtered_docs)
    #end_date = max(d['date'] for d in filtered_docs)

    #print('getting exchange rates...')
    #rates = c.get_previous_price_list('EUR', start_date, end_date)
    #rates = {dt.datetime.strptime(date, '%Y-%m-%d'): rate for date, rate in rates.items()}

    #for doc in filtered_docs:
        #doc['price'] *= rates[doc['date']]

    #print('DONE')

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
