import re
import logging

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)


MIN_SQFT_PATTERN = r'.*min-sqft=([0-9a-zA-Z]+)-sqft.*'
MAX_SQFT_PATTERN = r'.*max-sqft=([0-9a-zA-Z]+)-sqft.*'
MIN_LOT_SIZE = 10
MAX_LOT_SIZE = 12000

MIN_PRICE_PATTERN = r'.*min-price=([0-9a-zA-Z]+).*'
MAX_PRICE_PATTERN = r'.*max-price=([0-9a-zA-Z]+).*'
MIN_PRICE = 1000
MAX_PRICE = 2000000

MIN_YEAR_PATTERN = r'.*min-year-built=([0-9a-zA-Z]+).*'
MAX_YEAR_PATTERN = r'.*max-year-built=([0-9a-zA-Z]+).*'
MIN_YEAR = 1900
MAX_YEAR = 2018

# /filter/min-price=750k,max-price=780k,min-lot-size=3k-sqft,max-lot-size=4k-sqft,include=sold-3yr
# min-year-built=2016
# min-sqft=500-sqft
REDFIN_BASE_URL = 'https://www.redfin.com/city/17420/CA/San-Jose/'
BASE_FILTERS = ['include=sold-3yr']


def parse_filter_params(filter_str):
    min_sqft_m = re.match(MIN_SQFT_PATTERN, filter_str)
    max_sqft_m = re.match(MAX_SQFT_PATTERN, filter_str)
    min_price_m = re.match(MIN_PRICE_PATTERN, filter_str)
    max_price_m = re.match(MAX_PRICE_PATTERN, filter_str)
    min_year_m = re.match(MIN_YEAR_PATTERN, filter_str)
    max_year_m = re.match(MAX_YEAR_PATTERN, filter_str)

    min_sqft, max_sqft, min_price, max_price, min_year, max_year = None, None, None, None, None, None
    if min_sqft_m:
        min_sqft = int(min_sqft_m.group(1))
    if max_sqft_m:
        max_sqft = int(max_sqft_m.group(1))
    if min_price_m:
        min_price = int(min_price_m.group(1))
    if max_price_m:
        max_price = int(max_price_m.group(1))
    if min_year_m:
        min_year = int(min_year_m.group(1))
    if max_year_m:
        max_year = int(max_year_m.group(1))
    return {
        'min_sqft': min_sqft,
        'max_sqft': max_sqft,
        'min_price': min_price,
        'max_price': max_price,
        'min_year': min_year,
        'max_year': max_year,
    }


def construct_filter_url(**kwargs):
    filters = BASE_FILTERS
    if 'min_sqft' in kwargs:
        filters.append('min-sqft={}-sqft'.format(kwargs['min_sqft']))
    if 'max_sqft' in kwargs:
        filters.append('max-sqft={}-sqft'.format(kwargs['max_sqft']))
    if 'min_price' in kwargs:
        filters.append('min-price={}'.format(kwargs['min_price']))
    if 'max_price' in kwargs:
        filters.append('max-price={}'.format(kwargs['max_price']))
    if 'min_year' in kwargs:
        filters.append('min-year-built={}'.format(kwargs['min_year']))
    if 'max_year' in kwargs:
        filters.append('max-year-built={}'.format(kwargs['max_year']))
    return '{}/filter/{}'.format(REDFIN_BASE_URL, ','.join(filters))


def add_sqft_filters(min_sqft, max_sqft):
    sqft_range = max_sqft - min_sqft
    if sqft_range == 0:
        return [(min_sqft, max_sqft)]
    sqft_filters = []
    # 1000 is the break point. Above 1000, the min ticker becomes 10.
    if min_sqft < 1000 and max_sqft > 1000:
        sqft_filters.extend([(min_sqft, 1000), (1000, max_sqft)])
    else:
        min_ticker = 10 if min_sqft >= 1000 else 1
        sqft_ticker = sqft_range // 5
        if sqft_ticker >= min_ticker:
            sqft_ticker = sqft_ticker // min_ticker * min_ticker
        else:
            sqft_ticker = min_ticker

        tickers = list(range(min_sqft, max_sqft + 1, sqft_ticker))
        if max_sqft - tickers[-1] >= sqft_ticker:
            tickers.append(max_sqft)
        else:
            tickers[-1] = max_sqft
        sqft_filters = list(zip(tickers[:-1], tickers[1:]))
    return sqft_filters


def add_price_filters(min_price, max_price):
    if min_price == max_price:
        return [(min_price, max_price)]
    price_filters = []
    if min_price < 1000000 and max_price > 1000000:
        price_filters.extend([(min_price, 1000000), (1000000, max_price)])
    else:
        price_diff = max_price - min_price
        min_ticker = 10000 if min_price >= 1000000 else 1000
        price_ticker = price_diff // 5
        price_ticker = max(min_ticker, price_ticker // min_ticker * min_ticker)
        tickers = list(range(min_price, max_price, price_ticker))
        if max_price - tickers[-1] >= price_ticker:
            tickers.append(max_price)
        else:
            tickers[-1] = max_price
        price_filters = list(zip(tickers[:-1], tickers[1:]))
    return price_filters


def add_year_filters(min_year, max_year):
    if min_year == max_year:
        return [(min_year, max_year)]

    year_diff = max_year - min_year
    year_ticker = max(1, year_diff // 5)

    tickers = list(range(min_year, max_year, year_ticker))
    if max_year - tickers[-1] >= year_ticker:
        tickers.append(max_year)
    else:
        tickers[-1] = max_year
    year_filters = list(zip(tickers[:-1], tickers[1:]))
    return year_filters


def apply_filters(base_url):
    """Apply more filters to make it more fine-grained.
    Return a list of urls containing filters, which adds up
    to the original url.
    Filter priority: price, sqft-size, year-built
    """
    filters = ''
    if '/filter/' not in base_url:
        price_filters = [(1000, 1000000), (1000000, 2000000)]
        return [construct_filter_url(None, None, x[0], x[1]) for x in price_filters]

    base_url, filters = base_url.split('/filter/')
    min_lot, max_lot, min_price, max_price = parse_filter_params(filters)

    if min_lot or max_lot:
        assert (min_price and max_price) and (
            min_lot and max_lot), 'filters invalid {}'.format(filters)
        # Granualarity becomes 10 once the min lot is above 1000 sqft.
        lot_range = max_lot - min_lot
        lot_filters = []
        if min_lot < 1000 and max_lot > 1000:
            lot_filters.extend([(min_lot, 1000), (1000, max_lot)])
        else:
            min_ticker = 10 if min_lot >= 1000 else 1
            lot_ticker = lot_range // 5
            if lot_ticker >= min_ticker:
                lot_ticker = lot_ticker // min_ticker * min_ticker
            else:
                lot_ticker = min_ticker

            tickers = list(range(min_lot, max_lot + 1, lot_ticker))
            if max_price - tickers[-1] >= lot_ticker:
                tickers.append(max_price)
            else:
                tickers[-1] = max_price
            lot_filters = list(zip(tickers[:-1], tickers[1:]))

        if len(lot_filters) == 1:
            LOGGER.info('cannot further split the data.')
            return []

        return [construct_filter_url(x[0], x[1], min_price, max_price) for x in lot_filters]

    if min_price or max_price:
        assert min_price and max_price, 'filters invalid {}'.format(filters)
        price_filters = []
        if min_price < 1000000 and max_price > 1000000:
            price_filters.append((min_price, 1000000), (1000000, max_price))
        else:
            price_diff = max_price - min_price
            min_ticker = 10000 if min_price >= 1000000 else 1000
            price_ticker = price_diff // 5
            if price_ticker >= min_ticker:
                price_ticker = price_ticker // min_ticker * min_ticker
            else:
                price_ticker = min_ticker

            tickers = list(range(min_price, max_price, price_ticker))
            if max_price - tickers[-1] >= price_ticker:
                tickers.append(max_price)
            else:
                tickers[-1] = max_price
            price_filters = list(zip(tickers[:-1], tickers[1:]))
            if len(price_filters) == 1:
                return apply_filters(
                    construct_filter_url(MIN_LOT_SIZE, MAX_LOT_SIZE, min_price, max_price))
        return [construct_filter_url(None, None, x[0], x[1]) for x in price_filters]
