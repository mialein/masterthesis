if __name__ == '__main__':
    import pymongo
    from scrapy.conf import settings
    import numpy as np
    import datetime as dt
    import sys
    import re
    from collections import Counter

    with pymongo.MongoClient(settings['MONGODB_SERVER'], settings['MONGODB_PORT']) as client:
        db = client[settings['MONGODB_DB']]
        table = db[settings['MONGODB_COLLECTION']]

        drug = sys.argv[1]
        query = {'drug_type': drug}
        docs = table.find(query)

    currency = sys.argv[2] if len(sys.argv) > 2 else '€' 

    docs = [d for d in docs]
    for doc in docs:
        doc['price_unit'] = doc['price_unit'].strip()
        doc['ships_from'] = ' '.join(s.replace('Ships from:', '').strip() for s in doc['ships_from'].split('\n')).strip()
        doc['ships_to'] = ' '.join(s.replace('Only ships to certain countries', '').strip() for s in doc['ships_to'].split('\n')).strip()

    print('{} docs'.format(len(docs)))

    print(Counter(d['price_unit'] for d in docs))
    print(Counter(re.sub(r'[^\$\€]', '', d['price']) for d in docs))
    print(Counter(d['ships_from'] for d in docs))
    print(Counter(d['ships_to'] for d in docs))

    eur_grams = {(doc['title'], doc['date']): doc for doc in docs if currency in doc['price'] and doc['price_unit'] == '/Gram'}.values()
    print('{} docs with {}/Gram'.format(len(eur_grams), currency))

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

    eur_grams = [{
        'title': d['title'],
        'date': dt.datetime.strptime(d['date'],'%d.%m.%Y').date(),
        'price': to_float(d['price'].strip(currency))}
        for d in eur_grams]

    find_multi = re.compile(r'(\d+)\s*(gr|g)', re.I) #case insensitive

    for eg in eur_grams:
        match = find_multi.search(eg['title'])
        if match:
            div = int(match.group(1))
            if div != 0:
                eg['price'] /= div


    dates = sorted({d['date'] for d in eur_grams})

    prices_per_date = {date: [p['price'] for p in eur_grams if p['date'] == date] for date in dates} # group by dates

    labels = ['offer count', 'median price']

    data_per_date = {date: {labels[0]: len(prices), labels[1]: np.median(prices)}
                     for date, prices in prices_per_date.items()}

    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates

    y = {label: [data[label] for date, data in sorted(data_per_date.items())] for label in labels}

    for label in labels:
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%d.%m.%Y'))
        plt.plot(dates, y[label])

        plt.legend([label], loc='upper right')
        plt.xticks(dates[::1], rotation=90)
        plt.show()
