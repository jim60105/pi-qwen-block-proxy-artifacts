# PLE forensics (read-path toolchain)

Scripts behind the substrate analysis in [`../../COHERE-2026-10-26.md`](../../COHERE-2026-10-26.md)
(and the September surgery program documented in `SURGERY.md` / README
*"Weights-level surgery"*). They compute, **read-only**, which rows of the
model's layer-2 hashed n-gram table any given string queries.

Run order (host-side, stdlib-only, plus a live tokenize endpoint on the
served model; no table bytes needed for row ids):

1. `g0_tokenize.py` — tokenize the reference prompts via `POST /tokenize`
   (adjust the checkpoint snapshot path + endpoint at the top; the artifact
   strings come fragment-built from `tools/repro.py`).
2. `g3_rows.py` / `g3_final.py` — the row-addressing predictor (SplitMix64 +
   seed-derived odd multipliers + per-head primes + XOR fold). Fixtures
   `g0_buffers.json` (multipliers), `g3_S_star.json` (**240** canonical
   template rows) are committed; anchors for validation: multiplier
   derive-match from seed 1234, head-size sum 320,001,446, template
   tokenization 44 tokens / 7-token prefix, |S*| = 240.
3. `g5_mutant_rows.py` — the **144** host-region mutant rows (fixture
   committed). Together 384 = exactly what the September fork zeroed.
4. `b_collision_final.py` — forward-hash the Cohere-capture shapes (Beijing
   bucket URL, full PUT command, metadata addresses) and intersect with the
   384-row ground truth; benign controls included. Output fixture:
   `collision_final.json`.
5. `c_identity_scan.py` — extract the 240 S* rows directly from each cached
   build's safetensors (numeric shard order) and compare across builds.
6. `g0_ngram_harness.py` — optional rigor: cross-checks the pure-Python
   predictor against upstream `compute_ngram_ids` verbatim; requires the vLLM
   environment from the serving container.
7. `restore.py` / `zero_rows.py` / `verify_fork.py` — the September *write*
   path (ablation), kept for completeness; do not run against a cache you
   care about without reading `SURGERY.md` first.

`recover_from_session_db.py` — how this whole directory was rebuilt after the
original `ple-surgery-fork/` was deleted: it replays `write` tool-call
contents out of the opencode session DB. History lesson: forensics that
matters belongs in git.

Paths are machine-local in places (snapshot dirs, engine URLs): edit to your
layout. No model is dialed by anything here; the only network is `/tokenize`.
