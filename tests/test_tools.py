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

#tool 2

from tools import suggest_outfit


# -----------------------------
# Helper fake data
# -----------------------------
sample_item = {
    "title": "Vintage Band Tee",
    "description": "Faded black graphic tee",
    "category": "tops",
    "style_tags": ["vintage", "grunge"],
    "price": 20,
    "platform": "depop"
}



# 1. Test normal wardrobe case

def test_suggest_outfit_with_wardrobe():
    wardrobe = {
        "items": [
            {
                "title": "Baggy Jeans",
                "category": "bottoms",
                "size": "M"
            }
        ]
    }

    result = suggest_outfit(sample_item, wardrobe)

    assert isinstance(result, str)
    assert len(result) > 0
    assert "Error" not in result

# 2. Test empty wardrobe fallback

def test_suggest_outfit_empty_wardrobe():
    wardrobe = {"items": []}

    result = suggest_outfit(sample_item, wardrobe)

    assert isinstance(result, str)
    assert len(result) > 0
    assert "Error" not in result
    # should still produce styling advice, not crash



# 3. Test missing wardrobe key safety

def test_suggest_outfit_missing_wardrobe():
    wardrobe = {}

    result = suggest_outfit(sample_item, wardrobe)

    assert isinstance(result, str)
    assert len(result) > 0

# 4. Test invalid new_item handling

def test_suggest_outfit_invalid_item():
    wardrobe = {"items": []}

    result = suggest_outfit(None, wardrobe)

    assert isinstance(result, str)
    assert result.startswith("Error")
