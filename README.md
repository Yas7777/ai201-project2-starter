# FitFindr

FitFindr is an AI-powered secondhand shopping assistant. You describe what you're looking for in natural language, and the agent searches a mock thrift dataset, suggests how to style the find with your existing wardrobe, and generates a shareable outfit caption — all in a single interaction.

## Setup

```bash
pip install -r requirements.txt
```

Add your Groq API key to a `.env` file in the project root (free key at [console.groq.com](https://console.groq.com)):

```
GROQ_API_KEY=your_key_here
```

Run the app:

```bash
python app.py
```

Open the URL shown in your terminal (typically `http://localhost:7860`).

---

## Tool Inventory

### `search_listings(description, size, max_price)`

**Purpose:** Searches the mock listings dataset for secondhand items that match the user's request.

**Inputs:**
- `description` (`str`) — keywords describing the item (e.g., `"vintage graphic tee"`). Used to score each listing by keyword overlap against its title, description, category, style tags, colors, brand, and platform.
- `size` (`str | None`) — optional size filter (e.g., `"M"`). Matching is case-insensitive and substring-based so `"M"` matches `"S/M"`. Pass `None` to skip.
- `max_price` (`float | None`) — optional price ceiling (inclusive). Pass `None` to skip.

**Returns:** A list of listing dicts sorted by relevance score (highest first). Each dict contains: `id`, `title`, `description`, `category`, `style_tags` (list), `size`, `condition`, `price` (float), `colors` (list), `brand`, and `platform`. Returns `[]` if nothing matches — never raises an exception.

---

### `suggest_outfit(new_item, wardrobe)`

**Purpose:** Uses the Groq LLM (`llama-3.3-70b-versatile`) to generate 1–2 complete outfit suggestions for a thrifted item, drawing on the user's existing wardrobe when available.

**Inputs:**
- `new_item` (`dict`) — the selected listing dict returned by `search_listings`. Must include `title`, `description`, `category`, `style_tags`, `price`, and `platform`.
- `wardrobe` (`dict`) — a dict with an `"items"` key containing a list of wardrobe item dicts. Accepts an empty wardrobe (`{"items": []}`) gracefully.

**Returns:** A non-empty string with outfit suggestions. If the wardrobe has items, the LLM references specific pieces by name and builds complete outfits. If the wardrobe is empty, the LLM provides general styling advice describing what kinds of pieces pair well with the new item. Returns an `"Error: ..."` string (never `None`) if the input is invalid or the API call fails.

---

### `create_fit_card(outfit, new_item)`

**Purpose:** Uses the Groq LLM to turn the outfit suggestion into a 2–4 sentence social media caption suitable for Instagram or TikTok. Temperature is set higher than `suggest_outfit` so captions vary across runs.

**Inputs:**
- `outfit` (`str`) — the outfit suggestion string returned by `suggest_outfit`.
- `new_item` (`dict`) — the selected listing dict. Used to pull `title`, `price`, and `platform` into the caption naturally.

**Returns:** A non-empty string written in a casual, aesthetic first-person voice. The caption mentions the item name, price, and resale platform exactly once each. Returns an `"Error: ..."` string if either input is missing or invalid, or if the API call fails.

---

## How the Planning Loop Works

The agent does not call all three tools unconditionally. It checks the output of each step before deciding whether to continue.

**Step 1 — Parse the query.**
The loop uses regular expressions to extract a price ceiling (after words like "under", "below", "max", or "budget"), a size (after the word "size"), and a cleaned description (the query with those filter phrases removed). These become `description`, `size`, and `max_price`.

**Step 2 — Search for listings.**
The loop calls `search_listings(description, size, max_price)` and stores the result in `session["search_results"]`.

**Decision point:** If `search_results` is empty, the loop sets a specific error message and returns immediately. `suggest_outfit` and `create_fit_card` are never called because there is no item to style. The user sees: *"No listings matched your request. Try raising your budget, removing the size filter, or using a broader description."*

**Step 3 — Select the top item.**
If results were found, the loop sets `session["selected_item"] = session["search_results"][0]` — the highest-relevance match.

**Step 4 — Generate an outfit suggestion.**
The loop calls `suggest_outfit(session["selected_item"], session["wardrobe"])` and stores the result in `session["outfit_suggestion"]`.

**Decision point:** If the returned string starts with `"Error"`, the loop copies it into `session["error"]` and returns immediately. `create_fit_card` is not called because a valid outfit string is required as its input.

**Step 5 — Generate a fit card.**
The loop calls `create_fit_card(session["outfit_suggestion"], session["selected_item"])` and stores the result in `session["fit_card"]`. If this also returns an error string, the loop records it in `session["error"]` but still returns the completed session (the listing and outfit suggestion are still valid outputs).

**Step 6 — Return the session.**
The session dict is returned to `app.py`, which maps `selected_item`, `outfit_suggestion`, and `fit_card` to the three Gradio output panels.

### Architecture

```
User Query
    │
    ▼
┌─────────────────────────────────────┐
│ Planning Loop                       │
│  parse → description, size, budget  │
└─────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────┐
│ search_listings(description,         │
│                 size, max_price)     │
└──────────────────────────────────────┘
    │
    ├─── results = [] ──► ERROR: "No listings matched…" → return session
    │
    │ results found → session["selected_item"] = results[0]
    ▼
┌──────────────────────────────────────┐
│ suggest_outfit(selected_item,        │
│                wardrobe)             │
└──────────────────────────────────────┘
    │
    ├─── starts with "Error" ──► session["error"] = msg → return session
    │
    │ success → session["outfit_suggestion"] = string
    ▼
┌──────────────────────────────────────┐
│ create_fit_card(outfit_suggestion,   │
│                 selected_item)       │
└──────────────────────────────────────┘
    │
    ├─── starts with "Error" ──► session["error"] = msg
    │
    │ success → session["fit_card"] = string
    ▼
Return completed session → Gradio UI
```

---

## State Management

All information is stored in a single session dictionary created at the start of each request. No state is persisted between requests.

| Key | Type | Set when | Used by |
|---|---|---|---|
| `query` | `str` | Initialization | Parsing step |
| `wardrobe` | `dict` | Initialization | `suggest_outfit` |
| `parsed` | `dict` | After regex parsing | `search_listings` call |
| `search_results` | `list[dict]` | After `search_listings` | Decision point, `selected_item` |
| `selected_item` | `dict \| None` | After results found | `suggest_outfit`, `create_fit_card` |
| `outfit_suggestion` | `str \| None` | After `suggest_outfit` | `create_fit_card` |
| `fit_card` | `str \| None` | After `create_fit_card` | Gradio UI |
| `error` | `str \| None` | On any failure | Gradio UI (early return) |

Tools never receive raw user input directly. Each tool only receives values that were already validated and stored by a previous step. For example, `create_fit_card` receives `session["outfit_suggestion"]` and `session["selected_item"]` — not anything the user typed.

---

## Error Handling

### `search_listings` — no results

**Failure mode:** No listings match the description, size, and price combination.

**Agent response:** Sets `session["error"]` to a specific, actionable message and returns the session immediately without calling the outfit tools.

**Concrete test — deliberately triggered:**
```
Query: "designer ballgown size XXS under $5"
```
```
Error message: No listings matched your request. Try raising your budget,
removing the size filter, or using a broader description.
```
The agent stopped after `search_listings` and returned. `suggest_outfit` and `create_fit_card` were never called.

---

### `suggest_outfit` — API failure or invalid input

**Failure mode:** The Groq API times out, returns an empty response, or `new_item` is `None` or not a dict.

**Agent response:** The tool returns an `"Error: ..."` string. The planning loop detects that the string starts with `"Error"`, copies it into `session["error"]`, and returns the session before calling `create_fit_card`.

Note: an empty wardrobe is not a failure — it is handled gracefully by switching the prompt to request general styling advice rather than wardrobe-specific outfits.

---

### `create_fit_card` — missing outfit input

**Failure mode:** `outfit` is an empty string, whitespace only, or `None`; or `new_item` is missing.

**Agent response:** The tool returns an `"Error: missing outfit suggestion for fit card generation"` string without calling the LLM. The planning loop stores this in `session["error"]`. The listing and outfit suggestion (if present) are still returned to the UI; only the fit card panel is empty.

---

## Spec Reflection

**One way the spec helped:** Writing out the planning loop step-by-step in `planning.md` before any code made the early-exit logic very easy to implement. Because the conditions for stopping (`results == []`, `outfit.startswith("Error")`) were already defined in plain language, the `agent.py` code mapped almost directly to the spec. The session dictionary structure was also defined before coding, which meant there was no ambiguity about what to name each key or when to set it.

**One divergence and why:** The error handling table in `planning.md` described the `suggest_outfit` failure mode as "the agent continues normally and generates general styling advice using common clothing basics." This was imprecise — that description applies to the *empty wardrobe* path, not an API failure. When the Groq API actually fails, `suggest_outfit` returns an `"Error: ..."` string and the planning loop stops. The table was corrected to separate these two cases: an empty wardrobe triggers a different prompt branch inside the tool (not an error), while an API failure causes the tool to return an error string and the loop to exit early.

---

## AI Usage

### Instance 1 — Implementing `search_listings`

I gave ChatGPT the Tool 1 section of `planning.md` (the function purpose, all three parameter descriptions with types, the return value spec listing all 11 dict fields, the filtering rules, the keyword scoring requirement, and the empty-result behavior), along with the existing function signature and docstring from `tools.py`. I asked it specifically to use `load_listings()` from the data loader rather than re-opening the JSON file directly.

The generated code was structurally correct but had one issue: it used `in item_size` for the size check, which would match `"XL"` when the user searched for `"L"` since `"l"` is in `"xl"` after lowercasing. I changed the check to use `requested_size not in item_size` after reviewing the test case `test_search_listings_filters_by_size` — the spec required `"L"` to match `"L"` items, not `"XL"` items. I rewrote the size comparison logic before using the function.

### Instance 2 — Implementing the planning loop in `agent.py`

I gave ChatGPT the Planning Loop section from `planning.md` (all 10 numbered steps), the State Management section (the full session key table), the ASCII architecture diagram, and the three tool signatures from `tools.py`. I asked it to generate `run_agent()` and `_new_session()`.

The generated code checked for `suggest_outfit` failure using `outfit.startswith("I couldn't")`, which did not match the `"Error: ..."` strings the tools actually return. I caught this by comparing the generated agent against the tool return-value specs in planning.md and running the no-results test path. I changed the check to `outfit.startswith("Error")` to match the actual tool output, and applied the same fix to the `create_fit_card` error check.