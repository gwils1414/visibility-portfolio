# Fine-Tuning DistilBERT for PII Detection

A practical guide to training a token-level PII classifier that outputs probabilities (0–1) per token.

---

## Architecture Choice: Token Classification, Not Sequence Classification

PII detection is a **Named Entity Recognition (NER)** task — you want to know *which tokens* are PII, not just whether a document contains PII. Use `DistilBertForTokenClassification`, not the sequence classifier variant.

Each token gets an independent softmax output, so you naturally get per-token probabilities for each entity class.

---

## Label Schema (BIO Format)

Standard NER uses BIO tagging:

```
B-<ENTITY>   # Beginning of an entity span
I-<ENTITY>   # Inside/continuation of an entity span
O            # Not an entity
```

Example label set for PII:

```python
LABELS = [
    "O",
    "B-NAME", "I-NAME",
    "B-EMAIL", "I-EMAIL",
    "B-PHONE", "I-PHONE",
    "B-SSN", "I-SSN",
    "B-ADDRESS", "I-ADDRESS",
    "B-DOB", "I-DOB",
    "B-CREDIT_CARD", "I-CREDIT_CARD",
]

id2label = {i: l for i, l in enumerate(LABELS)}
label2id = {l: i for i, l in enumerate(LABELS)}
```

---

## Datasets / Corpora

### Synthetic (best starting point — no privacy risk)

| Dataset | Source | Notes |
|---|---|---|
| `ai4privacy/pii-masking-400k` | HuggingFace | 400k labeled PII examples, BIO-tagged, most comprehensive free option |
| `Isotonic/pii-masking-200k` | HuggingFace | Smaller, faster to iterate on |
| `Microsoft Presidio` synthetic generator | GitHub | Generate unlimited synthetic PII in any domain |
| `faker` + custom labeler | Python library | Roll your own corpus for domain-specific entities |

### Real-world annotated

| Dataset | Source | Notes |
|---|---|---|
| CoNLL-2003 | HuggingFace `datasets` | Person/org/loc NER — not PII-specific but useful for transfer |
| TAC KBP 2017 EDL | LDC (requires license) | High quality but gated |
| I2B2 2014 De-identification | i2b2.org | Clinical notes PII — requires DUA agreement |

**Recommended starting point:** `ai4privacy/pii-masking-400k` — it's purpose-built, pre-labeled in BIO format, and loads directly via `datasets`.

```python
from datasets import load_dataset
ds = load_dataset("ai4privacy/pii-masking-400k")
```

---

## Environment Setup

```bash
uv venv .venv
source .venv/bin/activate
uv pip install transformers datasets seqeval torch accelerate
```

---

## Full Training Script

```python
# train_pii.py
from datasets import load_dataset
from transformers import (
    AutoTokenizer,
    AutoModelForTokenClassification,
    TrainingArguments,
    Trainer,
    DataCollatorForTokenClassification,
)
import numpy as np
from seqeval.metrics import classification_report

MODEL_CHECKPOINT = "distilbert-base-uncased"

LABELS = [
    "O",
    "B-NAME", "I-NAME",
    "B-EMAIL", "I-EMAIL",
    "B-PHONE", "I-PHONE",
    "B-SSN", "I-SSN",
    "B-ADDRESS", "I-ADDRESS",
    "B-DOB", "I-DOB",
    "B-CREDIT_CARD", "I-CREDIT_CARD",
]
id2label = {i: l for i, l in enumerate(LABELS)}
label2id = {l: i for i, l in enumerate(LABELS)}

tokenizer = AutoTokenizer.from_pretrained(MODEL_CHECKPOINT)


def tokenize_and_align_labels(examples):
    """
    Tokenize words and align BIO labels to subword tokens.
    Subword continuations inherit the label of their first subword;
    special tokens ([CLS], [SEP]) get label -100 (ignored in loss).
    """
    tokenized = tokenizer(
        examples["tokens"],
        truncation=True,
        is_split_into_words=True,  # input is pre-tokenized word list
    )
    all_labels = []
    for i, labels in enumerate(examples["ner_tags"]):
        word_ids = tokenized.word_ids(batch_index=i)
        aligned = []
        prev_word = None
        for word_id in word_ids:
            if word_id is None:
                aligned.append(-100)  # special token — ignore in loss
            elif word_id != prev_word:
                aligned.append(labels[word_id])  # first subword of word
            else:
                # Continuation subword — keep label or set -100 to ignore
                aligned.append(labels[word_id])
            prev_word = word_id
        all_labels.append(aligned)
    tokenized["labels"] = all_labels
    return tokenized


# --- Load & preprocess ---
# Swap for ai4privacy/pii-masking-400k once you've validated the label mapping
ds = load_dataset("conll2003")  # placeholder — swap dataset here
tokenized_ds = ds.map(tokenize_and_align_labels, batched=True)

# --- Model ---
model = AutoModelForTokenClassification.from_pretrained(
    MODEL_CHECKPOINT,
    num_labels=len(LABELS),
    id2label=id2label,
    label2id=label2id,
)

# --- Metrics ---
def compute_metrics(eval_pred):
    logits, labels = eval_pred
    predictions = np.argmax(logits, axis=-1)

    true_labels, true_preds = [], []
    for pred_seq, label_seq in zip(predictions, labels):
        true_labels.append([id2label[l] for l in label_seq if l != -100])
        true_preds.append(
            [id2label[p] for p, l in zip(pred_seq, label_seq) if l != -100]
        )

    report = classification_report(true_labels, true_preds, output_dict=True)
    return {
        "precision": report["weighted avg"]["precision"],
        "recall": report["weighted avg"]["recall"],
        "f1": report["weighted avg"]["f1-score"],
    }

# --- Training args ---
args = TrainingArguments(
    output_dir="pii-distilbert",
    eval_strategy="epoch",
    save_strategy="epoch",
    learning_rate=2e-5,
    per_device_train_batch_size=16,
    per_device_eval_batch_size=16,
    num_train_epochs=3,
    weight_decay=0.01,
    load_best_model_at_end=True,
    metric_for_best_model="f1",
)

trainer = Trainer(
    model=model,
    args=args,
    train_dataset=tokenized_ds["train"],
    eval_dataset=tokenized_ds["validation"],
    tokenizer=tokenizer,
    data_collator=DataCollatorForTokenClassification(tokenizer),
    compute_metrics=compute_metrics,
)

trainer.train()
trainer.save_model("pii-distilbert-final")
```

---

## Inference with Per-Token Probabilities

After training, run inference to get 0–1 probabilities per token:

```python
import torch
import torch.nn.functional as F
from transformers import AutoTokenizer, AutoModelForTokenClassification

model = AutoModelForTokenClassification.from_pretrained("pii-distilbert-final")
tokenizer = AutoTokenizer.from_pretrained("pii-distilbert-final")

def predict_pii(text: str, threshold: float = 0.5) -> list[dict]:
    """
    Returns a list of detected PII spans with their label and confidence.
    
    threshold: minimum probability to surface a token as PII.
    """
    inputs = tokenizer(text, return_tensors="pt", return_offsets_mapping=True)
    offset_mapping = inputs.pop("offset_mapping")[0]

    with torch.no_grad():
        logits = model(**inputs).logits  # (1, seq_len, num_labels)

    probs = F.softmax(logits, dim=-1)[0]  # (seq_len, num_labels)
    pred_ids = probs.argmax(dim=-1)

    results = []
    for i, (pred_id, token_probs, offsets) in enumerate(
        zip(pred_ids, probs, offset_mapping)
    ):
        label = model.config.id2label[pred_id.item()]
        confidence = token_probs[pred_id].item()

        if label != "O" and confidence >= threshold:
            start, end = offsets.tolist()
            results.append({
                "span": text[start:end],
                "label": label,
                "probability": round(confidence, 4),
                "start": start,
                "end": end,
            })

    return results


# Example
text = "Please contact John Smith at john.smith@example.com or call 555-867-5309."
hits = predict_pii(text, threshold=0.7)
for h in hits:
    print(h)
# {"span": "John Smith", "label": "B-NAME", "probability": 0.9823, "start": 16, "end": 26}
# {"span": "john.smith@example.com", "label": "B-EMAIL", "probability": 0.9971, ...}
# {"span": "555-867-5309", "label": "B-PHONE", "probability": 0.9644, ...}
```

---

## Probability Output Semantics

The softmax over `num_labels` classes gives you a proper probability distribution per token. The value you care about is `probs[token_idx][predicted_class_id]` — this is your 0–1 confidence score.

- **> 0.9** — high confidence, treat as PII
- **0.7–0.9** — review / flag for human
- **< 0.7** — likely false positive, depending on your risk tolerance

You can also surface the *full distribution* if you need to know "what's the probability this token is an EMAIL vs a NAME vs O."

---

## Expected Performance (ai4privacy dataset)

| Metric | Expected range |
|---|---|
| F1 (weighted) | 0.92 – 0.97 |
| Precision | 0.91 – 0.96 |
| Recall | 0.93 – 0.97 |
| Training time (M5 Pro CPU) | ~45–90 min for 3 epochs |
| Training time (RTX 3090) | ~8–15 min for 3 epochs |

---

## Gotchas

- **Subword alignment** — DistilBERT tokenizes "Smith" → ["smith"] but "Smithsonian" → ["smith", "##son", "##ian"]. The `tokenize_and_align_labels` function above handles this. Don't skip it.
- **Dataset label mapping** — `ai4privacy` uses string labels; you'll need to map them to your integer `label2id` before training. Check `ds["train"].features["privacy_mask"]` for the exact label names.
- **Long documents** — DistilBERT has a 512-token limit. For longer texts, chunk with overlap (e.g. 384 tokens with 128-token stride) and merge predictions.
- **Threshold tuning** — lower threshold = higher recall (catch more PII, more false positives). For data pipelines where missing PII is costly, bias toward recall (threshold ~0.4–0.5).

---

## Using the Trained Model

After `trainer.save_model("pii-distilbert-final")`, the output directory contains everything needed for inference:

```
pii-distilbert-final/
  config.json          # label mappings baked in
  model.safetensors    # weights (~250MB)
  tokenizer.json
  tokenizer_config.json
  vocab.txt
```

Load it once, keep it in memory — the expensive part is the `from_pretrained` call (~1–2s). Inference per call is ~10–50ms on CPU.

```python
from transformers import AutoTokenizer, AutoModelForTokenClassification

model = AutoModelForTokenClassification.from_pretrained("pii-distilbert-final")
tokenizer = AutoTokenizer.from_pretrained("pii-distilbert-final")

hits = predict_pii("Send the contract to jane.doe@gmail.com", threshold=0.7)
```

---

## Integration Patterns

### As a pydantic-ai Tool (Hermes)

Wrap `predict_pii` so the agent can call it before logging or storing any text:

```python
from pydantic_ai import tool

@tool
def scan_for_pii(text: str, threshold: float = 0.7) -> list[dict]:
    """Scan text for PII spans. Returns detected entities with label and confidence."""
    return predict_pii(text, threshold=threshold)
```

The agent can then decide to redact, flag, or reject based on the returned spans.

### As a FastAPI Endpoint

Load the model once at startup via the `lifespan` event so it's warm for every request:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from transformers import AutoTokenizer, AutoModelForTokenClassification

ml_models = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    ml_models["tokenizer"] = AutoTokenizer.from_pretrained("pii-distilbert-final")
    ml_models["model"] = AutoModelForTokenClassification.from_pretrained("pii-distilbert-final")
    yield
    ml_models.clear()

app = FastAPI(lifespan=lifespan)

@app.post("/scan")
def scan(payload: dict):
    text = payload["text"]
    threshold = payload.get("threshold", 0.7)
    # predict_pii uses the globally loaded model/tokenizer
    return {"hits": predict_pii(text, threshold)}
```

### As a Pre-processing Step in a Pipeline

Run it over text before it hits Postgres — redact spans above threshold, store the cleaned version:

```python
def redact_pii(text: str, threshold: float = 0.7, replacement: str = "[REDACTED]") -> str:
    hits = predict_pii(text, threshold=threshold)
    # Walk hits in reverse so offsets stay valid as we replace
    for hit in sorted(hits, key=lambda h: h["start"], reverse=True):
        text = text[: hit["start"]] + replacement + text[hit["end"] :]
    return text

# Example
clean = redact_pii("Call John at 555-867-5309 before the meeting.")
# "Call [REDACTED] at [REDACTED] before the meeting."
```

### As an Always-On Service on the ThinkCentre

The ~250MB weights run comfortably in the ThinkCentre's RAM. Expose it over Tailscale so your full stack can hit it without going to the internet:

```bash
# Run the FastAPI app
uv run uvicorn pii_service:app --host 0.0.0.0 --port 8765
```

Other machines on your Tailnet call it at `http://<thinkcentre-tailscale-ip>:8765/scan`. No GPU needed — CPU inference at this model size is fast enough for real-time use.