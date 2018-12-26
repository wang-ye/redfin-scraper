This post discusses the underlying scraping algorithms.

## High-level Ideas
As a common practice, we rely on proxies for crawling the data in parallel.
You can either buy proxies online or use a free proxy service like [proxybroker](http://proxybroker.readthedocs.io/en/latest/).

Another key element for effective scraping is the use of filtering predicates.
Redfin has tens of thousands properties in hot regions like "San Jose, CA", but its pagination system returns at most 350 properties. Fortunately, Redfin also provides filtering criteria like lot size, price and number of beds/baths. For example, the following url:

https://www.redfin.com/city/17420/CA/San-Jose/filter/min-price=750k,max-price=780k,min-lot-size=3k-sqft,max-lot-size=4k-sqft,include=sold-3yr

It basically says we want to find all properties in San Jose, CA, having price between [750k, 780k], and sqrt lot size between [3k, 4k], and sold within the last three years. The filtering predicates provide a simple way to partition the property space. We can then build our scraping algorithm based on this and get all listings in given region!

## Algorithm Sketch
At a high-level, we will construct a set of filtering urls to cover all the properties, and then scrape each url for the property details using multiple proxies. Note that, each filtering URL should contain no more than 350 listings due to the pagination system limit.

The algorithm has two phases. With a given region (state, city ..),

1. Partitioning the city region into multiple smaller regions. For example,
the total properties in "san jose, ca" can be partitioned into two smaller parts: those with lot size *less than 3k* and those *no less than 3k*. We can further partition the properties with the region with *not more than 3k lot* into two smaller parts - [(lot size <= 3k and price <= 1M), (lot size <= 3k and price > 1M)]. Finally, each small region should have at most 350 listings.
2. Translating each partition into a filtering URL, and ensure that all listings can be reached with Redfin's pagination system. As we mentioned above, Redfin's pagination can reach at most 350 properties. If there are more than 350 properties under a filtering URL, we need to further partition it until it contains no more than 350 properties.
3. Extract all the properties in the filtering URL. Each filtering url can have multiple paginated results. We need to scrape these paginated URLs as well. As an example, if the url (https://www.redfin.com/city/17420/CA/San-Jose//filter/min-price=830000,max-price=850000,include=sold-3yr) has 30 results, and each url contains 20 results, then the houses matching the filtering criteria are spread among two pages:
https://www.redfin.com/city/17420/CA/San-Jose//filter/min-price=830000,max-price=850000,include=sold-3yr and https://www.redfin.com/city/17420/CA/San-Jose//filter/min-price=830000,max-price=850000,include=sold-3yr/page-2 .

## Questions?
Please start an [issue](https://github.com/wang-ye/redfin-scraper/issues).