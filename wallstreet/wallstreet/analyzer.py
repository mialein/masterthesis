if __name__ == '__main__':
    import pymongo
    from scrapy.conf import settings
    import numpy as np
    import datetime as dt
    import sys
    import re
    from collections import Counter

    drug_list = ['weed', 'hashish', 'concentrates', 'cocaine', 'meth', 'speed',
            'lsd', 'mdma', 'benzos', 'ecstasy', 'opiates', 'steroids']

    with pymongo.MongoClient(settings['MONGODB_SERVER'], settings['MONGODB_PORT']) as client:
        db = client[settings['MONGODB_DB']]
        table = db[settings['MONGODB_COLLECTION']]

        drug = sys.argv[1]
        if drug not in drug_list:
            raise Exception('invalid drug: ' + drug)
        query = {'drug_type': drug}
        docs = table.find(query)

    currency = sys.argv[2] if len(sys.argv) > 2 else '€' 
    price_unit = sys.argv[3] if len(sys.argv) > 3 else 'gram'
    ships_from = sys.argv[4] if len(sys.argv) > 4 else None
    ships_to = sys.argv[5] if len(sys.argv) > 5 else None

    docs = [d for d in docs]
    for doc in docs:
        doc['price_unit'] = doc['price_unit'].lower().strip().replace('/', '')
        doc['ships_from'] = ' '.join(s.replace('Ships from:', '').strip() for s in doc['ships_from'].split('\n')).strip()
        stripped = ' '.join(s.replace('Only ships to certain countries', '').strip() for s in doc['ships_to'].split('\n')).strip()
        doc['ships_to'] = ['Worldwide'] if 'Worldwide' in stripped else [s.strip() for s in stripped.split(',')]

    print('{} docs'.format(len(docs)))

    print(Counter(d['price_unit'] for d in docs))
    print(Counter(re.sub(r'[^\$\€]', '', d['price']) for d in docs))
    print(Counter(d['ships_from'] for d in docs))
    print(Counter(t for d in docs for t in d['ships_to']))

    filtered_docs = {(doc['title'], doc['date']): doc for doc in docs # filter duplicate dates, TODO: rather differentiate by timestep, too
            if currency in doc['price'] and doc['price_unit'] == price_unit and
                (ships_from is None or ships_from == doc['ships_from']) and (ships_to is None or ships_to in doc['ships_to'])
            }.values()
    print('{} docs with {}/{} shipping from {} to {}'.format(len(filtered_docs), currency, price_unit, ships_from, ships_to))

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

    filtered_docs = [{
        'title': d['title'],
        'date': dt.datetime.strptime(d['date'],'%d.%m.%Y').date(),
        'price': to_float(d['price'].strip(currency))}
        for d in filtered_docs]

    if price_unit == 'gram':
        find_multi = re.compile(r'(\d+)\s*(gr|g)', re.I) #case insensitive

        for eg in filtered_docs:
            match = find_multi.search(eg['title'])
            if match:
                div = int(match.group(1))
                if div != 0:
                    eg['price'] /= div


    dates = sorted({d['date'] for d in filtered_docs})

    prices_per_date = {date: [p['price'] for p in filtered_docs if p['date'] == date] for date in dates} # group by dates

    labels = ['offer count', 'median price']

    data_per_date = {date: {labels[0]: len(prices), labels[1]: np.median(prices)}
                     for date, prices in prices_per_date.items()}

    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates

    y = {label: [data[label] for date, data in sorted(data_per_date.items())] for label in labels}

    for label in labels:
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%d.%m.%Y'))
        plt.plot(dates, y[label])

        plt.legend([label], loc='lower right')
        plt.xticks(dates[::1], rotation=90)
        plt.show()
