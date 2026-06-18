# Pod Classifier — Companion Document
**AI201 Lab 3 · Few-Shot Podcast Episode Classifier**

---

## Overall Plan — Step by Step

| # | Milestone | Status |
|---|---|---|
| 1 | Annotate all 20 training episodes in `data/my_labels.json` | ✅ Done |
| 2 | Write `build_few_shot_prompt()` in `classifier.py` | ⬜ TODO |
| 2 | Write `classify_episode()` in `classifier.py` | ⬜ TODO |
| 2 | Draft `specs/classifier-spec.md` before coding | ⬜ TODO |
| 3 | Write `compute_accuracy()` in `evaluate.py` | ⬜ TODO |
| 3 | Write `compute_per_class_accuracy()` in `evaluate.py` | ⬜ TODO |
| 3 | Draft `specs/evaluation-spec.md` before coding | ⬜ TODO |
| — | Run full evaluation; review per-class accuracy report | ⬜ TODO |
| — | Iterate on labels or prompt if accuracy is low | ⬜ TODO |

---

## Data: What We Have and What We Need

### Files on disk

| File | Contents | Role |
|---|---|---|
| `data/train_episodes.json` | 20 episodes — `id`, `title`, `podcast`, `description` | Source text for training examples |
| `data/my_labels.json` | 20 entries — `id`, `label` | Human-assigned ground truth for the few-shot prompt |
| `data/test_episodes.json` | ~20 held-out episodes with ground-truth labels | Evaluation set (never used as training signal) |
| `data/taxonomy.md` | Definitions + edge-case rules for the 4 labels | Reference for labeling and prompt design |

### Training label distribution (Milestone 1 final)

| Label | Count | Episodes |
|---|---|---|
| `interview` | 5 | t001, t002, t003, t004, t005 |
| `solo` | 6 | t006, t007, t008, t009, t010, t020 |
| `panel` | 5 | t011, t012, t013, t014, t015 |
| `narrative` | 4 | t016, t017, t018, t019 |
| **Total** | **20** | |

### API call structure

One Groq `chat.completions.create()` call per episode at inference time:

```python
response = _client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[
        {"role": "system", "content": "<system instructions>"},
        {"role": "user",   "content": "<few-shot prompt + new description>"},
    ],
)
text = response.choices[0].message.content
```

**Fields used from the response:**
- `response.choices[0].message.content` — raw text to parse for label + reasoning

**No streaming, no tool calls, no multi-turn.** One prompt in, one response out.

---

## Transforms and Logic

### `load_labeled_examples()` — already implemented
1. Read `train_episodes.json` → dict keyed by `id`
2. Read `my_labels.json` → dict keyed by `id`
3. Merge: for each episode, attach its label
4. Filter: skip any entry whose label is not in `VALID_LABELS`
5. Return list of dicts with keys: `id`, `title`, `podcast`, `description`, `label`

### `build_few_shot_prompt()` — TODO (Milestone 2)
1. Write a **system message** describing the task and the 4 labels
2. For each labeled training example, format a block like:
   ```
   Description: <episode description>
   Label: <label>
   ```
3. Append the **new unseen description** and ask the model to respond with:
   - A label (exactly one of: interview, solo, panel, narrative)
   - A brief reasoning sentence
4. Specify output format precisely so `classify_episode()` can parse it reliably
   - Options: `Label: X\nReasoning: Y` or JSON `{"label": "...", "reasoning": "..."}`

### `classify_episode()` — TODO (Milestone 2)
1. Call `build_few_shot_prompt(labeled_examples, description)`
2. Send to Groq API
3. Parse the text response:
   - Extract label string and reasoning
   - Strip whitespace, lowercase, validate against `VALID_LABELS`
4. If label not in `VALID_LABELS` → set `label = "unknown"`
5. Return `{"label": "...", "reasoning": "..."}`
6. Wrap in try/except — a failed API call or unparseable response must not crash evaluation

### `compute_accuracy()` — TODO (Milestone 3)
```
accuracy = number of (predicted == ground_truth) / total predictions
```
- Iterate `zip(predictions, ground_truth)`
- Count matches, divide by `len(predictions)`
- Return float in [0.0, 1.0]

### `compute_per_class_accuracy()` — TODO (Milestone 3)
For each label in `VALID_LABELS`:
1. Filter to episodes where `ground_truth == label`
2. Count how many were predicted correctly
3. Return `{"correct": int, "total": int, "accuracy": float}`

Edge case: if a label has 0 test examples, return `accuracy = 0.0` (not division-by-zero).

---

## Visualization — How Results Are Displayed

### Classify tab (`app.py`)
- Color-coded badge (indigo/violet/purple/fuchsia by label)
- Short label description below the badge
- Reasoning box with purple left border
- 4 quick-load example buttons

### Evaluate tab (`app.py` + `evaluate.py:format_evaluation_report`)
- **Overall accuracy:** shown as `X.X% (n/total)`
- **Per-class accuracy:** ASCII progress bar with `█░` fill
  ```
  interview    ████████░░  80%  (4/5)
  solo         ██████████  100% (5/5)
  panel        ███████░░░  70%  (3/5+ ...)
  narrative    ████████░░  80%  (4/5)
  ```
- **Misclassified list:** `[ground_truth → predicted] Episode Title`
- Rendered as Markdown inside the Gradio UI

### Label Guide tab (`app.py`)
- Static reference — taxonomy definitions + edge-case table
- Always available, no API calls needed

---

## What's Working / What's Left

### Working now
- [x] All 20 training labels assigned and validated (`20 labeled examples loaded`)
- [x] `load_labeled_examples()` merges and filters correctly
- [x] `run_evaluation()` loop iterates test set and calls `classify_episode()`
- [x] `format_evaluation_report()` formats per-class bars and misclassified list
- [x] Gradio UI renders both tabs and example buttons
- [x] Config loads API key from `.env`

### Yet to build (Milestone 2)
- [ ] `build_few_shot_prompt()` — prompt template with training examples
- [ ] `classify_episode()` — API call + response parsing + label validation
- [ ] `specs/classifier-spec.md` — write the spec before coding

### Yet to build (Milestone 3)
- [ ] `compute_accuracy()` — overall accuracy float
- [ ] `compute_per_class_accuracy()` — per-label correct/total/accuracy dict
- [ ] `specs/evaluation-spec.md` — write the spec before coding

### Known issues / watch-outs
- Pydantic V1 warning from Groq client under Python 3.14 — cosmetic, does not break anything
- `classify_episode()` currently returns `label: None` — evaluation will show 0% until Milestone 2 is done
- `compute_accuracy()` returns 0.0 stub — report will show 0% until Milestone 3 is done

---

## Building Next and Why

**Next: `specs/classifier-spec.md` + `build_few_shot_prompt()`**

The prompt is the entire training signal for the classifier. Getting the format right matters more than any other single decision:
- Too little context → the LLM ignores the examples
- Ambiguous output format → parsing fails silently and returns `"unknown"`
- Too many tokens → slower, more expensive, and the model may lose track of the task

The spec should nail down:
1. Exact system message wording
2. Example block format (how each training example is presented)
3. Output format the model must follow
4. How `classify_episode()` will parse that output

After the prompt is solid, `classify_episode()` is mostly plumbing. After that, the two evaluation functions are simple arithmetic.
