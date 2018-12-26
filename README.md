# redfin-scraper
redfin-scraper is a proxy-based scraper to extract properties from Redfin with filters. 
It is especially useful when you want to crawl **all recently sold** properties 
(e.g., properties sold in past 3 years) in a given state or city.

## Scraping Algorithm
Please refer to *algorithm_sketch.md*.

## Prerequisites

1. Have sqlite installed. If you are using mac, you 
[do not need to install](https://tableplus.io/blog/2018/08/download-install-sqlite-for-mac-osx-in-5-minutes.html).
2. Your OS system has python 3.6
3. You have a file of proxies. You can buy proxies online, or use a free service like 
[proxybroker](http://proxybroker.readthedocs.io/en/latest/). 
The repo assumes the use of proxies with user and password authorization.
If your proxies do not need authorization, you can just have the csv file like
```
ip,port
a.b.c.d,2345
e.f.g.h,1234
...
```
Otherwise, your csv proxy file can be
```
ip,port,user,password
a.b.c.d,2345,user1,pass1
e.f.g.h,1234,user2,pass2
...
```

## Environment Setup

1. Create Python virtual environment first with python3.
```shell
python3.6 -m venv /path/to/venv
```
2. Activate venv.
```shell
source /path/to/venv/bin/activate
```
3. ``pip install -r requirements.txt``

## How to use
Once you successfully have all the prerequisites ready and set up the Python environment, you can scrape
the Redfin data based on your needs. In the following I will demonstrate redfin-scraper usage by scraping
a small city called Belmont (https://www.redfin.com/city/1362/CA/Belmont).

### Property Summary URLs Only
If you want to get all Redfin summary URLs in a given city, you can just run

```shell
python redfin_crawler.py proxy.csv https://www.redfin.com/city/1362/CA/Belmont
--property_prefix https://www.redfin.com/city/1362/CA/Belmont --type pages
```

### Scraping Property Details
If you need to get the property details, you can just run with type *properties*. This
will not only generate the summary URLs containing the properties, but extract the property metadata
from those urls.

```shell
python redfin_crawler.py good_proxies.csv https://www.redfin.com/city/1362/CA/Belmont
--property_prefix https://www.redfin.com/city/1362/CA/Belmont --type properties
```

## Known Issues and Bugs

### Safe folk issue on Mac
If Mac user experiences errors like

```
may have been in progress in another thread when fork() was called.
We cannot safely call it or ignore it in the fork() child process. Crashing instead
```
Try setting the following env before running the program
```shell
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES
```

### Scraping with proxies returns 403 error code.
Most likely this proxy is blocked by the detection algorithm of the corresponding websites. You can temporarily remove
the proxy out of your proxy pool.

### But how do I know whether a proxy is good or not?
I put a *proxy_checker.py* in the tools repo. 
You can use this script to eliminate the proxies that are currently blocked by external website. To use, run 

```shell
python tools/proxy_checker.py --proxy_csv_path proxy.csv
```

## Disclaimer
Scraping websites can violate website term of service. Use at your own risk.

## TODO
1. Add free proxy integration so no external proxy file is needed.
2. Make it a package so users can easily install it with pip.
3. Add Docker environment.