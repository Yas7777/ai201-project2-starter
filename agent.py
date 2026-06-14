"""
agent.py

The FitFindr planning loop. Orchestrates the three tools in response to a
natural language user query, passing state between them via a session dict.

Complete tools.py and test each tool in isolation before implementing this file.

Usage (once implemented):
    from agent import run_agent
    from utils.data_loader import get_example_wardrobe

    result = run_agent(
        query="vintage graphic tee under $30, size M",
        wardrobe=get_example_wardrobe(),
    )
    print(result["fit_card"])
    print(result["error"])   # None on success
"""

from tools import search_listings, suggest_outfit, create_fit_card


# ── session state ─────────────────────────────────────────────────────────────

def _new_session(query: str, wardrobe: dict) -> dict:
    """
    Initialize and return a fresh session dict for one user interaction.

    The session dict is the single source of truth for everything that happens
    during a run — it stores the original query, parsed parameters, tool results,
    and any error that caused early termination.

    You may add fields to this dict as needed for your implementation.
    """
    return {
        "query": query,              # original user query
        "parsed": {},                # extracted description / size / max_price
        "search_results": [],        # list of matching listing dicts
        "selected_item": None,       # top result, passed into suggest_outfit
        "wardrobe": wardrobe,        # user's wardrobe dict
        "outfit_suggestion": None,   # string returned by suggest_outfit
        "fit_card": None,            # string returned by create_fit_card
        "error": None,               # set if the interaction ended early
    }


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    session = _new_session(query, wardrobe)

    # ── Step 2: simple parsing (safe minimal version) ──
    import re

    max_price = None
    size = None

    # price extraction
    price_match = re.search(r"(?:under|below|max|budget)\s*\$?(\d+)", query.lower())
    if price_match:
        max_price = float(price_match.group(1))

    # size extraction
    size_match = re.search(r"\bsize\s*([a-z0-9]+)\b", query.lower())
    if size_match:
        size = size_match.group(1).upper()

    # clean description (remove filters crudely)
    description = re.sub(r"(under|below|max|budget)\s*\$?\d+", "", query, flags=re.I)
    description = re.sub(r"size\s*[a-z0-9]+", "", description, flags=re.I).strip()

    session["parsed"] = {
        "description": description,
        "size": size,
        "max_price": max_price,
    }

    # ── Step 3: search_listings ──
    results = search_listings(description, size, max_price)
    session["search_results"] = results

    if not results:
        session["error"] = (
            "No listings matched your request. "
            "Try raising your budget, removing the size filter, "
            "or using a broader description."
        )
        return session

    # ── Step 4: select item ──
    session["selected_item"] = results[0]

    # ── Step 5: suggest outfit ──
    outfit = suggest_outfit(session["selected_item"], session["wardrobe"])
    session["outfit_suggestion"] = outfit

    if isinstance(outfit, str) and outfit.startswith("Error"):
        session["error"] = outfit
        return session

    # ── Step 6: create fit card ──
    fit_card = create_fit_card(outfit, session["selected_item"])
    session["fit_card"] = fit_card

    if isinstance(fit_card, str) and fit_card.startswith("Error"):
        session["error"] = fit_card

    # ── Step 7: return session ──
    return session


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

    print("=== Happy path: graphic tee ===\n")

    session = run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    )

    if session.get("error"):
        print(f"Error: {session['error']}")
    else:
        selected = session.get("selected_item") or {}

        print(f"Found: {selected.get('title', 'N/A')}")
        print(f"\nOutfit: {session.get('outfit_suggestion', '')}")
        print(f"\nFit card: {session.get('fit_card', '')}")

    print("\n\n=== No-results path ===\n")

    session2 = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )

    print(f"Error message: {session2.get('error')}")