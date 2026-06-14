# FitFindr — planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

---

## Tools

List every tool your agent will use. For each tool, fill in all four fields.
You must have at least 3 tools. The three required tools are listed — add any additional tools below them.

### Tool 1: search_listings

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
Search the mock listings dataset for items matching the description,
optional size, and optional price ceiling. It returns a list of matching listing dicts, sorted by relevance (best match first). If nothing matches, it will return an empty list and does NOT raise an exception.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
description (str): Keywords describing the item.
size (str | None): Optional size filter.
max_price (float | None): Maximum price filter.

**What it returns:**
A list of matching listing dicts, sorted by relevance (best first). Each returned dictionary includes `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform`.

**What happens if it fails or returns nothing:**
<!-- What should the agent do if no listings match? -->
Returns an empty list if nothing matches and doesnt return an exception. If no listing matches, it returns `[]`; it does not raise an exception. 
The planning loop detects the empty list, sets an actionable error message, and returns early without calling `suggest_outfit`.

---

### Tool 2: suggest_outfit

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
Given a thrifted item and the user's wardrobe, this tool generates 1–2 complete outfit suggestions using Groq’s llama-3.3-70b-versatile model. It either incorporates actual wardrobe items (if available) or provides general styling advice when the wardrobe is empty. The output is always a response suitable for a user-facing app.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
new_item (dict): The selected listing dictionary returned by search_listings. This includes fields like title, description, category, style_tags, size, price, and platform.
wardrobe (dict): A dictionary containing an "items" key, which is a list of wardrobe item dictionaries. May be empty ({"items": []}), which must be handled gracefully.


**What it returns:**
<!-- Describe the return value -->
Returns:
A non-empty string containing 1–2 outfit suggestions.
The response must always be user-readable styling advice.

Two cases:
Wardrobe has items
The LLM must reference specific wardrobe items by name.
It must combine the new_item with at least one wardrobe item per outfit suggestion.
Output should describe complete outfits (not just single-item advice).
Wardrobe is empty
The LLM must provide general styling suggestions.
It should describe what types of clothing pair well with the new_item.
It must explicitly acknowledge that the wardrobe is empty in natural language.

Output should be deterministic enough to follow structure, but still natural
Temperature can be moderate (0.7–1.0) for variation

**What happens if it fails or returns nothing:**
<!-- What should the agent do if the wardrobe is empty or no outfit can be suggested? -->
If the new_item is missing or invalid, the tool will return:
Error: missing or invalid new_item input
If the Groq API call fails, times out, or returns empty content, the tool will return:
Error: unable to generate outfit suggestion at this time
The function must never return None or an empty string.

---

### Tool 3: create_fit_card

**What it does:**
This tool generates a short, shareable outfit caption for the thrifted find. This tool uses Groq's `llama-3.3-70b-versatile` model to turn an outfit suggestion and selected listing into a  2–4 sentence caption suitable for an Instagram or TikTok post. It uses a higher temperature than `suggest_outfit` so repeated calls can vary.

**Input parameters:**

outfit (str): A complete outfit suggestion returned by suggest_outfit.
new_item (dict): The selected listing dictionary used in the outfit (includes title, price, platform, and description fields).


**What it returns:**
A non-empty string (2–4 sentences) styled like a social media caption.
Must naturally include:
item name (from new_item["title"])
price (from new_item["price"])
platform (from new_item["platform"])
Must sound like a real user caption, not a product description.
Style requirements:
Casual, TikTok/Instagram tone
May include emojis sparingly
Should feel like a “posted outfit flex”
Must vary across runs (not identical outputs every time)


**What happens if it fails or returns nothing:**
If outfit is empty, None, or invalid it returns:
Error: missing outfit suggestion for fit card generation
If new_item is missing or invalid, it returns:
Error: missing or invalid listing data for fit card generation
If the Groq API call fails or returns empty output, it returns:
Error: unable to generate fit card at this time
The function must never crash or returns None.

---

## Planning Loop

**How does your agent decide which tool to call next?**
<!-- Describe the logic your planning loop uses. What does it look at? What conditions change its behavior? How does it know when it's done? -->

1. Initialize a new session dictionary with the original query, wardrobe, empty parsed values, empty search results, no selected item, no outfit suggestion, no fit card, and no error.
2. Parse the user query with regular expressions and string cleanup:
   - Extract a dollar amount after terms such as `"under"`, `"below"`, `"max"`, or `"budget"` and store it as `max_price`.
   - Extract a size after terms such as `"size"` or a comma-delimited size phrase and store it as `size`.
   - Remove the extracted filter phrases from the query. The remaining cleaned text becomes `description`.
3. Call `search_listings(description, size, max_price)` and save the returned list in `session["search_results"]`.
4. If `session["search_results"]` is empty:
   - Set `session["error"] = "No listings matched your request. Try raising your budget, removing the size filter, or using a broader description."`
   - Return the session immediately.
   - Do not call `suggest_outfit`.
5. Otherwise, set `session["selected_item"] = session["search_results"][0]`.
6. Call `suggest_outfit(session["selected_item"], session["wardrobe"])` and store the returned string in `session["outfit_suggestion"]`.
7. If the outfit suggestion begins with `"Error"`:
   - Copy that message into `session["error"]`
   - Return the session immediately.
   - Do not call `create_fit_card`.
8. Otherwise, call `create_fit_card(session["outfit_suggestion"], session["selected_item"])` and store the result in `session["fit_card"]`.
9. If the fit card begins with `"Error"`, copy that message into `session["error"]`.
10. Return the completed session.

---

## State Management

**How does information from one tool get passed to the next?**
<!-- Describe how your agent stores and accesses state within a session. What data is tracked? How is it passed between tool calls? -->

The agent stores all intermediate information in a session dictionary.
The session is created at the beginning of each user request and
contains:

-   `query` (`str`): the original user message.
-   `wardrobe` (`dict`): the user's saved wardrobe data.
-   `description` (`str`): cleaned item description extracted from the
    query.
-   `size` (`str | None`): extracted size filter.
-   `max_price` (`float | None`): extracted budget limit.
-   `search_results` (`list[dict]`): all matching resale listings
    returned by `search_listings`.
-   `selected_item` (`dict | None`): the highest-ranked listing selected
    from `search_results`.
-   `outfit_suggestion` (`str | None`): the styling recommendation
    returned by `suggest_outfit`.
-   `fit_card` (`str | None`): the social caption returned by
    `create_fit_card`.
-   `error` (`str | None`): any error message that stops the workflow.

Data flows between tools through these stored session values. The
planning loop does not call the next tool until the required previous
output exists. For example, `create_fit_card` receives
`session["outfit_suggestion"]` and `session["selected_item"]`, not raw
user input.

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool             | Failure mode                              | Agent response                                                                                                                                                                      |
|------------------|-------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| search_listings  | No results match the query                | Stops the workflow immediately. Does not call `suggest_outfit`. User sees: "No listings matched your request. Try raising your budget, removing the size filter, or using a broader description." |
| suggest_outfit   | Groq API failure, timeout, or empty response | Tool returns an `"Error: ..."` string. Loop detects the prefix, stores it in `session["error"]`, and exits without calling `create_fit_card`. User sees: "Error: unable to generate outfit suggestion at this time" |
| suggest_outfit   | Empty wardrobe (`wardrobe["items"] == []`) | Tool returns general styling advice (not an error). Workflow continues normally into `create_fit_card`.                                                                              |
| create_fit_card  | Outfit input is missing or empty string   | Tool returns `"Error: missing outfit suggestion for fit card generation"`. Loop stores it in `session["error"]`. User sees that message directly.                                    |
| create_fit_card  | Groq API failure, timeout, or empty response | Tool returns `"Error: unable to generate fit card at this time"`. Loop stores it in `session["error"]`. User sees that message directly.                                            |

-----------------------------------------------------------------------------


## Architecture

<!-- Draw a diagram of your agent showing how the components connect:
     User input → Planning Loop → Tools (search_listings, suggest_outfit, create_fit_card)
                                                                          ↕
                                                                   State / Session
     Show what triggers each tool, how state flows between them, and where error paths branch off.
     ASCII art, a Mermaid diagram (https://mermaid.js.org/syntax/flowchart.html), or an embedded
     sketch are all fine. You'll share this diagram with an AI tool when asking it to implement
     the planning loop and each individual tool. -->


```text
User Query
    │
    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          Planning Loop                              │
│                                                                     │
│  1. Create session dict (query, wardrobe, all fields = None/[])     │
│  2. Parse query → description (str), size (str|None),               │
│                   max_price (float|None)                            │
└────────────────────┬────────────────────────────────────────────────┘
                     │
                     ▼
        ┌────────────────────────┐
        │   search_listings()    │
        │ in: description,       │
        │     size, max_price    │
        └────────────┬───────────┘
                     │
          ┌──────────┴──────────┐
          │                     │
    results = []          results = [item, ...]
          │                     │
          ▼                     ▼
  session["error"] =    session["search_results"] = results
  "No listings          session["selected_item"]  = results[0]
   matched. Try                │
   broader search."            ▼
          │             ┌────────────────────────┐
          │             │   suggest_outfit()      │
          │             │ in: selected_item,      │
          │             │     wardrobe            │
          │             └────────────┬───────────┘
          │                          │
          │             ┌────────────┴────────────┐
          │             │                         │
          │       "Error: ..."           outfit string (success)
          │             │                         │
          │     session["error"]  =    session["outfit_suggestion"]
          │       returned string                 │
          │             │                         ▼
          │             │             ┌────────────────────────┐
          │             │             │   create_fit_card()    │
          │             │             │ in: outfit_suggestion, │
          │             │             │     selected_item      │
          │             │             └────────────┬───────────┘
          │             │                          │
          │             │             ┌────────────┴────────────┐
          │             │             │                         │
          │             │       "Error: ..."          fit card string (success)
          │             │             │                         │
          │             │     session["error"] =   session["fit_card"]
          │             │       returned string                 │
          │             │             │                         │
          └─────────────┴─────────────┴─────────────────────────┘
                                      │
                                      ▼
                            Return session to app
                                      │
                                      ▼
                              ┌───────────────┐
                              │  User sees:   │
                              │  • Top listing│
                              │  • Outfit tip │
                              │  • Fit card   │
                              │  (or error)   │
                              └───────────────┘
```


---

## AI Tool Plan

<!-- For each part of the implementation below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, your agent diagram)
     - What you expect it to produce
     - How you'll verify the output matches your spec before moving on

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Tool 1 spec (inputs, return value, failure mode) and ask it to implement
     search_listings() using load_listings() from the data loader — then test it against 3 queries
     before trusting it" is a plan. -->

- Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)

- What you'll give it as input (which sections of this planning.md, your agent diagram)

# AI Tool Plan

**Tool:** ChatGPT (used for all three milestones below)


**Milestone 3 — `search_listings`**

Input to ChatGPT: the Tool 1 spec block from planning.md (purpose, parameters, return value, filtering rules, relevance scoring, empty-result behavior) plus the existing stub signature from `tools.py`.

Expected output: a function that calls `load_listings()`, filters by `size` and `max_price` when provided, scores each listing for keyword relevance against `description`, drops zero-score results, sorts by score descending, and returns a list of listing dicts (or `[]`).

Verification: before running, confirm the code uses `load_listings()` and not a manual file open. Then run four test cases: a query with matches, a query filtered by size, a query filtered by price, and an impossible query that returns `[]`. All four must match expected output before moving to the next tool.

---

**Milestone 3 — `suggest_outfit`**

Input to ChatGPT: the Tool 2 spec block from planning.md, the wardrobe schema field list, and the existing stub signature.

Expected output: a function that builds a prompt from the selected item and wardrobe items, calls Groq's `llama-3.3-70b-versatile`, returns a styling suggestion string when the wardrobe has items, returns general advice when `wardrobe["items"]` is empty, and returns a readable `"Error: ..."` string on API failure.

Verification: confirm the code does not crash on `{"items": []}`. Run it with a populated wardrobe and confirm wardrobe pieces are named. Run it with an empty wardrobe and confirm it returns advice rather than an error. Simulate an API failure and confirm it returns a string, not an exception.

---

**Milestone 3 — `create_fit_card`**

Input to ChatGPT: the Tool 3 spec block from planning.md and the existing stub signature from `tools.py`.

Expected output: a function that returns `"Error: missing outfit suggestion for fit card generation"` when `outfit` is empty, otherwise builds a prompt using the item name, price, and platform, calls the Groq LLM at a higher temperature, and returns a short social-media caption string.

Verification: confirm the guard clause runs before any API call. Run the same valid input three times and confirm the captions vary. Confirm the caption includes the item name, price, and platform.

---

**Milestone 4 — Planning loop (`run_agent` in `agent.py`)**

Input to ChatGPT: the Planning Loop section from planning.md, the State Management section, the Architecture ASCII diagram, and the three tool signatures from `tools.py`.

Expected output: a `run_agent()` function that initializes the session dict, parses the query into `description`, `size`, and `max_price`, calls the three tools in order, stores each result in the session, and exits early with `session["error"]` set when `search_listings` returns `[]` or either LLM tool returns an `"Error: ..."` string.

Verification: compare the generated code against the architecture diagram branch by branch before running. Then run three integration tests: (1) a valid query that flows through all three tools, (2) an impossible query that stops after `search_listings`, and (3) a query where `suggest_outfit` is forced to return an error to confirm `create_fit_card` is never called. Run `pytest tests/` and confirm all tests pass before connecting to the Gradio app.

---

## A Complete Interaction (Step by Step)

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Wardrobe context:** `session["wardrobe"]` for this user contains two items: a pair of wide-leg dark-wash jeans and a pair of chunky white platform sneakers. This is what `suggest_outfit` will receive alongside the selected listing.

---

**Step 1 — `search_listings`**

The planning loop parses the query and calls:

```python
search_listings(
    description="vintage graphic tee",
    size=None,
    max_price=30.0,
)
```

`search_listings` loads all listings, drops any priced above $30, scores each remaining listing for keyword relevance against `"vintage graphic tee"`, removes zero-score results, and returns the matches sorted by score. The top result is:

```python
{
    "id": "lst_033",
    "title": "Vintage Band Tee — Faded Grey",
    "description": "Faded grey band-style tee with distressed graphic. Crew neck. Fits boxy.",
    "category": "tops",
    "style_tags": ["vintage", "grunge", "band tee", "graphic tee", "streetwear"],
    "size": "L",
    "condition": "fair",
    "price": 19.0,
    "colors": ["grey", "charcoal"],
    "brand": None,
    "platform": "depop",
}
```

The planning loop saves the full list to `session["search_results"]` and sets `session["selected_item"] = results[0]`.

---

**Step 2 — `suggest_outfit`**

The planning loop calls:

```python
suggest_outfit(
    new_item=session["selected_item"],
    wardrobe=session["wardrobe"],
)
```

`suggest_outfit` builds a prompt describing the band tee and the two wardrobe items (wide-leg jeans, chunky sneakers), sends it to Groq's `llama-3.3-70b-versatile`, and returns a styling string. For example:

```text
"Pair the faded graphic tee with your wide-leg dark-wash jeans and chunky
white sneakers for a relaxed grunge-inspired look. Roll the sleeves once
and add a slight front tuck to give the oversized shape more structure."
```

The planning loop stores this in `session["outfit_suggestion"]`.

---

**Step 3 — `create_fit_card`**

The planning loop calls:

```python
create_fit_card(
    outfit=session["outfit_suggestion"],
    new_item=session["selected_item"],
)
```

`create_fit_card` builds a prompt from the outfit suggestion, item title, price, and platform, and returns a short social-media caption. For example:

```text
"found this faded vintage band tee on depop for $19 and it was made for
baggy jeans + chunky sneakers 🖤 rolled the sleeves and did a tiny front
tuck for the easiest grunge fit"
```

The planning loop stores this in `session["fit_card"]` and returns the completed session.

---

**Final output to user:**

```text
Top match:
Vintage Band Tee — Faded Grey
$19 · depop · Size L · Fair condition

Outfit suggestion:
Pair the faded graphic tee with your wide-leg dark-wash jeans and chunky
white sneakers for a relaxed grunge-inspired look. Roll the sleeves once
and add a slight front tuck to give the oversized shape more structure.

Fit card:
found this faded vintage band tee on depop for $19 and it was made for
baggy jeans + chunky sneakers 🖤 rolled the sleeves and did a tiny front
tuck for the easiest grunge fit
```

The exact wording of the outfit suggestion and fit card will vary between runs because both are LLM-generated.




