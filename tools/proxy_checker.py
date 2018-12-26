import requests
import time
import argparse
import fake_useragent
import pandas as pd

TOTAL_TRIES_PER_URL = 2
URL = 'https://www.redfin.com/city/1362/CA/Belmont/filter/include=sold-3yr,min-price=500000'


def build_proxies(ip_addr, port, user=None, password=None):
    if user:
        return {
            'http': f'http://{user}:{password}@{ip_addr}:{port}',
            'https': f'https://{user}:{password}@{ip_addr}:{port}',
        }

    return {
        'http': f'http://{ip_addr}:{port}',
        'https': f'https://{ip_addr}:{port}',
    }


def time_proxy(ip_addr, port, proxy_user=None, proxy_pass=None,  url='https://www.google.com', timeout=10):
    success_counts = 0
    start = time.time()
    ua = fake_useragent.UserAgent()

    pull_proxies = build_proxies(ip_addr, port, proxy_user, proxy_pass)
    for i in range(TOTAL_TRIES_PER_URL):
        try:
            r = requests.get(url, proxies=pull_proxies, headers={'User-agent': ua.chrome}, timeout=timeout)
            if r.status_code == 200:
                success_counts += 1
        except Exception as e:
            print(e)

    print('for proxy {}'.format(pull_proxies))
    print('total time {} for visiting {} times'.format(time.time() - start, TOTAL_TRIES_PER_URL))
    print('success rate = {}'.format(success_counts / TOTAL_TRIES_PER_URL))


def time_no_proxy(url='https://www.google.com'):
    success_counts = 0
    start = time.time()
    for i in range(TOTAL_TRIES_PER_URL):
        r = requests.get(url)
        if r.status_code == 200:
            success_counts += 1
    print('for normal request without proxies')
    print('total time {} for visiting {} times'.format(time.time() - start, TOTAL_TRIES_PER_URL))
    print('success rate = {}'.format(success_counts / TOTAL_TRIES_PER_URL))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Scrape Redfin property data.')
    parser.add_argument(
        '--proxy_csv_path',
        help='proxies csv path. '
             'It should contain ip_addr,port,user,password if using proxies with auth. '
             'Or just contain ip_addr,port columns if no auth needed.'
    )
    args = parser.parse_args()

    proxies = pd.read_csv(args.proxy_csv_path, encoding='utf-8').values
    for proxy_info in proxies:
        time_proxy(*proxy_info, url=URL)
