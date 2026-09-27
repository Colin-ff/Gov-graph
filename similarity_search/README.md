# ToR Similarity Search — Duplicate Detection Spike

A two-stage pipeline for flagging duplicate governance groups in the
Terms-of-Reference (ToR) dataset:

1. **Embed** each ToR with `all-mpnet-base-v2`.
2. **Cosine similarity** retrieves candidate pairs above a threshold (recall stage).
3. **LLM verification** (Gemini) judges each candidate pair (precision stage).

```
extract_tors.py  ─►  tors.json  ─►  similarity_search.py  ─►  heatmap + verdicts
   (.docx → fields)                 (embed → cosine → Gemini)
```

---

## Quick start

> **Windows:** create the venv at a **short path** (e.g. `C:\tmp\ssvenv`), not
> inside this deeply-nested repo folder. PyTorch ships header files whose paths
> exceed Windows' 260-char limit, so `pip install` fails with an
> `OSError: No such file or directory: ...predicated_tile_access_iterator_residual_last.h`
> when the venv sits under the project directory. A short venv root avoids it
> (alternatively, enable long-path support). macOS/Linux are unaffected.

```powershell
# Windows (PowerShell) — venv at a SHORT path
python -m venv C:\tmp\ssvenv
C:\tmp\ssvenv\Scripts\pip install -r similarity_search\requirements.txt

# 1. Build the dataset (10 curated ToRs; drop --only-ten for all 40)
C:\tmp\ssvenv\Scripts\python similarity_search\extract_tors.py --only-ten

# 2. Run the pipeline
C:\tmp\ssvenv\Scripts\python similarity_search\similarity_search.py --threshold 0.55
```

```bash
# macOS / Linux — a venv inside the repo is fine
python -m venv similarity_search/.venv
similarity_search/.venv/bin/pip install -r similarity_search/requirements.txt
similarity_search/.venv/bin/python similarity_search/extract_tors.py --only-ten
similarity_search/.venv/bin/python similarity_search/similarity_search.py --threshold 0.55
```

`extract_tors.py` is standard-library only, so it also runs under the backend
venv. `similarity_search.py` needs the packages in `requirements.txt`
(`sentence-transformers` pulls in PyTorch — the first run downloads the model
and can take a few minutes).

The LLM stage **requires** `GEMINI_API_KEY` to be set — the script loads it
from the repo-root `.env` automatically (same file the Flask backend uses,
and the same key used by the ToR autofill feature), or you can export it in
your shell. Without a key, the script exits with an error unless you pass
`--no-llm`, which skips the LLM stage and runs embedding + cosine only.

---

## The approach, and why

### The key problem: these ToRs are ~70% boilerplate

Every ToR in the dataset is template-generated. The Purpose section, Composition,
Quorum, Resolutions, Reporting, and Review blocks are near-identical across all
40 documents — for example every Purpose opens with:

> *"The group is established to oversee and guide matters within its remit. In
> practical terms, … The group provides assurance, advice and coordination to
> support institutional decision-making and accountability."*

**If you embed the raw document text, that shared boilerplate dominates the
vector and every pair scores ~0.85+ cosine — the threshold becomes meaningless
and everything looks like a duplicate.** This is the single most important design
decision in the spike.

**So we don't embed the raw text.** `extract_tors.py` parses each `.docx` and
keeps only the fields that actually distinguish one group from another, then
builds a compact `embedding_text` from them. Field selection follows the signal
ranking below.

### Field selection (what goes into the embedding)

Duplicate detection cares about *what a group does and where it sits*, not who
its members are or how often it meets.

| Signal | Field | In embedding? | Why |
|--------|-------|:---:|-----|
| **High** | Purpose (distinguishing clause) | ✅ | The clearest statement of why the group exists. We strip the boilerplate wrapper and keep only the "in practical terms …" clause. |
| **High** | Responsibilities / scope (section 8) | ✅ | The most detailed description of what the group is accountable for. |
| **High** | Reporting line (section 6) | ✅ | Same purpose + different reporting line can mean *not* a duplicate. |
| Medium | Scope / jurisdiction | ✅ (implicit) | Faculty vs university-wide is carried in the name and reporting line. |
| Medium | Group type | ✅ | Committee / Working Group / Taskforce — a lightweight structural signal, derived from the name. |
| Medium | Decision authority | ⚠️ inferable | The template doesn't state it explicitly; the group type is a proxy. |
| Low | Members, chair, secretariat | ❌ | Membership churns and says nothing about purpose. |
| Low | Meeting cadence, dates, doc version | ❌ | Administrative metadata, pure noise for similarity. |

The assembled `embedding_text` looks like:

```
Committee. Purpose: oversee research data management, access, retention and
governance. Responsibilities: monitor research strategy...; consider research
integrity...; ... Reports to: Research Committee.
```

### Why `all-mpnet-base-v2`

A strong, widely used general-purpose sentence embedding model (768-dim) that
tops MTEB semantic-textual-similarity benchmarks for its size and runs locally
with no API cost. We L2-normalise the vectors so cosine similarity reduces to a
dot product.

### Stage 2 — cosine similarity + threshold

We compute the full pairwise cosine matrix, save it as a heatmap, and list every
pair at or above the threshold as a **candidate**.

**Recommended starting threshold: `0.55`.** Reference scale for
`all-mpnet-base-v2` cosine on the *distilled* text (not raw docs):

| Range | Interpretation |
|-------|----------------|
| `< 0.40` | unrelated |
| `0.40 – 0.55` | same domain, different function |
| `0.55 – 0.75` | strong overlap → **candidate duplicate** |
| `> 0.75` | near-paraphrase → very likely duplicate |

The threshold is set **low on purpose**. In a two-stage design the embedding
step should maximise **recall** (catch every plausible duplicate) and let the
**LLM be the precision filter**. Sending a few extra pairs to the LLM is cheap;
silently dropping a real duplicate below the cutoff is not recoverable.

### Calibrating the threshold on this dataset

The 10 curated ToRs were chosen to include known relationships, so the threshold
can be tuned against ground truth rather than guessed:

| Pair | Relationship | Should be flagged? |
|------|--------------|:---:|
| Research **Data** Gov ↔ Research **Information** Gov | near-duplicate (differ only in data-vs-information) | **Yes** |
| Audit & Risk ↔ Finance | identical scope + same parent, different purpose | borderline |
| Education ↔ Faculty Education | same purpose/scope, **different jurisdiction + reporting line** | **No** |
| Cyber Security ↔ AI Governance | overlapping digital scope, same parent | borderline |

`similarity_search.py` prints the cosine score for the ground-truth duplicate
pair(s) on every run. Pick the threshold that puts *Research Data ↔ Information
Governance* above the line and *Education ↔ Faculty Education* below it (or into
the LLM's hands). That gives a defensible, data-driven number.

### Stage 3 — LLM verification

Each candidate pair goes to Gemini (`gemini-flash-lite-latest`) with the distilled fields
and a rubric: duplicates share purpose **and** scope **and** reporting line;
same-domain-different-function or same-purpose-different-jurisdiction pairs are
**not** duplicates. The model is constrained to a JSON schema
(`is_duplicate`, `confidence`, `reasoning`) via structured outputs, so the result
is machine-readable with no parsing guesswork.

---

## Files

| File | Purpose |
|------|---------|
| `extract_tors.py` | `.docx` → `tors.json` (field extraction; stdlib only) |
| `similarity_search.py` | embed → cosine → heatmap → LLM verify |
| `tors.json` | generated dataset (distilled fields + `embedding_text`) |
| `similarity_heatmap.png` | generated cosine-similarity heatmap |
| `requirements.txt` | pinned dependencies for the pipeline |

## Notes / next steps

- **Dataset location:** the ToR `.docx` files live in
  `../../ClientGovernanceDataSet/Sandbox Data Set/Terms of Reference` (alongside
  the repo, not committed). Override with `extract_tors.py --src "<path>"`.
- **Scaling up:** drop `--only-ten` to embed all 40 ToRs. For a production
  registry, embeddings would be precomputed and stored (e.g. in the graph DB or
  a vector index) rather than recomputed each run.
- **Section parsing** relies on the current template's numbered headings
  (1 Purpose, 6 Reporting, 8 Scope). If the client changes the template, adjust
  the section numbers in `extract_tors.py`.
