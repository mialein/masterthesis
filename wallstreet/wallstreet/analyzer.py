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

    stripped_docs = [{'title': d['title'], 'date': d['date'], 'price': d['price'], 'price_unit': d['price_unit'].strip()} for d in docs]
    print('{} stripped docs'.format(len(stripped_docs)))

    print(Counter(d['price_unit'] for d in stripped_docs)) #{'/Milligram', '/Ounce', '/Gram', '/Piece'}

    eur_grams = {(doc['title'], doc['date']): doc for doc in stripped_docs if currency in doc['price'] and doc['price_unit'] == '/Gram'}.values()
    print('{} docs with {}/Gram'.format(len(eur_grams), currency))

    def to_float(str):
        try:
            str = str.replace("'", '')
            if ',' in str:
                return float(str.replace('.', '').replace(',', '.'))
            else:
                return float(str)
        except:
            print('failed: ' + str)
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
            eg['price'] /= int(match.group(1))


    dates = sorted({d['date'] for d in eur_grams})

    prices_per_date = {date: [p['price'] for p in eur_grams if p['date'] == date] for date in dates} # group by dates

    labels = ['offer count', 'median price']

    data_per_date = {date: {labels[0]: len(prices), labels[1]: np.median(prices)}
                     for date, prices in prices_per_date.items()}

    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates

    y = {label: [data[label] for date, data in sorted(data_per_date.items())] for label in labels if label}

    for label in y:
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%d.%m.%Y'))
        plt.plot(dates, y[label])

        plt.legend([label], loc='upper right')
        plt.xticks(dates[::2], rotation=90)
        plt.show()
