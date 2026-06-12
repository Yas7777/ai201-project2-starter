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
    optional size, and optional price ceiling.Returns:
        A list of matching listing dicts, sorted by relevance (best match first).
        Returns an empty list if nothing matches — does NOT raise an exception.


**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `description` Keywords describing what the user is looking for.
- `size` Size string such as S/M/L etc to filter by, or None to skip size filtering (case-insensitive) 
- `max_price` Maximum price (inclusive), or None to skip price filtering.

**What it returns:**
A list of matching listing dicts, sorted by relevance (best first). Each returned dictionary includes `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform`.

**What happens if it fails or returns nothing:**
<!-- What should the agent do if no listings match? -->
Returns an empty list if nothing matches and doesnt return an exception. If no listing matches, it returns `[]`; it does not raise an exception. 

CHECK -->The planning loop detects the empty list, sets an actionable error message, and returns early without calling `suggest_outfit`.

---

### Tool 2: suggest_outfit

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
Given a thrifted item and the user's wardrobe, the tool suggests 1–2 complete outfits. It uses Groq's `llama-3.3-70b-versatile` model to create one or two concise styling suggestions based on what is provided. When wardrobe items exist, it asks the LLM to use named pieces from the wardrobe. When the wardrobe is empty, it asks for practical general styling advice using common basics.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `new_item` A listing dict (the item the user is considering buying).
- `wardrobe` A wardrobe dict with an 'items' key containing a list of wardrobe item dicts. May be empty — handle this gracefully.

**What it returns:**
<!-- Describe the return value -->
Returns: A non-empty string with outfit suggestions. If the wardrobe is empty, offer general styling advice for the item
rather than raising an exception or returning an empty string.For a populated wardrobe, the response should name usable wardrobe pieces. For an empty wardrobe, it should explicitly say the saved wardrobe is empty and offer general pairings.


**What happens if it fails or returns nothing:**
<!-- What should the agent do if the wardrobe is empty or no outfit can be suggested? -->
check -->
- `wardrobe` A wardrobe dict with an 'items' key containing a list of wardrobe item dicts. May be empty — handle this gracefully. If `new_item` is missing, the tool returns a descriptive error string. If the wardrobe is empty, the tool still calls the LLM with a safe fallback prompt. If the Groq request fails or returns blank content, the tool returns a readable error string rather than raising an exception.

---

### Tool 3: create_fit_card

**What it does:**
Generate a short, shareable outfit caption for the thrifted find. This tool uses Groq's `llama-3.3-70b-versatile` model to turn an outfit suggestion and selected listing into a  2–4 scaption suitable for an Instagram or TikTok post. It uses a higher temperature than `suggest_outfit` so repeated calls can vary.

**Input parameters:**
- `outfit` (`str`): The outfit suggestion returned by `suggest_outfit`.
- `new_item` (`dict`): The selected listing dictionary.


**What it returns:**
 A 2–4 sentence string usable as an Instagram/TikTok caption. A non-empty `str` containing a casual caption that mentions the item name, price, and resale platform naturally once each and describes the outfit vibe.

**What happens if it fails or returns nothing:**
<!-- What should the agent do if the outfit data is incomplete? -->

CHECK -->
If `outfit` is empty or missing, the tool returns a descriptive error string and does not call the LLM. If `new_item` is missing, it returns a descriptive error string. If the Groq request fails or returns blank content, it returns a readable error string rather than raising an exception.

---

### Additional Tools (if any)

<!-- Copy the block above for any tools beyond the required three -->

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
7. If the outfit suggestion begins with `"I couldn't"`:
   - Copy that message into `session["error"]`.
   - Return the session immediately.
   - Do not call `create_fit_card`.
8. Otherwise, call `create_fit_card(session["outfit_suggestion"], session["selected_item"])` and store the result in `session["fit_card"]`.
9. If the fit card begins with `"I couldn't"`, copy that message into `session["error"]`.
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

----------------------------------------------------------------------------
  Tool              Failure mode               Agent response
  ----------------- -------------------------- --------------------------------
  search_listings   No results match the query The agent stops the workflow and
                                               returns: "No listings matched
                                               your request. Try raising your
                                               budget, removing the size
                                               filter, or using a broader
                                               description." It does not call
                                               the outfit tools because there
                                               is no item to style.

  suggest_outfit    Wardrobe is empty          The agent continues normally. It
                                               tells the tool to generate
                                               general styling advice using
                                               common clothing basics instead
                                               of wardrobe-specific pieces.

  create_fit_card   Outfit input is missing or The agent stops before
                    incomplete                 generating a caption and
                                               returns: "I couldn't create a
                                               fit card because the outfit
                                               suggestion is missing. Please
                                               generate an outfit suggestion
                                               first."
  -----------------------------------------------------------------------------

---

## Architecture

<!-- Draw a diagram of your agent showing how the components connect:
     User input → Planning Loop → Tools (search_listings, suggest_outfit, create_fit_card)
                                                                          ↕
                                                                   State / Session
     Show what triggers each tool, how state flows between them, and where error paths branch off.
     ASCII art, a Mermaid diagram (https://mermaid.js.org/syntax/flowchart.html), or an embedded
     sketch are all fine. You'll share this diagram with an AI tool when asking it to implement
     the planning loop and each individual tool. -->


``` text
User Query
    |
    v
+----------------+
| Planning Loop  |
+----------------+
    |
    | parse description, size, budget
    v
+-----------------------------+
| search_listings()           |
| input: description, size,   |
| max_price                   |
+-----------------------------+
    |
    +--------------------+
    | results = []        |
    v                     |
[ERROR] No listings       |
found -> return session   |
                          |
    results found         |
    v                     |
Session: selected_item    |
    |
    v
+-----------------------------+
| suggest_outfit()            |
| input: selected_item,       |
| wardrobe                    |
+-----------------------------+
    |
    +--------------------+
    | error string        |
    v                     |
[ERROR] return session   |
                          |
    success               |
    v
Session: outfit_suggestion
    |
    v
+-----------------------------+
| create_fit_card()           |
| input: outfit_suggestion,   |
| selected_item               |
+-----------------------------+
    |
    +--------------------+
    | error string        |
    v                     |
[ERROR] return session
                          |
    success
    v
Session: fit_card
    |
    v
Return completed session to User
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

I will use ChatGPT to implement one tool at a time. For `search_listings`, I will provide the Tool 1 specification and the starter docstring from `tools.py`, and ask it to use `load_listings()` rather than reopening the JSON file. Before running the result, I will confirm that it applies the optional price and size filters, scores text relevance, sorts best matches first, and returns `[]` when nothing matches.

For `suggest_outfit`, I will provide the Tool 2 specification, the wardrobe schema notes, and the starter signature. I will ask ChatGPT to use Groq's `llama-3.3-70b-versatile` model and to handle both a populated wardrobe and an empty wardrobe. I will verify that the code does not crash on `{"items": []}`, names wardrobe pieces when available, and returns a readable error string when the API call fails.

For `create_fit_card`, I will provide the Tool 3 specification and the starter signature. I will ask ChatGPT to guard against blank outfit input, include the item name, platform, and price in the prompt, and use a higher temperature for varied captions. I will call it several times with the same valid input and confirm that the output can vary.

- What you expect it to produce


- How you'll verify the output matches your spec before moving on
After reviewing each function, I will run `pytest tests/` and confirm that every normal path and required failure mode passes before connecting the tools.


**Milestone 3 — Individual tool implementations:**
For this milestone, I will use ChatGPT to implement the three required tools in `tools.py`.

For `search_listings`, I will provide ChatGPT with the Tool 1 section from planning.md (the function purpose, parameters, return value, filtering rules, scoring requirements, and empty-result behavior) along with the existing `search_listings()` function signature from tools.py. I expect it to generate a function that uses `load_listings()`, filters listings by size and max_price, calculates keyword relevance scores from the description, removes zero-score results, sorts matches by relevance, and returns a list of listing dictionaries. Before accepting the code, I will test queries that return matches, queries with size filters, queries with price limits, and queries that return no results.

For `suggest_outfit`, I will provide ChatGPT with the Tool 2 section from planning.md, the wardrobe format, and the existing function signature. I expect it to generate code that handles both populated wardrobes and empty wardrobes, calls the Groq LLM with the correct prompt, and always returns a non-empty string. I will verify that it uses wardrobe pieces when available, provides general styling advice when the wardrobe is empty, and returns a readable error message if the API call fails.

For `create_fit_card`, I will provide ChatGPT with the Tool 3 section from planning.md and the function signature from tools.py. I expect it to generate code that validates the outfit input, builds an LLM prompt using the selected item details, and creates a short social-media caption. I will verify that the caption includes the item name, price, and resale platform and that missing inputs return a clear error instead of crashing.


**Milestone 4 — Planning loop and state management:**

For this milestone, I will use ChatGPT to implement the agent workflow after the individual tools are complete.

I will provide ChatGPT with the Planning Loop section from planning.md, the State Management section, the Architecture ASCII diagram, and the required tool signatures from tools.py. I expect it to generate the planning loop that creates the session dictionary, parses the user query into description/size/max_price, calls the tools in the correct order, saves each tool result into session state, and stops early when an error condition occurs.

Before using the generated code, I will compare it against the architecture diagram and verify each branch:
- If `search_listings()` returns `[]`, the loop should create an error message and stop before calling `suggest_outfit`.
- If `suggest_outfit()` fails, the loop should store the error and stop before calling `create_fit_card`.
- If all tools succeed, the loop should return a completed session containing the selected listing, outfit suggestion, and fit card.

I will then run integration tests using example user queries to confirm that the planning loop follows the exact sequence described in planning.md.





---

## A Complete Interaction (Step by Step)

Write out what a full user interaction looks like from start to finish — tool call by tool call. Use a specific example query.

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1:**
<!-- What does the agent do first? Which tool is called? With what input? -->
The planning loop gets the relevant search request and calls:

```python
search_listings(
    description="vintage graphic tee",
    size=None,
    max_price=30.0,
)
```

**Step 2:**
<!-- What happens next? What was returned from step 1? What tool is called now? -->

The dataset returns matching listing dictionaries sorted by relevance. For example:

```python
{
    "id": "lst_033",
    "title": "Vintage Band Tee — Faded Grey",
    "description": "Faded grey band-style tee with distressed graphic. Crew neck. Fits boxy. Well-loved but no holes or major damage.",
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

The planning loop creates a session dictionary using _new_session(query, wardrobe). After search_listings() returns matching listings, the planning loop saves the returned list in session["search_results"] and sets session["selected_item"] to the first result.

The next call is:

```python
suggest_outfit(
    new_item=session["selected_item"],
    wardrobe=session["wardrobe"],
)
```

**Step 3:**
<!-- Continue until the full interaction is complete -->

Step 3:
After suggest_outfit() returns a styling recommendation, the planning loop stores the returned string in session["outfit_suggestion"].
The planning loop then calls the create_fit_card() function from tools.py:
create_fit_card(
    outfit=session["outfit_suggestion"],
    new_item=session["selected_item"],
)
The function receives the outfit suggestion generated in the previous step and the selected listing saved earlier in the session. It passes those details to the LLM and returns a short social-media caption. The planning loop saves that returned string in session["fit_card"].


**Final output to user:**
<!-- What does the user actually see at the end? -->

After the planning loop finishes successfully, the user sees the top matching resale listing, the generated outfit suggestion, and the fit-card caption.

The listing details come from `session["selected_item"]`. The outfit suggestion comes from `session["outfit_suggestion"]`, which stores the string returned by `suggest_outfit()`. The fit-card caption comes from `session["fit_card"]`, which stores the string returned by `create_fit_card()`.

For this example, the final response may look like:

```text
Top match:
Vintage Band Tee — Faded Grey
$19 on depop
Size: L
Condition: fair

Outfit suggestion:
Pair the faded graphic tee with your baggy dark-wash jeans and chunky white
sneakers for a relaxed grunge-inspired look. Roll the sleeves once and add a
slight front tuck to give the oversized shape more structure.

Fit card:
found this faded vintage band tee on depop for $19 and it was made for baggy
jeans + chunky sneakers 🖤 rolled the sleeves and did a tiny front tuck for the
easiest grunge fit
```

The exact wording of the outfit suggestion and fit-card caption may vary because its generated by the LLM.



