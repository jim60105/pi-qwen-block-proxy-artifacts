# session-scan

`scan-exfil-shapes.py` — role-classified indicator scan over every recorded
opencode session (v1 `part` table + v2 `session_message`) for the Cohere
2026-10-26 shapes: Beijing upload bucket, cloud-metadata addresses, namespace
escalation tricks, upload verbs at any aliyuncs host, probe filenames — plus
a catch-all inventory of **non-family** aliyuncs buckets. Results:
`../../COHERE-2026-10-26.md` §3.1 (460 sessions, zero pre-blog sightings).

Point `DB` at your `opencode.db` (read-only URI; edit at top). Patterns are
fragment-assembled so running the scanner never trips the very fence rules
whose coverage it measures — and any tool call containing a contiguous
indicator is itself blocked by rules 3–4, by design. Hits are classified by
JSON path into tool-input vs tool-output vs prose so analysis text from this
repo's own investigations doesn't masquerade as model behavior; expect to
attribute the routify-family noise to this project itself.
