# Pod Classifier — Companion Document
**AI201 Lab 3 · Few-Shot Podcast Episode Classifier**

---

## Overall Plan — Step by Step

| # | Milestone | Status |
|---|---|---|
| 1 | Annotate all 20 training episodes in `data/my_labels.json` | ✅ Done |
| 2 | Draft `specs/classifier-spec.md` before coding | ✅ Done |
| 2 | Write `build_few_shot_prompt()` in `classifier.py` | ⬜ TODO |
| 2 | Write `classify_episode()` in `classifier.py` | ⬜ TODO |
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
Spec finalized in `specs/classifier-spec.md`. Key decisions locked in:
1. System message defines the 4 labels and instructs: *return only label and reasoning*
2. Each training example is a three-line block — `Title:`, `Description:`, `Label:` — separated by `---`
3. New episode is presented identically with `Label: ?` at the end
4. Requested output format: exactly two lines — `Label: <label>` / `Reasoning: <sentence>`
5. If `labeled_examples` is empty, insert an explicit note before the examples block

Confirmed with a live Groq test call — the model returned:
```
Label: narrative
Reasoning: This episode tells a story assembled from external information...
```

### `classify_episode()` — TODO (Milestone 2)
Spec finalized in `specs/classifier-spec.md`. Key decisions locked in:
1. Call `build_few_shot_prompt(labeled_examples, description)`
2. Send via `_client.chat.completions.create(model=LLM_MODEL, max_tokens=200)`
3. Parse: split on `\n`, scan for `Label:` and `Reasoning:` prefixes using `split(':', 1)[1].strip()`
4. Fallback: if no `Label:` line, scan first non-empty line for any VALID_LABELS word
5. Validate: exact match against `VALID_LABELS` only — no fuzzy matching; invalid → `"unknown"`
6. Wrap entire body in `try/except Exception` — return `{"label": "unknown", "reasoning": "Classification failed: ..."}` on any error

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
- [x] `specs/classifier-spec.md` fully complete — all blanks filled, implementation notes populated with real LLM response data

### Yet to build (Milestone 2)
- [ ] `build_few_shot_prompt()` — prompt template with training examples
- [ ] `classify_episode()` — API call + response parsing + label validation

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

**Next: `build_few_shot_prompt()` + `classify_episode()` in `classifier.py`**

The spec is done and a live test call confirmed the model returns the expected two-line format. Implementation is now straightforward plumbing — the design decisions are already locked in. Priority order:

1. `build_few_shot_prompt()` — assemble the prompt string from the spec's template
2. `classify_episode()` — wire up the API call, parse with `split(':', 1)`, validate, wrap in try/except
3. Smoke-test by running the Classify tab in the Gradio UI on one of the four built-in examples
4. Then move to `specs/evaluation-spec.md` + Milestone 3 accuracy functions
