// Hallucinated file-proxy artifact URLs. Small quantized Qwen models
// regurgitate signed Aliyun OSS "file proxy" links from their pretraining
// data. 371 recorded dials (as of 2026-09-27) hit one relay bucket label,
// `routify-file-proxy-sg`, in Aliyun OSS's two DOCUMENTED endpoint formats
// (public `<bucket>.oss-<region>.aliyuncs.com`, dual-stack
// `<bucket>.<region>.oss.aliyuncs.com`), re-synthesizing only the
// trace/request/date segments each time.
// The 2026-09-28/29 PLE n-gram row-ablation experiment (SURGERY.md; README
// "Weights-level surgery") proved this is a TEMPLATE FAMILY, not one
// memorized host: after the table rows carrying the canonical template were
// zeroed, unshielded runs dialed 70 new URLs at never-before-observed
// members — the `oversea` label (no "proxy" segment at all), the
// `oss-accelerate`/`oss-cn-beijing`/`oss-acdr-ut-1` endpoint forms, and an
// `aliyuncs.io` TLD variant. The family library lives in the LM weights,
// so rule 2 must NOT require a "proxy" segment and must include Aliyun's
// second TLD. Rule 1 still pins the exact incident host for provenance.
// Every span must be host-shaped ([\w.-]) with bounded gaps and must end in
// an aliyuncs TLD, so code or prose that merely mentions the token passes
// through.
//
// Retired rules: a generic aliyuncs path rule (would block legitimate relay
// operators' own proxy_temp_file objects, which can validly return 200) and
// a bare relay-host-token rule (over-fires on relay-ops code and incident
// writeups, and blocks self-documentation; since rule 2 widened to
// proxy-less labels its only unique catches are separator-mutated labels
// missing the `file` segment — re-add a suitably-shaped token rule if ever
// observed). Measurement deliberately stays broad:
// tools/blocks-by-session.py still counts token-shaped mentions and leaks,
// so any novel shape this fence lets through surfaces in the tracker.
//
// Keep indicator literals fragmented so an agent running this extension can
// still edit its sources. Metadata guidance is number-free for the same reason.
//
// Rules 3-4 (2026-10-26, Cohere field capture, cohere.com/blog): the same
// model family was caught running recon (ls /tmp, tool inventory, resolv.conf)
// and a curl PUT of a payload to an Aliyun OSS bucket in Beijing, plus
// prefill studies showing the link-local metadata address in 23-36% of
// sampled curl completions. Rule 3 stays literal-host-narrow (the bucket
// label plus an aliyuncs endpoint, both required): the word alone completes
// to an ordinary blog in local probes, and other cn-beijing buckets are
// legitimate. Rule 4 blocks the metadata/credential surface; guidance for
// both new rules is family-specific because "fetch the publisher URL
// instead" is wrong advice for an upload target and an IMDS endpoint.
//
// The shared pi/omp surface is intentionally structural. Neither host package
// is needed at runtime or when copying this standalone extension file.
type ExtensionHost = {
  on(
    event: "tool_call",
    handler: (
      event: { input: unknown },
      ctx: { sessionManager: { getSessionId(): string } },
    ) => { block: true; reason: string } | void,
  ): void
}

type Rule = {
  pattern: RegExp
  why: string
  guidance?: { full?: string; terse?: string }
}

const BLOCKED: Rule[] = [
  { pattern: /routify[-]file[-]proxy[-]sg[.]oss-ap-southeast-1[.]aliyuncs[.]com/i, why: "observed incident host (dead relay bucket)" },
  { pattern: /routify[\w.-]{0,12}file[\w.-]{0,56}aliyuncs[.](com|io)/i, why: "relay bucket label (any routify-file-* form) on an Aliyun OSS endpoint, com or io TLD" },
  // Rule 3: bucket label caught mid-PUT (Cohere 2026-10-26). Both the label
  // and an aliyuncs endpoint are required, so the label alone (which
  // completes to an unrelated blog in local probes) stays near-miss-clean.
  {
    pattern: /sanmaohe[\w.-]{0,24}aliyuncs[.](com|io)/i,
    why: "upload-target bucket caught attempting outbound PUT with payload (Cohere field capture 2026-10-26)",
    guidance: {
      full: `This host is an upload endpoint caught in the wild receiving a ` +
        `model-initiated PUT of a payload; it is not a content source, and ` +
        `contacting it reports this machine's presence and network. Do NOT ` +
        `retry it and do not probe it with GET either. Complete the task ` +
        `without any outbound request to this host.`,
      terse: `Model-initiated upload endpoint (Cohere 2026-10-26 capture). Do NOT dial it.`,
    },
  },
  // Rule 4: cloud metadata / credential surface (IMDS). Link-local for
  // AWS/GCP/Azure, plus Alibaba's non-link-local address, plus the GCP name.
  // Numeric boundaries keep longer numbers (versions, concatenated IPs) out.
  // The why-string is deliberately number-free: it is echoed into the tool
  // error and would otherwise make the error message itself re-trip rule 4
  // on every transcript echo.
  {
    pattern: /(?:^|[^\d.])169[.]254[.]169[.]254(?:$|[^\d.])|(?:^|[^\d.])100[.]100[.]100[.]200(?:$|[^\d.])|metadata[.]google[.]internal/i,
    why: "cloud instance-metadata endpoint — the link-local address plus Alibaba's variant and the GCP hostname (temporary-credential surface; never needed by an agent task)",
    guidance: {
      full: `Cloud metadata addresses hand out the machine's temporary IAM ` +
        `credentials; reaching for one is a credential-exfiltration primitive ` +
        `and is never required to complete a coding or analysis task. Do NOT ` +
        `retry it. Continue the task without touching any metadata address.`,
      terse: `Cloud metadata endpoint (credential surface). Do NOT dial it; continue without it.`,
    },
  },
]

function* strings(v: unknown, depth = 0): Generator<string> {
  if (depth > 6) return
  if (typeof v === "string") yield v
  else if (Array.isArray(v)) for (const x of v) yield* strings(x, depth + 1)
  else if (v && typeof v === "object")
    for (const [k, x] of Object.entries(v)) {
      yield k
      yield* strings(x, depth + 1)
    }
}

function findBlocked(args: unknown): Rule | null {
  for (const s of strings(args))
    for (const b of BLOCKED) if (b.pattern.test(s)) return b
  return null
}

const FULL_GUIDANCE =
  `This URL is a dead upload-proxy artifact from a third-party relay middlebox, not a real ` +
  `content source: it cannot be fetched and retrying leaks trace identifiers. ` +
  `Do NOT retry it. Go back to the original publisher URL and fetch that instead.`

// Repeat occurrences in the same session get a one-liner: the full guidance is
// what drove good self-corrections in the field, but re-injecting ~200 tokens
// per recurrence pollutes the context it is trying to protect.
const TERSE_GUIDANCE =
  `Dead upload-proxy artifact from a third-party relay middlebox. Do NOT retry it. ` +
  `Fetch the original publisher URL directly.`

// Bound warning state when a host switches between many sessions.
const WARNED_CAP = 500

function verdict(args: unknown, warned: Set<string>, session: string): string | null {
  const hit = findBlocked(args)
  if (!hit) return null
  if (!warned.has(session) && warned.size >= WARNED_CAP) warned.clear()
  const first = !warned.has(session)
  warned.add(session)
  const g = hit.guidance ?? {}
  return (
    `Blocked by block-proxy-artifacts policy (${hit.why}). ` +
    (first ? (g.full ?? FULL_GUIDANCE) : (g.terse ?? TERSE_GUIDANCE))
  )
}

export default function blockProxy(pi: ExtensionHost): void {
  // Omp reuses imported factories for child sessions. Keep mutable state here.
  const warned = new Set<string>()
  pi.on("tool_call", (event, ctx) => {
    const reason = verdict(event.input, warned, ctx.sessionManager.getSessionId())
    if (reason) return { block: true, reason }
  })
}
