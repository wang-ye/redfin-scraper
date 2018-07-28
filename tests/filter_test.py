from redfin_filters import add_sqft_filters, add_price_filters, add_year_filters
# from redfin_filters import construct_filter_url


def test_add_sqft_filters():
    assert add_sqft_filters(1000, 1010) == [(1000, 1010)]
    assert add_sqft_filters(1000, 1500) == [(1000, 1100), (1100, 1200), (1200, 1300), (1300, 1400), (1400, 1500)]
    assert add_sqft_filters(1000, 1320) == [(1000, 1060), (1060, 1120), (1120, 1180), (1180, 1240), (1240, 1320)]
    assert add_sqft_filters(10, 10) == [(10, 10)]
    assert add_sqft_filters(10, 13) == [(10, 11), (11, 12), (12, 13)]


def test_add_price_filters():
    assert add_price_filters(10, 10) == [(10, 10)]
    assert add_price_filters(10, 2000000) == [(10, 1000000), (1000000, 2000000)]
    assert add_price_filters(10000, 310000) == [(10000, 70000), (70000, 130000), (130000, 190000), (190000, 250000), (250000, 310000)]
    assert add_price_filters(1200000, 2000000) == [(1200000, 1360000), (1360000, 1520000), (1520000, 1680000), (1680000, 1840000), (1840000, 2000000)]
    assert add_price_filters(1200000, 1220000) == [(1200000, 1210000), (1210000, 1220000)]
    assert add_price_filters(1000, 4000) == [(1000, 2000), (2000, 3000), (3000, 4000)]


def test_add_year_filters():
    assert add_year_filters(10, 10) == [(10, 10)]
    assert add_year_filters(1980, 1983) == [(1980, 1981), (1981, 1982), (1982, 1983)]
