from redfin_filters import add_sqft_filters, add_price_filters, add_year_filters, apply_filters, REDFIN_BASE_URL


# def test_add_sqft_filters():
#     assert add_sqft_filters(1000, 1010) == [(1000, 1010)]
#     assert add_sqft_filters(1000, 1500) == [(1000, 1100), (1100, 1200), (1200, 1300), (1300, 1400), (1400, 1500)]
#     assert add_sqft_filters(1000, 1320) == [(1000, 1060), (1060, 1120), (1120, 1180), (1180, 1240), (1240, 1320)]
#     assert add_sqft_filters(10, 10) == [(10, 10)]
#     assert add_sqft_filters(10, 13) == [(10, 11), (11, 12), (12, 13)]


# def test_add_price_filters():
#     assert add_price_filters(10, 10) == [(10, 10)]
#     assert add_price_filters(10, 2000000) == [(10, 1000000), (1000000, 2000000)]
#     assert add_price_filters(10000, 310000) == [(10000, 70000), (70000, 130000), (130000, 190000), (190000, 250000), (250000, 310000)]
#     assert add_price_filters(1200000, 2000000) == [(1200000, 1360000), (1360000, 1520000), (1520000, 1680000), (1680000, 1840000), (1840000, 2000000)]
#     assert add_price_filters(1200000, 1220000) == [(1200000, 1210000), (1210000, 1220000)]
#     assert add_price_filters(1000, 4000) == [(1000, 2000), (2000, 3000), (3000, 4000)]


# def test_add_year_filters():
#     assert add_year_filters(10, 10) == [(10, 10)]
#     assert add_year_filters(1980, 1983) == [(1980, 1981), (1981, 1982), (1982, 1983)]


def test_apply_filters():
    def base_url():
        sub_urls = apply_filters('https://www.redfin.com/city/17420/CA/San-Jose/')
        assert sub_urls == [REDFIN_BASE_URL + 'filter/include=sold-3yr,min-price=1000,max-price=1000000', REDFIN_BASE_URL + 'filter/include=sold-3yr,min-price=1000000,max-price=2000000']

    def price_only_url():
        sub_urls = apply_filters('https://www.redfin.com/city/17420/CA/San-Jose/filter/include=sold-3yr,min-price=1000000,max-price=2000000')
        assert sub_urls == [
            REDFIN_BASE_URL + 'filter/include=sold-3yr,min-price=1000000,max-price=1200000',
            REDFIN_BASE_URL + 'filter/include=sold-3yr,min-price=1200000,max-price=1400000',
            REDFIN_BASE_URL + 'filter/include=sold-3yr,min-price=1400000,max-price=1600000',
            REDFIN_BASE_URL + 'filter/include=sold-3yr,min-price=1600000,max-price=1800000',
            REDFIN_BASE_URL + 'filter/include=sold-3yr,min-price=1800000,max-price=2000000',
        ]

        sub_urls = apply_filters('https://www.redfin.com/city/17420/CA/San-Jose/filter/include=sold-3yr,min-price=100000,max-price=101000')
        assert sub_urls == [
            REDFIN_BASE_URL + 'filter/include=sold-3yr,min-price=100000,max-price=101000,min-sqft=10-sqft,max-sqft=1000-sqft',
            REDFIN_BASE_URL + 'filter/include=sold-3yr,min-price=100000,max-price=101000,min-sqft=1000-sqft,max-sqft=12000-sqft',
        ]

    def price_sqft_filter_url():
        sub_urls = apply_filters('https://www.redfin.com/city/17420/CA/San-Jose/filter/include=sold-3yr,min-price=100000,max-price=101000,min-sqft=10-sqft,max-sqft=1000-sqft')
        assert sub_urls == [
            REDFIN_BASE_URL + 'filter/include=sold-3yr,min-price=100000,max-price=101000,min-sqft=10-sqft,max-sqft=208-sqft',
            REDFIN_BASE_URL + 'filter/include=sold-3yr,min-price=100000,max-price=101000,min-sqft=208-sqft,max-sqft=406-sqft',
            REDFIN_BASE_URL + 'filter/include=sold-3yr,min-price=100000,max-price=101000,min-sqft=406-sqft,max-sqft=604-sqft',
            REDFIN_BASE_URL + 'filter/include=sold-3yr,min-price=100000,max-price=101000,min-sqft=604-sqft,max-sqft=802-sqft',
            REDFIN_BASE_URL + 'filter/include=sold-3yr,min-price=100000,max-price=101000,min-sqft=802-sqft,max-sqft=1000-sqft',
        ]

        sub_urls = apply_filters('https://www.redfin.com/city/17420/CA/San-Jose/filter/include=sold-3yr,min-price=100000,max-price=101000,min-sqft=10-sqft,max-sqft=11-sqft')
        assert sub_urls == [
            REDFIN_BASE_URL + 'filter/include=sold-3yr,min-price=100000,max-price=101000,min-sqft=10-sqft,max-sqft=11-sqft,min-year-built=1900,max-year-built=2018'
        ]

    def price_sqft_year_filter_url():
        sub_urls = apply_filters(REDFIN_BASE_URL + 'filter/include=sold-3yr,min-price=100000,max-price=101000,min-sqft=10-sqft,max-sqft=11-sqft,min-year-built=1900,max-year-built=2000')
        assert sub_urls == [
            REDFIN_BASE_URL + 'filter/include=sold-3yr,min-price=100000,max-price=101000,min-sqft=10-sqft,max-sqft=11-sqft,min-year-built=1900,max-year-built=1920',
            REDFIN_BASE_URL + 'filter/include=sold-3yr,min-price=100000,max-price=101000,min-sqft=10-sqft,max-sqft=11-sqft,min-year-built=1920,max-year-built=1940',
            REDFIN_BASE_URL + 'filter/include=sold-3yr,min-price=100000,max-price=101000,min-sqft=10-sqft,max-sqft=11-sqft,min-year-built=1940,max-year-built=1960',
            REDFIN_BASE_URL + 'filter/include=sold-3yr,min-price=100000,max-price=101000,min-sqft=10-sqft,max-sqft=11-sqft,min-year-built=1960,max-year-built=1980',
            REDFIN_BASE_URL + 'filter/include=sold-3yr,min-price=100000,max-price=101000,min-sqft=10-sqft,max-sqft=11-sqft,min-year-built=1980,max-year-built=2000',
        ]

    base_url()
    price_only_url()
    price_sqft_filter_url()
    price_sqft_year_filter_url()
