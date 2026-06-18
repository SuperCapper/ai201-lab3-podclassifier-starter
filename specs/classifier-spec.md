# Classifier Spec — Pod Classifier

Complete this spec **before** writing any code for Milestone 2.

Use Plan or Ask mode to think through each blank field. When you're done,
your answers here become the blueprint for `build_few_shot_prompt()` and
`classify_episode()` in `classifier.py`.

---

## build_few_shot_prompt(labeled_examples, description)

### What it does
Constructs a prompt string for the LLM that includes the task instructions,
all labeled training examples, and the new episode description to classify.

### Inputs

| Parameter | Type | Description |
|---|---|---|
| `labeled_examples` | `list[dict]` | Each dict has `"title"`, `"description"`, `"label"` (and others). These are the examples you labeled in Milestone 1. |
| `description` | `str` | The episode description to classify. |

### Output

| Return value | Type | Description |
|---|---|---|
| prompt | `str` | A complete prompt string ready to send to the LLM. |

---

### Spec fields — fill these in before writing code

**Task instruction (what should the LLM know about the task?):**

```
You are classifying podcast episodes by their format. Classify the episode
into exactly one of these four labels:

- interview: a conversation between a host and one or more guests
- solo: a single host speaking from memory, experience, or opinion — no guests,
  no assembled external sources
- panel: multiple guests with roughly equal speaking time, often debating or
  discussing a topic together
- narrative: a story assembled from external sources — interviews, archival
  audio, reporting — with a clear narrative arc

Return only the label and your reasoning. Do not explain the taxonomy.
```

---

**How should labeled examples be formatted in the prompt?**

```
Each example should include the episode title, a brief excerpt or the full
description, and the correct label. Separate examples with a blank line or
a delimiter like "---". Include all fields that help the model see why the
label was applied — title and description are both useful; other fields
(like episode ID) are not needed.
```

---

**Example block sketch (write one concrete example):**

```
Title: {title}
Description: {description}
Label: {label}
```

---

**How should the new episode (to be classified) be presented?**

```
Present it in the same format as the labeled examples, but omit the Label
line and replace it with an instruction to classify. For example:

Title: {title}
Description: {description}
Label: ?

Then add a line like: "Classify the episode above. Return your answer in
the format below:" followed by the output format you chose.
```

---

**What output format should you request from the LLM?**

```
Use a two-line labeled format:

  Label: <label>
  Reasoning: <one sentence>

Ask the model to respond with exactly those two lines and nothing else.

Why not JSON? LLMs frequently wrap JSON in markdown fences (```json ... ```)
or add a prose sentence before the block, making json.loads() fail without
extra stripping logic. The labeled-line format is easier to parse: scan lines
for the "Label:" prefix, strip and lowercase, done. If the model ignores the
format and writes prose, the parser can still search for a VALID_LABELS word
on the first non-empty line as a fallback.

Why not a single bare label? A reasoning string is required by classify_episode()'s
return type and shown in the Gradio UI. A bare label gives us nothing to display.
```

---

**Edge cases to handle in the prompt:**

```
1. labeled_examples is empty
   Still build and send the prompt — the LLM has general knowledge of podcast
   formats and can still classify. Insert a note before the examples block:
   "No labeled examples are available. Use your general knowledge of podcast
   formats." This makes the absence explicit rather than silently sending a
   malformed prompt.

2. Description is very short (e.g., one sentence)
   No special handling needed. Short descriptions are valid input. The model
   may be less confident, but that shows up in the reasoning, not in a crash.

3. Description contains quotation marks or special characters
   Python f-strings handle this fine. No escaping needed for plain text prompts.

4. A labeled example has a missing title or description field
   Use .get() with a fallback: ep.get("title", "(no title)"). This prevents
   a KeyError from breaking prompt construction for all 20 examples.
```

---

## classify_episode(description, labeled_examples)

### What it does
Classifies a single podcast episode description using the few-shot LLM classifier.
Returns a dict with a label and reasoning.

### Inputs

| Parameter | Type | Description |
|---|---|---|
| `description` | `str` | The episode description to classify. |
| `labeled_examples` | `list[dict]` | Labeled training examples from `load_labeled_examples()`. |

### Output

| Return value | Type | Description |
|---|---|---|
| result | `dict` | Must have keys `"label"` and `"reasoning"`. `"label"` must be one of `VALID_LABELS` or `"unknown"`. |

---

### Spec fields — fill these in before writing code

**Step 1 — Build the prompt:**

```
Call build_few_shot_prompt(labeled_examples, description) and store the
returned string in a variable (e.g., prompt). Pass through both arguments
exactly as received — no modification needed before calling.
```

---

**Step 2 — Send to the LLM:**

```
Call _client.chat.completions.create() with:
  - model: the model name from config (LLM_MODEL)
  - messages: a list with one dict — {"role": "user", "content": prompt}
    (system-design.md shows an optional system message too — either shape works)
  - max_tokens: a reasonable limit (e.g., 200–300) to keep responses concise

Extract the response text from:
  response.choices[0].message.content
```

---

**Step 3 — Parse the response:**

```
The expected format is:
  Label: interview
  Reasoning: The host draws out the guest's expertise via Q&A.

Parsing steps:
  1. Split the response text on newlines.
  2. Scan each line for one that starts with "Label:" (case-insensitive).
     Extract everything after the colon, strip whitespace, lowercase → label_raw.
  3. Scan each line for one that starts with "Reasoning:" (case-insensitive).
     Extract everything after the colon, strip whitespace → reasoning_raw.
  4. If no "Label:" line is found, fallback: scan the first non-empty line for
     any word that matches a VALID_LABELS entry (after lowercasing).
  5. If no "Reasoning:" line is found, use the full response text as reasoning
     so the UI always has something to display.

This makes the parser tolerant of minor format deviations without hiding
parsing failures — the fallback behavior is visible in the reasoning field.
```

---

**Step 4 — Validate the label:**

```
After parsing, check:
  if label_raw not in VALID_LABELS:
      label = "unknown"
  else:
      label = label_raw

"unknown" is the contract defined in classify_episode()'s return spec and is
handled by the UI's LABEL_COLORS dict (mapped to slate gray). Setting it here
keeps all downstream code clean — no None checks, no KeyErrors in the UI.

Do NOT try to fuzzy-match (e.g., "interviews" → "interview"). If the model
can't return a valid label verbatim, "unknown" is the honest answer and helps
identify prompt quality issues.
```

---

**Step 5 — Handle errors gracefully:**

```
Wrap the entire function body in try/except Exception as e.

Things that can fail:
  - Network error or Groq API timeout → raises an exception before we get a response
  - Rate-limit error (429) → raises an exception
  - response.choices is empty → IndexError on choices[0]
  - Response text is completely unparseable → label stays "unknown" (handled in Step 4)

On any exception:
  return {
      "label": "unknown",
      "reasoning": f"Classification failed: {str(e)}",
  }

Why return rather than re-raise? run_evaluation() iterates 20 episodes in a loop.
One failed API call must not abort the remaining 19. The "unknown" label is counted
as incorrect in accuracy scoring, which is the right behavior — a failure is not a
correct prediction.
```

---

### Return value structure

```python
{
    "label": str,      # one of VALID_LABELS, or "unknown" if invalid/error
    "reasoning": str,  # brief explanation from the LLM
}
```

---

## Notes on label quality

The classifier is only as good as your labels. If your training examples have
inconsistent or ambiguous labels, the LLM will learn the wrong pattern.

Before implementing the classifier, re-read `data/taxonomy.md` and double-check
any labels you're unsure about. Annotation quality is part of the lab.

---

## Implementation Notes

*Fill this in after implementing and testing both functions.*

**Test: what does the raw LLM response look like for one episode?**

```
Episode tested: [title]
Raw response text: [paste it here]
```

**How did you parse the label out of the response?**

```
[describe the string operations — strip, split, lower, etc.]
```

**Did any episodes return `"unknown"`? If so, why?**

```
[yes / no — if yes, what did the raw response look like?]
```

**One thing about the output format that surprised you:**

```
[your answer here]
```
