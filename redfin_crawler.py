import json
import random
import requests
import logging
import time
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
import re
from bs4 import BeautifulSoup
import sqlite3


logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

# /filter/min-price=750k,max-price=780k,min-lot-size=3k-sqft,max-lot-size=4k-sqft,include=sold-3yr
REDFIN_BASE_URL = 'https://www.redfin.com/city/17420/CA/San-Jose/'

LOT_SIZE_FILTER = 'lot-size'
MIN_LOT_PATTERN = r'.*min-lot-size=([0-9a-zA-Z]+)-sqft.*'
MAX_LOT_PATTERN = r'.*max-lot-size=([0-9a-zA-Z]+)-sqft.*'
MIN_LOT_SIZE = 10
MAX_LOT_SIZE = 8000

PRICE_FILTER = 'price'
MIN_PRICE_PATTERN = r'.*min-price=([0-9a-zA-Z]+).*'
MAX_PRICE_PATTERN = r'.*max-price=([0-9a-zA-Z]+).*'
MIN_PRICE = 1000
MAX_PRICE = 2000000
USER_AGENT = {
    'User-agent': 'Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.112 Safari/537.36'
}


def construct_proxy(ip_addr, port, user, password):
    return {
        'http': 'http://{}:{}@{}:{}'.format(user, password, ip_addr, port),
        'https': 'https://{}:{}@{}:{}'.format(user, password, ip_addr, port),
    }


def create_tables():
    conn = sqlite3.connect('redfin_scraper.db')
    conn.execute('''CREATE TABLE IF NOT EXISTS URLS
             (
             URL            TEXT    NOT NULL,
             NUM_PROPERTIES INT,
             NUM_PAGES      INT,
             PER_PAGE_PROPERTIES   INT);''')
    conn.execute('''CREATE TABLE IF NOT EXISTS LISTINGS
             (
             URL            TEXT    NOT NULL,
             INFO           TEXT);''')
    conn.close()


def parse_filter_params(filter_str):
    min_lot_m = re.match(MIN_LOT_PATTERN, filter_str)
    max_lot_m = re.match(MAX_LOT_PATTERN, filter_str)
    min_price_m = re.match(MIN_PRICE_PATTERN, filter_str)
    max_price_m = re.match(MAX_PRICE_PATTERN, filter_str)

    min_lot, max_lot, min_price, max_price = None, None, None, None
    if min_lot_m:
        min_lot = int(min_lot_m.group(1))
    if max_lot_m:
        max_lot = int(max_lot_m.group(1))
    if min_price_m:
        min_price = int(min_price_m.group(1))
    if max_price_m:
        max_price = int(max_price_m.group(1))

    return min_lot, max_lot, min_price, max_price


def construct_filter_url(min_lot, max_lot, min_price, max_price):
    filters = []
    if min_lot:
        filters.append('min-lot-size={}-sqft'.format(min_lot))
    if max_lot:
        filters.append('max-lot-size={}-sqft'.format(max_lot))

    if min_price:
        filters.append('min-price={}'.format(min_price))
    if max_price:
        filters.append('max-price={}'.format(max_price))

    filters.append('include=sold-3yr')
    return '{}/filter/{}'.format(REDFIN_BASE_URL, ','.join(filters))


def apply_filters(base_url):
    """Apply more filters to make it more fine-grained.
    Return a list of urls containing filters, which adds up to the original url.
    Filter priority: price, lot-size
    """
    # import pdb; pdb.set_trace()
    filters = ''
    if '/filter/' in base_url:
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
        # import pdb; pdb.set_trace()
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
            # import pdb; pdb.set_trace()
            price_filters = list(zip(tickers[:-1], tickers[1:]))
            if len(price_filters) == 1:
                return apply_filters(
                    construct_filter_url(MIN_LOT_SIZE, MAX_LOT_SIZE, min_price, max_price))
        return [construct_filter_url(None, None, x[0], x[1]) for x in price_filters]
    else:  # Add price filter.
        price_filters = [(1000, 1000000), (1000000, 2000000)]
        return [construct_filter_url(None, None, x[0], x[1]) for x in price_filters]


def get_page_info(url_and_proxy):
    """Return property count, page count and total properties under a given URL."""
    url, proxy = url_and_proxy

    session = requests.Session()
    total_properties, num_pages, properties_per_page = None, None, None
    try:
        resp = session.get(url, headers=USER_AGENT, proxies=proxy)
        if resp.status_code == 200:
            bf = BeautifulSoup(resp.text, 'lxml')
            page_description = bf.find('div', {'class': 'homes summary'}).get_text()
            if 'of' in page_description:
                property_cnt_pattern = r'Showing ([0-9]+) of ([0-9]+) .*'
                m = re.match(property_cnt_pattern, page_description)
                if m:
                    properties_per_page = int(m.group(1))
                    total_properties = int(m.group(2))
                pages = [int(x.get_text()) for x in bf.find_all('a', {'class': "goToPage"})]
                num_pages = max(pages)
            else:
                property_cnt_pattern = r'Showing ([0-9]+) .*'
                m = re.match(property_cnt_pattern, page_description)
                if m:
                    properties_per_page = int(m.group(1))
                num_pages = 1
    except Exception as e:
        LOGGER.exception('Swallowing exception {}'.format(e))

    return (url, total_properties, num_pages, properties_per_page)


def url_partition(base_url, proxies, max_levels=6):
    urls = [base_url]
    num_levels = 0
    partitioned_urls = []
    while urls and (num_levels < max_levels):
        rand_move = random.randint(0, len(proxies) - 1)
        partition_inputs = []
        for i, url in enumerate(urls):
            proxy = construct_proxy(*proxies[(rand_move + i) % len(proxies)])
            partition_inputs.append((url, proxy))

        scraper_results = []
        with ThreadPoolExecutor(max_workers=50) as executor:
            scraper_results = list(executor.map(get_page_info, partition_inputs))

        LOGGER.info('Getting {} results'.format(len(scraper_results)))

        with sqlite3.connect('redfin_scraper.db') as db:
            LOGGER.info('stage {} saving to db!'.format(num_levels))
            values = []
            for result in scraper_results:
                to_nulls = [x if x else 'NULL' for x in result]
                values.append("('{}', {}, {}, {})".format(*to_nulls))
            cursor = db.cursor()
            LOGGER.info('values {}'.format(values))
            cursor.execute("""
                INSERT INTO URLS (URL, NUM_PROPERTIES, NUM_PAGES, PER_PAGE_PROPERTIES)
                VALUES {};
            """.format(','.join(values)))

        LOGGER.info('Writing to sqlite {} results'.format(len(scraper_results)))
        new_urls = []
        for result in scraper_results:
            if result[1] and result[2] and result[3] and result[1] > result[2] * result[3]:
                expanded_urls = apply_filters(result[0])
                new_urls.extend(expanded_urls)
            else:
                partitioned_urls.append(result)
                # LOGGER.info('skipping url {}'.format(result))
        LOGGER.info('stage {}: running for {} urls. We already captured {} urls'.format(
            num_levels, len(new_urls), len(partitioned_urls)))
        urls = new_urls
        num_levels += 1
        time.sleep(random.randint(2, 5))
    return partitioned_urls


def extract_property_fields(property_info_list):
    # addr_details_hash, addr_str, num_rooms, url, price = None, None, None, None, None
    # for info in property_info_list:
    #     if info.get('address'):
    #         addr_details_hash = info.get('address')
    #         addr_str = info.get('name')
    #         num_rooms = info.get('numberOfRooms')
    #         url = info.get('url')
    #     if info.get('offers'):
    #         price = info.get('offers').get('price')
    # return addr_details_hash, addr_str, num_rooms, url, price
    return property_info_list


def scrape_page(url_proxy):
    url, proxy = url_proxy
    session = requests.Session()
    resp = session.get(url, headers=USER_AGENT, proxies=proxy)
    bf = BeautifulSoup(resp.text, 'lxml')
    details = [json.loads(x.text) for x in bf.find_all('script', type='application/ld+json')]
    return url, json.dumps(details)


def get_paginated_urls():
    # Return a set of paginated urls with at most 20 properties each.
    paginated_urls = []
    with sqlite3.connect('redfin_scraper.db') as db:
        cursor = db.execute("""
            SELECT URL, NUM_PROPERTIES, NUM_PAGES, PER_PAGE_PROPERTIES
            FROM URLS
        """)
        seen_urls = set()
        for row in cursor:
            url, num_properties, num_pages, per_page_properties = row
            if url in seen_urls:
                continue
            urls = []
            if not num_pages:
                urls = [url]
            elif num_properties < num_pages * per_page_properties:
                # Build per page urls.
                # print('num pages {}'.format(num_pages))
                urls = ['{},sort=lo-price/page-{}'.format(url, p) for p in range(1, num_pages + 1)]
            paginated_urls.extend(urls)
    return paginated_urls


def crawl_info_with_proxies(proxies):
    small_urls = get_paginated_urls()[:1000]
    rand_move = random.randint(0, len(proxies) - 1)
    scrape_inputs, scraper_results = [], []
    for i, url in enumerate(small_urls):
        proxy = construct_proxy(*proxies[(rand_move + i) % len(proxies)])
        scrape_inputs.append((url, proxy))

    with ThreadPoolExecutor(max_workers=min(50, len(scrape_inputs))) as executor:
        scraper_results = list(executor.map(scrape_page, scrape_inputs))

    with sqlite3.connect('redfin_scraper.db') as db:
        cursor = db.cursor()
        for result in scraper_results:
            value = "('{}', '{}')".format(*result)
            try:
                cursor.execute("""
                    INSERT INTO LISTINGS (URL, INFO)
                    VALUES {};
                """.format(value))
            except Exception as e:
                LOGGER.info('failed record: {}'.format(value))
                LOGGER.info(e)


def get_properties(proxies_csv_path, output_csv_path):
    proxies = pd.read_csv(proxies_csv_path, encoding='utf-8').values
    # LOGGER.info('partitioned urls are {}'.format(
    #     url_partition(REDFIN_BASE_URL + 'filter/include=sold-3yr', proxies)))
    crawl_info_with_proxies(proxies)


if __name__ == '__main__':
    create_tables()
    get_properties('/Users/your_name/Desktop/good_proxies.csv', '/Users/your_name/Desktop/results')
    # all_urls = get_paginated_urls()
    # print(len(all_urls))
    # print(all_urls[:20])
