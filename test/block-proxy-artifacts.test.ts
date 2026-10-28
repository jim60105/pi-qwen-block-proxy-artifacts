import { test } from "node:test"
import assert from "node:assert/strict"
import blockProxy from "../plugin/block-proxy-artifacts.ts"

// Fragment indicators so this file can be edited while the extension is active.
const DEAD_URL = [
  "https://routify", "-file", "-proxy-sg.oss-ap-southeast-1",
  ".aliyuncs.com/proxy_", "temp_file/production/trace/request?Signature=example",
].join("")
const UPLOAD_URL = ["https://sanmaohe", ".oss-cn-beijing", ".aliyuncs.com/upload"].join("")
const META_IP = ["http://169", ".254.169.254/latest/meta-data/"].join("")
const META_ALI = ["100.100", ".100.200"].join("")
const META_NAME = ["http://metadata", ".google.internal/computeMetadata/v1/instance/"].join("")

type Host = Parameters<typeof blockProxy>[0]
type Handler = Parameters<Host["on"]>[1]

function loadPolicy() {
  let handler: Handler | undefined
  blockProxy({ on(_event, callback) { handler = callback } })
  assert.ok(handler)
  const hook = handler
  return (input: unknown, session = "s1", toolName = "bash") => {
    const event = { type: "tool_call", input, toolName, toolCallId: "probe" }
    return hook(event, { sessionManager: { getSessionId: () => session } })
  }
}

function nest(depth: number, leaf: unknown): unknown {
  let value = leaf
  for (let i = 0; i < depth; i++) value = [value]
  return value
}

test("blocks incident arguments across built-in, custom, MCP, and subagent tools", () => {
  const call = loadPolicy()
  const shapes = [
    ["webfetch", { url: DEAD_URL, format: "markdown" }],
    ["mcp_fetch", { urls: ["https://example.org", DEAD_URL] }],
    ["bash", { command: `curl -s ${DEAD_URL}` }],
    ["task", { prompt: { context: "fetch", urls: [DEAD_URL] } }],
    ["custom_tool", { payload: DEAD_URL.toUpperCase() }],
    ["write", { path: "report.txt", content: DEAD_URL }],
  ] as const
  for (const [tool, args] of shapes) {
    const before = structuredClone(args)
    const result = call(args, "incident", tool)
    assert.equal(result?.block, true, tool)
    assert.equal(typeof result?.reason, "string")
    assert.deepEqual(args, before, "blocked arguments must remain unchanged")
  }
})

test("blocks relay template variants on alternate OSS endpoints", () => {
  const call = loadPolicy()
  const hosts = [
    ["routify", "-file", "-proxy-sg.ap-southeast-1.oss", ".aliyuncs.com"],
    ["routify", "-file", "-proxy-sg.oss-ap-southeast-1-internal", ".aliyuncs.com"],
    ["routify", "-file", "-oversea.oss-acdr-ut-1", ".aliyuncs.com"],
    ["routify", "-file", "-proxy.oss-accelerate", ".aliyuncs.com"],
    ["routify", "-file", "-proxy.oss-cn-beijing", ".aliyuncs.com"],
    ["routify", "-file", "-proxy-eu.oss-eu-west-3", ".aliyuncs.io"],
  ]
  for (const host of hosts) {
    assert.equal(call({ url: `https://${host.join("")}/download` })?.block, true)
  }
})

test("blocks captured upload targets and metadata addresses in arbitrary arguments", () => {
  const call = loadPolicy()
  const inputs = [
    { url: UPLOAD_URL },
    { urls: [["https://sanmaohe", ".oss-cn-beijing.oss", ".aliyuncs.io/upload"].join("")] },
    { command: `curl -X PUT --data-binary payload ${UPLOAD_URL}` },
    { url: META_IP },
    { server: META_ALI },
    { url: `http://${META_ALI}/latest/meta-data/` },
    { url: META_NAME.toUpperCase() },
  ]
  for (const input of inputs) assert.equal(call(input)?.block, true)
})

test("scans object keys and values through depth six", () => {
  const call = loadPolicy()
  assert.equal(call({ [DEAD_URL]: "metadata" })?.block, true)
  assert.equal(call({ nested: [{ [META_ALI]: null }] })?.block, true)
  assert.equal(call(nest(6, DEAD_URL))?.block, true)
  assert.equal(call(nest(7, DEAD_URL)), undefined)
})

test("allows legitimate sources and indicator near misses without modifying arguments", () => {
  const call = loadPolicy()
  const inputs = [
    { url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC5795620/" },
    { url: "https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=EXT_ID:28759224" },
    { url: "https://www.targetmol.com/attachment/DataSheet/1B25D990/T11717" },
    { url: "https://my-backup.oss-cn-beijing.aliyuncs.com/legit-object.tar.gz" },
    { url: "https://my-app.ap-southeast-1.oss.aliyuncs.com/x" },
    { url: "https://my-relay.oss-cn-hangzhou.aliyuncs.com/proxy_temp_file/signed-export?sig=valid" },
    { url: ["https://routify", "_file", "_proxy-sg.example.org/download"].join("") },
    { url: ["https://routify", "-file", "-proxy-hz.example.net/download"].join("") },
    { notes: "audit notes: the routify-file-proxy bucket uploads to aliyuncs.com daily" },
    { notes: "routify is also a logistics company" },
    { path: "/var/tmp/proxy_temp_file/report.csv" },
    { url: "https://sanmaoheling.com/blogs/news.atom" },
    { command: "grep -ri sanmaohe ./docs/" },
    { url: "http://169.254.1.1/other-link-local" },
    { url: "http://" + ["1", ".169.254", ".169.254"].join("") + "/longer-address" },
    { url: "http://100.100.100.201/" },
    { version: ["169.254", ".169.2540", "-1"].join("") },
    { url: "https://metadata.example.com/google/internal" },
  ]
  for (const input of inputs) {
    const before = structuredClone(input)
    assert.equal(call(input), undefined, JSON.stringify(input))
    assert.deepEqual(input, before)
  }
})

test("allows empty and non-string inputs", () => {
  const call = loadPolicy()
  for (const input of [undefined, null, {}, [], 42, true, { a: { b: [null, 1, true] } }]) {
    assert.equal(call(input), undefined)
  }
})

test("warning history follows the current session and is independent per factory", () => {
  const call = loadPolicy()
  const first = call({ url: DEAD_URL }, "s1")!
  const repeat = call({ url: DEAD_URL }, "s1")!
  assert.equal(first.block, true)
  assert.equal(repeat.block, true)
  assert.notEqual(first.reason, repeat.reason)
  assert.deepEqual(call({ url: DEAD_URL }, "s2"), first)
  assert.deepEqual(call({ url: DEAD_URL }, "s1"), repeat)
  assert.deepEqual(loadPolicy()({ url: DEAD_URL }, "s1"), first)
})

test("clean calls do not consume first-warning guidance", () => {
  const call = loadPolicy()
  call({ url: "https://example.org" })
  assert.deepEqual(call({ url: DEAD_URL }), loadPolicy()({ url: DEAD_URL }))
})

test("each indicator family keeps distinct first and repeat guidance without echoing the URL", () => {
  const call = loadPolicy()
  const firstReasons = new Set<string>()
  const repeatReasons = new Set<string>()
  for (const url of [DEAD_URL, UPLOAD_URL, META_IP]) {
    const first = call({ url }, url)!
    const repeat = call({ url }, url)!
    assert.equal(first.block, true)
    assert.equal(repeat.block, true)
    assert.notEqual(first.reason, repeat.reason)
    assert.equal(first.reason.includes(url), false)
    assert.equal(repeat.reason.includes(url), false)
    firstReasons.add(first.reason)
    repeatReasons.add(repeat.reason)
  }
  assert.equal(firstReasons.size, 3)
  assert.equal(repeatReasons.size, 3)
})

test("warning-state eviction restores first guidance without ever allowing a blocked call", () => {
  const call = loadPolicy()
  const first = call(DEAD_URL, "s0")!
  const repeat = call(DEAD_URL, "s0")!
  for (let i = 1; i < 500; i++) assert.deepEqual(call(DEAD_URL, `s${i}`), first)
  assert.deepEqual(call(DEAD_URL, "s0"), repeat)
  assert.deepEqual(call(DEAD_URL, "s500"), first)
  assert.deepEqual(call(DEAD_URL, "s0"), first)
})
