# Hermes Local Model Fine-Tuning Pipeline — Plan

## Overview

Take the feedback you're already capturing (from Plan 1) and use it to actually update model weights — not just instructions. The result is a personalized model that has *learned* your preferences at the weight level, not just been told about them in a prompt.

```
feedback DB → format as preference pairs → DPO training → LoRA adapter → load in Ollama
```

This is a **monthly batch process**, not real-time. Different timescale than the daily instruction reflection.

---

## Why DPO (Direct Preference Optimization)

The feedback you're collecting fits DPO naturally:

| Feedback type | What you have | DPO format |
|---|---|---|
| 👍 Good | input + good response | not directly useful (no rejected pair) |
| 👎 Bad with reason | input + bad response | needs a "chosen" alternative to be useful |
| ✏️ Correction | input + bad response + corrected response | **perfect DPO pair** |

So corrections become your training signal. The good/bad alone won't fine-tune anything — you need pairs of (chosen, rejected) for every input.

Unsloth recommends a learning rate of 5e-6 for DPO/RL training (vs 2e-4 for standard LoRA), and 1-3 epochs to avoid overfitting.

---

## Hardware Requirements

This is the most honest part of the plan — you need to know what you're getting into.

QLoRA fine-tuning of a 7B model needs ~8GB VRAM. A consumer GPU like an RTX 4070 Ti works for 7B-8B models.

On Apple Silicon via Unsloth's MPS backend or llama.cpp with MLX, expect 3-5x slower training than NVIDIA. A 7B fine-tune that takes 3 hours on RTX 4090 takes 10-15 hours on an M3 Max.

| Model size | Method | VRAM needed | M3/M4 Mac viable? |
|---|---|---|---|
| 3B | LoRA | 8GB | ✅ Yes, ~3-5h |
| 7B | QLoRA | 8GB | ✅ Yes, ~10-15h |
| 13B | QLoRA | 12GB | ⚠️ Slow, ~24h+ |
| 70B | QLoRA | 40GB | ❌ Cloud needed |

For Hermes specifically — start with a 7B local model (qwen3.5:7b or similar) since `gpt-oss:120b-cloud` and `qwen3.5:397b-cloud` are too large to fine-tune yourself.

---

## Data Pipeline

### Step 1 — Extract feedback pairs

```python
def extract_training_pairs() -> list[dict]:
    pairs = db.query("""
        SELECT 
            user_input as prompt,
            correction as chosen,
            response   as rejected
        FROM agent_feedback
        WHERE correction IS NOT NULL
          AND used_in_training = false
    """)
    
    return [
        {
            "prompt":   p.prompt,
            "chosen":   p.chosen,
            "rejected": p.rejected
        }
        for p in pairs
    ]
```

### Step 2 — Quality filter

Not every correction is good training data. Filter out:
- Pairs where chosen and rejected are too similar (low signal)
- Pairs where chosen is shorter than 20 chars (probably not a real correction)
- Pairs older than 6 months (preferences drift)

### Step 3 — Minimum threshold check

```python
if len(pairs) < 100:
    print(f"Only {len(pairs)} pairs available — need 100+ minimum.")
    return
```

DPO needs meaningful sample size. Below ~100 pairs you're more likely to harm the model than improve it.

---

## Training Pipeline (Offline)

### Unsloth + TRL setup

```python
from unsloth import FastLanguageModel
from trl import DPOTrainer, DPOConfig
from datasets import Dataset

# load base model with QLoRA config
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="unsloth/qwen3.5-7b-instruct",
    max_seq_length=2048,
    load_in_4bit=True,
)

# add LoRA adapters
model = FastLanguageModel.get_peft_model(
    model,
    r=16,                            # LoRA rank
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
    lora_alpha=16,
    use_gradient_checkpointing="unsloth",
)

# build dataset
training_pairs = extract_training_pairs()
dataset = Dataset.from_list(training_pairs)

# DPO training config
training_args = DPOConfig(
    output_dir="./hermes-adapter-v1",
    num_train_epochs=2,
    learning_rate=5e-6,              # lower for DPO
    per_device_train_batch_size=2,
    gradient_accumulation_steps=4,
    warmup_ratio=0.1,
    logging_steps=10,
    save_strategy="epoch",
)

trainer = DPOTrainer(
    model=model,
    args=training_args,
    train_dataset=dataset,
    tokenizer=tokenizer,
    beta=0.1,                        # how aggressive the preference update is
)

trainer.train()
trainer.save_model()
```

### Why these specific settings
- **r=16** — small adapter, ~50MB final size
- **beta=0.1** — conservative preference strength
- **2 epochs** — enough to learn signal without memorizing
- **5e-6 learning rate** — DPO standard, prevents catastrophic forgetting

---

## Export to Ollama

Unsloth saves the fine-tuned model as a small LoRA adapter (~100MB). For local inference in Ollama, use llama.cpp to convert to GGUF format.

```bash
# 1. merge adapter with base model
python -c "
from unsloth import FastLanguageModel
model, tokenizer = FastLanguageModel.from_pretrained('./hermes-adapter-v1')
model.save_pretrained_merged('./hermes-merged', tokenizer)
"

# 2. convert to GGUF
python llama.cpp/convert.py ./hermes-merged --outfile hermes-v1.gguf

# 3. create Ollama Modelfile
cat > Modelfile << EOF
FROM ./hermes-v1.gguf
PARAMETER temperature 0.5
SYSTEM "$(cat hermes_system_prompt.md)"
EOF

# 4. register with Ollama
ollama create hermes-personal-v1 -f Modelfile

# 5. test
ollama run hermes-personal-v1 "test prompt"
```

---

## Versioning & Rollback

```sql
CREATE TABLE model_versions (
    id              INTEGER PRIMARY KEY,
    version         TEXT,           -- "hermes-personal-v3"
    base_model      TEXT,           -- "qwen3.5:7b"
    training_pairs  INTEGER,        -- how many pairs used
    feedback_ids    INTEGER[],      -- which feedback drove this version
    eval_score      FLOAT,          -- score from eval suite post-training
    created_at      TIMESTAMP,
    active          BOOLEAN,
    notes           TEXT
);
```

Each fine-tune is a new version. Never overwrite — you must be able to roll back.

---

## Evaluation Gate

**Critical** — never deploy a new fine-tuned model without evaluating it first.

```python
async def evaluate_new_version(version: str) -> dict:
    # run your standing eval suite against the new model
    base_score = await run_evals(model="qwen3.5:7b")
    new_score  = await run_evals(model=version)
    
    return {
        "version": version,
        "base_score": base_score,
        "new_score": new_score,
        "delta": new_score - base_score,
        "regression_detected": new_score < base_score - 5,  # 5pt threshold
    }
```

If the new model scores lower than the base on standing evals, **do not promote** — investigate first. Catastrophic forgetting is a real risk with DPO.

---

## Monthly Schedule

```python
@flow(schedule=CronSchedule(cron="0 2 1 * *"))  # 2am on 1st of month
async def monthly_fine_tune():
    pairs = extract_training_pairs()
    
    if len(pairs) < 100:
        log("Not enough training data — skipping month.")
        return
    
    # this runs as a separate process — fine-tuning is heavy
    subprocess.run(["python", "fine_tune.py", "--pairs", str(len(pairs))])
    
    # evaluate before promoting
    new_version = get_latest_version()
    eval_results = await evaluate_new_version(new_version)
    
    if eval_results["regression_detected"]:
        alert_user("Regression detected — not promoting v{new_version}")
        return
    
    promote_version(new_version)
    mark_pairs_as_used(pairs)
```

---

## CLI Commands

```
/finetune status          show latest version, when next scheduled
/finetune run             manually trigger fine-tune cycle now
/finetune history         show all versions with eval deltas
/finetune rollback <v>    switch active model to previous version
/finetune compare <v1> <v2>  side-by-side responses from two versions
```

The compare command is the killer feature — chat with two versions in parallel to qualitatively assess what changed.

---

## Build Order

```
Phase 1 — Data layer
  ├── Quality filter for training pairs
  ├── extract_training_pairs() with minimum threshold
  └── model_versions table

Phase 2 — Training (offline, manual first)
  ├── Unsloth setup script
  ├── DPO training config
  ├── Save adapter

Phase 3 — Deployment
  ├── Merge + GGUF conversion script
  ├── Ollama Modelfile generation
  ├── ollama create automation

Phase 4 — Evaluation gate
  ├── Standing eval suite (depends on eval plan)
  ├── Regression detection
  └── Promotion logic

Phase 5 — Schedule + CLI
  ├── Prefect monthly flow
  ├── /finetune commands
  └── /finetune compare (side-by-side chat)
```

---

## The Open Questions

- **Catastrophic forgetting** — fine-tuning on personal preferences can degrade general reasoning. How do you measure this? Standing eval suite must include both Hermes-specific tasks AND general capability tests (MMLU-style).
- **Drift over time** — your preferences from 6 months ago might not match today. Weight older feedback less? Or only train on the last 90 days?
- **Cold-start problem** — first few fine-tunes have little data. Maybe wait 6 months of feedback collection before the first cycle.
- **Bad-pair detection** — if you correct something incorrectly (you were wrong, agent was right), that's poisoned training data. Manual review queue before pairs enter training?
- **Hybrid with instruction reflection** — when the daily job updates the system prompt AND the monthly job updates weights, which takes precedence? They could conflict.

---

## What This Achieves (and what it doesn't)

**What it achieves:**
- Genuine personalization at the model level
- Patterns the model has *internalized*, not just been instructed about
- Reduced prompt overhead (fewer guidelines needed if they're baked in)
- A model that becomes uniquely yours over months

**What it doesn't achieve:**
- Instant adaptation — there's a 30-day lag minimum
- Replacement for good prompting — DPO is additive, not curative
- Magic — bad input data gives bad models

**The honest assessment:**
This is real, doable, and few personal-agent projects do it. But it's also 80% of the engineering effort for maybe 20% of the daily quality improvement compared to good instruction reflection. The reflection loop in Plan 1 gives you 80% of the benefit at 20% of the complexity.

Build the reflection loop first. Run it for 3-6 months. Once you have a substantial corpus of corrections AND clear patterns the daily reflection can't capture, *then* invest in fine-tuning.