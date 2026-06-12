"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import os

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.

    Args:
        description: Keywords describing what the user is looking for
                     (e.g., "vintage graphic tee").
        size:        Size string to filter by, or None to skip size filtering.
                     Matching is case-insensitive (e.g., "M" matches "S/M").
        max_price:   Maximum price (inclusive), or None to skip price filtering.

    Returns:
        A list of matching listing dicts, sorted by relevance (best match first).
        Returns an empty list if nothing matches — does NOT raise an exception.

    Each listing dict has the following fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand, platform

    TODO:
        1. Load all listings with load_listings().
        2. Filter by max_price and size (if provided).
        3. Score each remaining listing by keyword overlap with `description`.
        4. Drop any listings with a score of 0 (no relevant matches).
        5. Sort by score, highest first, and return the listing dicts.

    Before writing code, fill in the Tool 1 section of planning.md.
    """
    
    # Load all listings from dataset
    listings = load_listings()

    # Clean user description into searchable keywords
    keywords = set(description.lower().split())

    scored_results = []

    for item in listings:

        # Filter by price
        if max_price is not None and item.get("price", float("inf")) > max_price:
            continue

        # Filter by size
        if size:
            requested_size = size.lower()
            item_size = str(item.get("size", "")).lower()

            # Allows "M" to match "S/M"
            if requested_size not in item_size:
                continue

        # Build searchable text from listing fields
        searchable_text = " ".join(
            [
                str(item.get("title", "")),
                str(item.get("description", "")),
                str(item.get("category", "")),
                " ".join(item.get("style_tags", [])),
                " ".join(item.get("colors", [])),
                str(item.get("brand", "")),
                str(item.get("platform", "")),
            ]
        ).lower()

        # Calculate keyword overlap score
        score = sum(
            1 for keyword in keywords
            if keyword in searchable_text
        )

        # Only keep relevant matches
        if score > 0:
            scored_results.append((score, item))

    # Sort by highest relevance score first
    scored_results.sort(
        key=lambda result: result[0],
        reverse=True
    )

    # Return only listing dictionaries
    return [item for score, item in scored_results]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.

    Args:
        new_item: A listing dict (the item the user is considering buying).
        wardrobe: A wardrobe dict with an 'items' key containing a list of
                  wardrobe item dicts. May be empty — handle this gracefully.

    Returns:
        A non-empty string with outfit suggestions.
        If the wardrobe is empty, offer general styling advice for the item
        rather than raising an exception or returning an empty string.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If empty: call the LLM with a prompt for general styling ideas
           (what kinds of items pair well, what vibe it suits, etc.).
        3. If not empty: format the wardrobe items into a prompt and ask
           the LLM to suggest specific outfit combinations using the new item
           and named pieces from the wardrobe.
        4. Return the LLM's response as a string.

    Before writing code, fill in the Tool 2 section of planning.md.
    """
    # Replace this with your implementation


    client = Groq(api_key=os.getenv("GROQ_API_KEY"))


   
    # 1. Validate inputs
  
    if not new_item or not isinstance(new_item, dict):
        return "Error: missing or invalid new_item input"

    items = wardrobe.get("items", []) if wardrobe else []

    # 2. Format new item
   
    item_text = (
        f"Title: {new_item.get('title', 'N/A')}\n"
        f"Description: {new_item.get('description', 'N/A')}\n"
        f"Category: {new_item.get('category', 'N/A')}\n"
        f"Style tags: {new_item.get('style_tags', [])}\n"
        f"Price: {new_item.get('price', 'N/A')}\n"
        f"Platform: {new_item.get('platform', 'N/A')}\n"
    )

   
    # 3. Handle wardrobe empty vs not
   
    if len(items) == 0:
        wardrobe_text = (
            "The user's wardrobe is empty. "
            "Give general styling advice and suggest what items would pair well."
        )
    else:
        wardrobe_text = "User wardrobe items:\n"
        for i, w in enumerate(items[:10]):
            wardrobe_text += (
                f"{i+1}. {w.get('title', 'Unknown')} "
                f"({w.get('category', 'unknown')}, "
                f"size {w.get('size', 'N/A')})\n"
            )

    # 4. Build prompt
    prompt = f"""
    You are a fashion styling assistant.

    Task:
    Create 1–2 complete outfit suggestions using the thrifted item.

    Rules:
    - Always include the thrifted item.
    - If wardrobe items exist, use at least one named wardrobe item per outfit.
    - If wardrobe is empty, give general styling advice.
    - Keep tone casual, aesthetic, and natural.
    - Do NOT use JSON or bullet points.

    THRIFTED ITEM:
    {item_text}

    WARDROBE:
    {wardrobe_text}
    """

    # 5. Call Groq LLM
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
        )

        output = response.choices[0].message.content.strip()

        if not output:
            return "Error: unable to generate outfit suggestion at this time"

        return output

    except Exception:
        return "Error: unable to generate outfit suggestion at this time"


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.

    Args:
        outfit:   The outfit suggestion string from suggest_outfit().
        new_item: The listing dict for the thrifted item.

    Returns:
        A 2–4 sentence string usable as an Instagram/TikTok caption.
        If outfit is empty or missing, return a descriptive error message
        string — do NOT raise an exception.

    The caption should:
    - Feel casual and authentic (like a real OOTD post, not a product description)
    - Mention the item name, price, and platform naturally (once each)
    - Capture the outfit vibe in specific terms
    - Sound different each time for different inputs (use higher LLM temperature)

    TODO:
        1. Guard against an empty or whitespace-only outfit string.
        2. Build a prompt that gives the LLM the item details and the outfit,
           and asks for a caption matching the style guidelines above.
        3. Call the LLM and return the response.

    Before writing code, fill in the Tool 3 section of planning.md.
    """
    # Replace this with your implementation
    return ""
