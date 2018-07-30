import re
import json
import random
import requests
import logging
import time
import pandas as pd
import argparse
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup
import sqlite3

from redfin_filters import apply_filters, construct_filter_url, REDFIN_BASE_URL


logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

USER_AGENT = {
    'User-agent': 'Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.112 Safari/537.36'
}

SQLITE_DB_PATH = 'redfin_scraper_data.db'


def construct_proxy(ip_addr, port, user, password):
    return {
        'http': 'http://{}:{}@{}:{}'.format(user, password, ip_addr, port),
        'https': 'https://{}:{}@{}:{}'.format(user, password, ip_addr, port),
    }


def create_tables_if_not_exist():
    conn = sqlite3.connect(SQLITE_DB_PATH)
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
    conn.execute('''CREATE TABLE IF NOT EXISTS LISTING_DETAILS
             (
             URL            TEXT    NOT NULL,
             NUMBER_OF_ROOMS INT,
             NAME           TEXT,
             COUNTRY        TEXT,
             REGION         TEXT,
             LOCALITY       TEXT,
             STREET         TEXT,
             POSTOAL        TEXT,
             TYPE           TEXT,
             PRICE          REAL
             );''')
    conn.close()


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
    """Partition the listings for a given url into multiple sub-urls, such that
    each url contains at most 20 properties.
    """
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

        with sqlite3.connect(SQLITE_DB_PATH) as db:
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


def parse_addresses():
    listing_details = {}
    with sqlite3.connect(SQLITE_DB_PATH) as db:
        cur = db.cursor()
        cur.execute("SELECT * FROM listings")
        rows = cur.fetchall()
        urls = set()

        for url, json_details in rows:
            if url in urls:
                continue
            urls.add(url)
            listings_on_page = (json.loads(json_details))
            for listing in listings_on_page:
                # print('listing {}'.format(listing))
                num_rooms, name, country, region, locality, street, postal, house_type, price = None, None, None, None, None, None, None, None, None
                listing_url = None
                if (not isinstance(listing, list)) and (not isinstance(listing, dict)):
                    continue

                if isinstance(listing, dict):
                    info = listing
                    if ('url' in info) and ('address' in info):
                        listing_url = info.get('url')
                        address_details = info['address']
                        num_rooms = info.get('numberOfRooms')
                        name = info.get('name')
                        country = address_details.get('addressCountry')
                        region = address_details.get('addressRegion')
                        locality = address_details.get('addressLocality')
                        street = address_details.get('streetAddress')
                        postal = address_details.get('postalCode')
                        house_type = info.get('@type')
                        listing_details[listing_url] = (listing_url, num_rooms, name, country, region, locality, street, postal, house_type, price)
                    continue

                for info in listing:
                    if ('url' in info) and ('address' in info):
                        listing_url = info.get('url')
                        address_details = info['address']
                        num_rooms = info.get('numberOfRooms')
                        name = info.get('name')
                        country = address_details.get('addressCountry')
                        region = address_details.get('addressRegion')
                        locality = address_details.get('addressLocality')
                        street = address_details.get('streetAddress')
                        postal = address_details.get('postalCode')
                        house_type = info.get('@type')
                    if 'offers' in info:
                        price = info['offers'].get('price')
                if listing_url:
                    listing_details[listing_url] = (listing_url, num_rooms, name, country, region, locality, street, postal, house_type, price)

    # print(listing_details)
    with sqlite3.connect(SQLITE_DB_PATH) as db:
        cursor = db.cursor()
        try:
            cursor.executemany("""
                INSERT INTO LISTING_DETAILS (
                             URL,
                             NUMBER_OF_ROOMS,
                             NAME     ,
                             COUNTRY  ,
                             REGION    ,
                             LOCALITY  ,
                             STREET    ,
                             POSTOAL   ,
                             TYPE      ,
                             PRICE)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, listing_details.values())
        except Exception as e:
            LOGGER.info(e)


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
    with sqlite3.connect(SQLITE_DB_PATH) as db:
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


def crawl_redfin_with_proxies(proxies):
    small_urls = get_paginated_urls()
    rand_move = random.randint(0, len(proxies) - 1)
    scrape_inputs, scraper_results = [], []
    for i, url in enumerate(small_urls):
        proxy = construct_proxy(*proxies[(rand_move + i) % len(proxies)])
        scrape_inputs.append((url, proxy))

    with ThreadPoolExecutor(max_workers=min(50, len(scrape_inputs))) as executor:
        scraper_results = list(executor.map(scrape_page, scrape_inputs))

    with sqlite3.connect(SQLITE_DB_PATH) as db:
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


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Scrape Redfin property data.')
    parser.add_argument('--type', default='pages', choices=['properties', 'pages'],
                        help='pages or properties (default: properties)')

    parser.add_argument('proxy_csv_path', help='proxies csv path')
    args = parser.parse_args()

    create_tables_if_not_exist()
    proxies = pd.read_csv(args.proxy_csv_path, encoding='utf-8').values
    import pdb; pdb.set_trace()
    if args.type == 'pages':
        url_partition(construct_filter_url(REDFIN_BASE_URL), proxies, max_levels=2)
    elif args.type == 'properties':
        crawl_redfin_with_proxies(proxies)
    else:
        raise Exception('Unknown type {}'.format(args.type))
