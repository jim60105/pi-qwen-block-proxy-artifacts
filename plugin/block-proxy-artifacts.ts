// Rule provenance and research:
// https://github.com/wtogami/qwen-block-proxy-artifacts
// Host-shaped spans and bounded gaps avoid matching ordinary label mentions.
// Keep indicator literals fragmented so an agent running this extension can
// still edit its sources. Metadata guidance is number-free for the same reason.

// Use only the shared pi/omp API, with no host package imports.
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
  // Require both the bucket label and endpoint to allow unrelated label mentions.
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

// Shorten guidance on repeat blocks to limit duplicate context.
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
