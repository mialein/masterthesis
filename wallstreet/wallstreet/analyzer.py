if __name__ == '__main__':
    import pymongo
    from scrapy.conf import settings
    import time
    import numpy as np

    with pymongo.MongoClient(settings['MONGODB_SERVER'], settings['MONGODB_PORT']) as client:
        db = client[settings['MONGODB_DB']]
        table = db[settings['MONGODB_COLLECTION']]

        query = {'drug_type': 'weed'}

        docs = table.find(query)

        stripped_docs = [{'title': d['title'], 'date': d['date'], 'price': d['price'], 'price_unit': d['price_unit'].strip()} for d in docs]
        print('{} stripped docs'.format(len(stripped_docs)))

        print({d['price_unit'] for d in stripped_docs}) #{'/Milligram', '/Ounce', '/Gram', '/Piece'}

        eur_grams = [d for d in stripped_docs if '€' in d['price'] and d['price_unit'] == '/Gram']
        print('{} docs with EUR/Gram'.format(len(eur_grams)))

        def to_float(str):
            try:
                if ',' in str:
                    return float(str.replace('.', '').replace(',', '.'))
                else:
                    return float(str)
            except:
                print('failed: ' + str)
                return None

        eur_grams = [{'title': d['title'], 'date': time.strptime(d['date'], '%d.%m.%Y'), 'price': to_float(d['price'].strip('€'))} for d in eur_grams]

        import re
        find_multi = re.compile(r'(\d+)\s*(gr|g)', re.I) #case insensitive

        for eg in eur_grams:
            match = find_multi.search(eg['title'])
            if match:
                eg['price'] /= int(match.group(1))


        dates = sorted({d['date'] for d in eur_grams})

        prices_per_date = {d: np.asarray([p['price'] for p in eur_grams if p['date'] == d]) for d in dates} # group by dates

        data_per_date = {date: {'offer count': len(prices),
                                'max price': np.max(prices),
                                'min price': np.min(prices),
                                'mean price': np.mean(prices),
                                'median price': np.median(prices),
                                'std dev': np.std(prices)
                                }
                         for date, prices in prices_per_date.items()}

        prices_per_date_2sigma = {d: np.asarray([p for p in prices_per_date[d] if p < data_per_date[d]['mean price'] + 2*data_per_date[d]['std dev']]) for d in prices_per_date}

        data_per_date_2sigma = {date: {'offer count': len(prices),
                                'max price': np.max(prices),
                                'min price': np.min(prices),
                                'mean price': np.mean(prices),
                                'median price': np.median(prices),
                                'std dev': np.std(prices)
                                }
                         for date, prices in prices_per_date_2sigma.items()}

        for date, data in sorted(data_per_date.items()):
            print(time.strftime('%d.%m.%Y', date), data)

        for date, data in sorted(data_per_date_2sigma.items()):
            print(time.strftime('%d.%m.%Y', date), data)

