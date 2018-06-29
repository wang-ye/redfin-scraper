# rf-scraper
A proxy-based scraper to extract properties from Redfin with filters.
Especially useful when you want to crawl **all** properties in a given state or city.

# High-level Idea
When searching on hot regions like "San Jose, CA", Redfin could return tens of thousands properties. Redfin provides the result pagination, but you can at most access 400 properties at most. How can we get all properties for a given region effectively?

The answer lies in Redfin's filtering queries. Redfin provides filtering criteria like lot size, price and number of beds/baths. More specifically, you can filter based on the min/max value of the above criterias. We can construct the queries carefully to cover all the properties! One filtering url is 

https://www.redfin.com/city/17420/CA/San-Jose/filter/min-price=750k,max-price=780k,min-lot-size=3k-sqft,max-lot-size=4k-sqft,include=sold-3yr

It basically says we want to find all properties in San Jose, CA, having price between [750k, 780k], and sqrt lot size between [3k, 4k], and sold within the last three years. The filtering predicates provide a simple way to partition the property space. We can build our scraping algorithm based on this.

# Algorithm Sketch
The algorithm has two phases. With a given region (state, city ..),
1. Partitioning the city region into multiple smaller regions. For example,
the total properties in "san jose, ca" can be partitioned into two smaller parts: those with lot size *less than 3k* and those *no less than 3k*. We can further partition the properties with the region with <= 3k into [(lot size <= 3k and price <= 1M), (lot size <= k and price > 1M)].
2. Translating each partition into a filtering URL, and extract all the properties in that URL. Note that under each partition there are at most 18 pages * 20 properties per page = 360 properties. If it has more than 360 properties, we need to further partition the region. We also need to scrape all pages to get properties for each sub-region. Note that, each filtering url can contain multiple paginated results. You may also want to append the page ids to the filtering url.

# How to Use
1. Code is tested against python 3.6
2. You need sqlite installed.
3. You need a list of proxies. You can buy proxies online, or use a free service like [proxybroker](http://proxybroker.readthedocs.io/en/latest/). The repo assumes the use of proxies with user and password authorization.
4. Run ``pip install -r requirements``
