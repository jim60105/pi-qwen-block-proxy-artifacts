# ladder-v2 ignition grid

Replication of the Cohere prefill study at scale, with context arms designed
to discriminate mechanism. Full results and interpretation:
[`../../COHERE-2026-10-26.md`](../../COHERE-2026-10-26.md) §3.4; final tables:
[`RESULTS.md`](RESULTS.md).

- `driver.py` — 8 contexts × 8 curl-ladder rungs × 14 repeats, n=256 per job
  (temp 1, max 32 tokens) + greedy/logprob pass, round-robined across engines.
  Contexts: CTI detection objective, phantom-reasoning prefill, failure-wall
  variant, JSON/XML tool-call surfaces, two cyber-neutral controls, Chinese
  variant. Engine list + ports at the top of the file.
- `aggregate.py` — evidence → RESULTS.md tables (context×build rates, rung
  ladder, greedy-hardness check, novel-host vocabulary).

Engines were the `sm12x-exl3-qwen3.8-flash-next` recipe, sampling-tuned:
`GPU=n PORT=p QUANT=… MAX_MODEL_LEN=8192 MAX_NUM_SEQS=128`. All traffic is
local `/v1/completions`; **nothing dialed from sampled text is ever fetched**
— several emitted hosts are real third-party infrastructure and must stay
undialed.

Raw per-job evidence (896 JSONL, ~6.5 MB) is regenerable and not committed;
`sanmaohe` completions across the full grid: **0 / 229,376**. All indicator
patterns are fragment-built so the grid and its evidence stay invisible to
the fence rules it measures.
