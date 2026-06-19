import json
import os
from groq import Groq
from config import GROQ_API_KEY, LLM_MODEL, VALID_LABELS, DATA_PATH, TRAIN_FILE, LABELS_FILE

_client = Groq(api_key=GROQ_API_KEY)


def load_labeled_examples() -> list[dict]:
    """
    Load the training episodes and merge them with the student's labels.

    Returns a list of dicts, each with:
      - "id"          : episode ID
      - "title"       : episode title
      - "podcast"     : podcast name
      - "description" : episode description
      - "label"       : the label from my_labels.json (may be None if not yet annotated)

    Only returns episodes where the label is a valid, non-null string.
    Episodes with null labels are silently skipped.
    """
    train_path = os.path.join(DATA_PATH, TRAIN_FILE)
    labels_path = os.path.join(DATA_PATH, LABELS_FILE)

    with open(train_path, encoding="utf-8") as f:
        episodes = {ep["id"]: ep for ep in json.load(f)}

    with open(labels_path, encoding="utf-8") as f:
        labels = {entry["id"]: entry["label"] for entry in json.load(f)}

    labeled = []
    for ep_id, ep in episodes.items():
        label = labels.get(ep_id)
        if label in VALID_LABELS:
            labeled.append({**ep, "label": label})

    return labeled


def build_few_shot_prompt(labeled_examples: list[dict], description: str) -> str:
    """
    Build a few-shot classification prompt using the student's labeled training examples.
    """
    task_instruction = (
        "You are classifying podcast episodes by their format. "
        "Classify the episode into exactly one of these four labels:\n\n"
        "- interview: a conversation between a host and one or more guests\n"
        "- solo: a single host speaking from memory, experience, or opinion — "
        "no guests, no assembled external sources\n"
        "- panel: multiple guests with roughly equal speaking time, often debating "
        "or discussing a topic together\n"
        "- narrative: a story assembled from external sources — interviews, archival "
        "audio, reporting — with a clear narrative arc\n\n"
        "Return only the label and your reasoning. Do not explain the taxonomy."
    )

    if labeled_examples:
        examples_block = "Here are labeled examples:\n\n---\n\n"
        for ex in labeled_examples:
            title = ex.get("title", "(no title)")
            desc = ex.get("description", "(no description)")
            label = ex["label"]
            examples_block += f"Title: {title}\nDescription: {desc}\nLabel: {label}\n\n---\n\n"
    else:
        examples_block = (
            "No labeled examples are available. "
            "Use your general knowledge of podcast formats.\n\n---\n\n"
        )

    new_episode = (
        f"Now classify this episode:\n\n"
        f"Title: (unknown)\n"
        f"Description: {description}\n"
        f"Label: ?\n\n"
        f"Respond with exactly two lines:\n"
        f"Label: <one of: interview, solo, panel, narrative>\n"
        f"Reasoning: <one sentence explaining why>"
    )

    return f"{task_instruction}\n\n{examples_block}{new_episode}"


def classify_episode(description: str, labeled_examples: list[dict]) -> dict:
    """
    Classify a single podcast episode description using the few-shot LLM classifier.
    """
    try:
        prompt = build_few_shot_prompt(labeled_examples, description)

        response = _client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
        )
        raw = response.choices[0].message.content

        label_raw = None
        reasoning = raw.strip()

        for line in raw.splitlines():
            if line.lower().startswith("label:"):
                label_raw = line.split(":", 1)[1].strip().lower()
            elif line.lower().startswith("reasoning:"):
                reasoning = line.split(":", 1)[1].strip()

        # Fallback: scan first non-empty line for a valid label word
        if label_raw not in VALID_LABELS:
            for line in raw.splitlines():
                if line.strip():
                    for word in line.lower().split():
                        if word in VALID_LABELS:
                            label_raw = word
                            break
                    break

        label = label_raw if label_raw in VALID_LABELS else "unknown"
        return {"label": label, "reasoning": reasoning}

    except Exception as e:
        return {"label": "unknown", "reasoning": f"Classification failed: {e}"}
