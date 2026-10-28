# pi-qwen-block-proxy-artifacts

A shared pi and oh-my-pi (omp) extension that blocks hallucinated file-proxy
URLs, a known upload target, and cloud metadata endpoints before tool execution.
One standalone TypeScript file serves both hosts with no runtime dependencies.

## Upstream

Ported from [wtogami/qwen-block-proxy-artifacts][upstream]. The upstream
repository maintains the original incident reports and supporting evidence,
including the model experiments and reproduction/forensic tools. This fork
contains the pi/omp integration and its tests; research material is maintained
upstream rather than copied here. OpenCode support remains upstream.

## Install

Install the package directly from GitHub:

```bash
# omp
omp install https://github.com/jim60105/pi-qwen-block-proxy-artifacts

# pi
pi install https://github.com/jim60105/pi-qwen-block-proxy-artifacts
```

Both package managers fetch the repository and register the extension without
a local clone. Restart the host after installing. No build step or runtime
dependencies are required.

Alternatively, download `plugin/block-proxy-artifacts.ts` and place it in a
discovery directory:

| Host | Global directory | Project directory |
| --- | --- | --- |
| pi | `~/.pi/agent/extensions/` | `.pi/extensions/` |
| omp | `~/.omp/agent/extensions/` | `.omp/extensions/` |

Omp profiles and agent-directory overrides change the global directory.
Pi supports `/reload` for rediscovery; restart omp after adding or editing
an extension file.

## Behavior

The default factory registers `pi.on("tool_call", handler)` and scans
`event.input` across all tool names. Matching calls return
`{ block: true, reason }`; the host refuses execution and reports the reason
to the model. Arguments remain unchanged.

| Rule | Matches |
| --- | --- |
| Incident relay | The original dead relay host. |
| Relay family | `routify` and `file` in a bounded host-shaped span ending in `aliyuncs.com` or `aliyuncs.io`. |
| Upload target | The recorded `sanmaohe` bucket label with an Aliyun OSS endpoint. |
| Cloud metadata | The AWS/GCP/Azure and Alibaba metadata addresses, plus the GCP metadata hostname. |

Matching is case-insensitive. The scanner checks string values, array elements,
and object keys through six container levels. The exact patterns live in
`plugin/block-proxy-artifacts.ts`.

The first block in a session returns full guidance; repeats receive shorter
guidance. Warning history is keyed by `ctx.sessionManager.getSessionId()` and
kept inside each extension factory. A new warned session clears history when
500 sessions are already recorded. Reloading or restarting also resets warning
history. Blocking remains active after a reset.

`package.json#pi.extensions` declares the entry point. Both hosts accept this
manifest and the shared event API. API references are pi's published 0.73.1
[Extensions][pi-extensions] guide, omp's [Extensions][omp-extensions] guide,
and [Extension Loading (TypeScript/JavaScript Modules)][omp-loading].

## Limits

This is an argument filter, not a network sandbox. It can block tools that
merely quote an indicator, including file edits. Keep literal indicators
fragmented in source and test fixtures so an active extension can edit them.
Arguments nested deeper than six levels are not scanned.

Redirects, encoded addresses, and URLs assembled inside scripts can bypass
substring matching. Direct network activity in other extensions, user-entered
shell commands, and external programs are outside the intercepted tool pipeline.
A failed or disabled extension provides no protection.

After installation, verify a harmless call containing an indicator from a
fragment-assembled test fixture. For example, attempt to write the joined
indicator to a new file. The tool must report a policy block and the file must
remain absent. Do not verify by contacting a blocked endpoint.

## Development

Use Node.js 23.6 or newer for the test runner's native TypeScript stripping.
Runtime loading and TypeScript transpilation are supplied by the host.

```bash
npm ci
npm run typecheck
npm test
npm pack --dry-run
```

Tests cover the rule families and near misses, including depth boundaries,
object keys, unchanged arguments, and warning-state isolation/eviction. CI runs
the typecheck and tests, then checks package contents. No Python tools or host
packages are required for development.

Runtime verification uses omp 18.13.2 with an extracted npm package and an
isolated loopback fixture provider. Blocked tool calls must produce no filesystem
side effects, while clean calls execute and policy reasons reach the provider.
Pi compatibility is checked against its documented API; pi has not been installed
or executed for runtime verification.

## License

MIT. See [LICENSE](LICENSE) for the original attribution and terms.

[upstream]: https://github.com/wtogami/qwen-block-proxy-artifacts
[pi-extensions]: https://unpkg.com/@mariozechner/pi-coding-agent@0.73.1/docs/extensions.md
[omp-extensions]: https://github.com/can1357/oh-my-pi/blob/main/docs/extensions.md
[omp-loading]: https://github.com/can1357/oh-my-pi/blob/main/docs/extension-loading.md
