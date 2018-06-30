# redfin-scraper
redfin-scraper is a proxy-based scraper to extract properties from Redfin with filters. It is especially useful when you want to crawl **all** properties in a given state or city.

## High-level Idea
As a common practice, we rely on proxies for crawling the data in parallel.
You can either buy proxies online or use a free proxy service like [proxybroker](http://proxybroker.readthedocs.io/en/latest/).

Another key element for effective scraping is the use of filtering predicates.
Redfin has tens of thousands properties in hot regions like "San Jose, CA", but its pagination system can only return 400 properties at most. Fortunately, it also has filtering criteria like lot size, price and number of beds/baths. You can filter based on the min/max value of the above criteria. Here is an example url:

https://www.redfin.com/city/17420/CA/San-Jose/filter/min-price=750k,max-price=780k,min-lot-size=3k-sqft,max-lot-size=4k-sqft,include=sold-3yr

It basically says we want to find all properties in San Jose, CA, having price between [750k, 780k], and sqrt lot size between [3k, 4k], and sold within the last three years. The filtering predicates provide a simple way to partition the property space. We can build our scraping algorithm based on this.

To summarize, we will construct a set of filtering urls to cover all the properties, and then scrape each url for the property details using multiple proxies.

## Algorithm Sketch
The algorithm has two phases. With a given region (state, city ..),

1. Partitioning the city region into multiple smaller regions. For example,
the total properties in "san jose, ca" can be partitioned into two smaller parts: those with lot size *less than 3k* and those *no less than 3k*. We can further partition the properties with the region with <= 3k into [(lot size <= 3k and price <= 1M), (lot size <= 3k and price > 1M)].
2. Translating each partition into a filtering URL, and ensure that all listings can be reached with Redfin's pagination system. As we mentioned above, Redfin's pagination can reach at most 350 properties. If there are more than 350 properties under a filtering URL, we need to further partition it until it contains no more than 350 properties.
3. Extract all the properties in the filtering URL. We also need to scrape all pages to get properties for each sub-region. Note that, each filtering url can have multiple paginated results. You may also want to append the page ids to the filtering url. As an example, if the url (https://www.redfin.com/city/17420/CA/San-Jose//filter/min-price=830000,max-price=850000,include=sold-3yr) has 30 results, and each url contains 20 results, then the next page you want to visit is https://www.redfin.com/city/17420/CA/San-Jose//filter/min-price=830000,max-price=850000,include=sold-3yr/page-2 .

## How to Use
1. Code is tested against python 3.6
2. You need sqlite installed.
3. You need to provide a file of proxies. You can buy proxies online, or use a free service like [proxybroker](http://proxybroker.readthedocs.io/en/latest/). The repo assumes the use of proxies with user and password authorization.
4. Run ``pip install -r requirements``

## TODO
1. Add free proxy integration so no external proxy file is needed.
2. Make it a package so users can easily install it with pip. 
3. Code cleanups.
