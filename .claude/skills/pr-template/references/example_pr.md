Here's a filled-out example:

---

### Related Issues

Closes #142 — Embedding scores returning incorrect results for non-normalized models

### Problem

Cosine similarity scores were wrong because the loop reused `idx` across both the outer and inner iterators, causing chunk IDs to be matched against the wrong embeddings. Any model that doesn't normalize by default (like Qwen3-small) was also silently returning dot products instead of true cosine scores.

### Solution

Renamed loop variables to `data_idx` and `term_idx` to prevent the index collision. Added explicit L2 normalization before scoring so the function works correctly regardless of whether the embedding model normalizes its output.

### Files Touched

- `embeddings/scorer.py` — Fixed the dual `idx` bug and added normalization logic. This is where the broken scoring loop lived.
- `embeddings/utils.py` — Added a `normalize()` helper so normalization can be reused elsewhere without duplicating the `np.linalg.norm` call.
- `tests/test_scorer.py` — New test file, see below.

### Tests

- `test_correct_chunk_id_assignment` — Verifies that each chunk ID maps to the right embedding after the index fix. Caught the original bug.
- `test_scores_without_normalized_embeddings` — Runs scoring against deliberately non-normalized vectors and confirms results match the full cosine formula.
- `test_normalize_unit_length` — Confirms the `normalize()` helper returns a vector with norm ~1.0.