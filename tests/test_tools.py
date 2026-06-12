from tools import search_listings

### tool 1 tests 
def test_search_listings_returns_matching_items():
    results = search_listings(
        description="vintage graphic tee",
        size=None,
        max_price=30
    )

    assert isinstance(results, list)
    assert len(results) > 0


def test_search_listings_filters_by_price():
    results = search_listings(
        description="tee",
        size=None,
        max_price=20
    )

    for item in results:
        assert item["price"] <= 20


def test_search_listings_filters_by_size():
    results = search_listings(
        description="shirt",
        size="L",
        max_price=None
    )

    for item in results:
        assert "L" in item["size"].upper()


def test_search_listings_returns_empty_when_no_match():
    results = search_listings(
        description="spacesuit helmet",
        size=None,
        max_price=10
    )

    assert results == []