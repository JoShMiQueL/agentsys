# OpenCode 2 context-management hooks — research findings

Sources: `https://opencode.ai/v2/docs/build/plugins` (full page),
`https://opencode.ai/v2/docs/plugins`, `/v2/docs/config`, `/v2/docs/compaction`,
`/v2/docs/instructions`, `/v2/openapi.json`, `https://opencode.ai/config.json`.
Date: 2026-10-22.

## (a) Complete `ctx.*` hook catalog (OpenCode 2 plugin API)

Hooks register via `ctx.<domain>.hook(name, cb, opts?)` and return a
`Registration` with `dispose()`. Multiple plugins run in registration order;
later hooks see earlier edits.

### `ctx.session.hook` — `keyof SessionHooks`

| Hook name | Event type | Mutable fields |
|---|---|---|
| `prompt` | `SessionPrompt` | `prompt.text`, `prompt.files`, `prompt.agents`, `prompt.skills`, `metadata`, `delivery` (`"steer"→"queue"`). Runs once at admission, before attachment/skill resolution. No provider scoping. |
| `context` | `SessionContextHook` | `system: SystemPart[]` (push text parts), `messages`, `tools` (delete keys), `options` (temperature, maxTokens, provider options…). Runs for agent loop incl. tool continuations. |
| `compaction` | `SessionContextHook & { result?: SessionCompactionResult }` | Same as `context` (`system`, `messages`, `tools`, `options`) PLUS `result`. `messages` = transcript being summarized; OpenCode appends its summary prompt *after* hooks run. Setting `event.result = { summary, native?, metadata?, tokens? }` records the compaction and **skips the model call** — plugin writes the summary itself. |
| `generate` | `SessionContextHook` | Same shape; transient `ctx.session.generate` calls. |
| `title` | `SessionRequestHook & { result?: string }` | No `agent`/`tools`. Set `result` to skip the call. |
| `model.request` | `SessionModelRequestHook` | `headers` per model call; `event.kind ∈ primary/compaction/title/generate`. Optional `{providerID}` scoping. |
| `http.request` / `http.response` | HttpRequest/Response | Native HTTP req/res; `event.kind` distinguishes flows. Bodies are one-shot streams — clone/replace before reading. |
| `experimental.ws.handshake` | …HandshakeHook | `url`, `headers` for WS-transport providers, once per model call. |
| `experimental.ws.send` / `experimental.ws.receive` | …Send/ReceiveHook | `frame: string` rewritten in place. |
| `retry` | `SessionRetryHook` | `event.decision = {retry:false} | {retry:true, delay:ms}`. Sees `error`, `attempt` (1=initial). Note: *context-overflow recovery is separate — it compacts instead of retrying.* |

### Other domains

- `ctx.permission.hook("evaluate", cb)` — `event.effect: allow|ask|deny`, `event.message`. Runs for allow/ask only; configured `deny` is final (already used by `plugins/guard`).
- `ctx.tool.hook("execute.before" | "execute.after", cb)` — inspect/replace input; inspect result/error, rewrite `event.result`.
- `ctx.shell.hook("create.before", cb)` — `command`, `cwd`, `timeout`, `shell`, `env`.

### Non-hook context surfaces relevant here

- `ctx.event.subscribe({signal})` → `AsyncIterable<OpenCodeEvent>` — server event stream. Compaction lifecycle emits `session.compaction.*` events (docs: "Follow `session.compaction.*` events to learn when it finishes"); message schema has `Session.Message.Compaction = Running | Completed | Failed` with `reason: auto|manual`, `summary`, `tokens`.
- `ctx.session.synthetic({sessionID, text, description?, metadata?})` → durable synthetic message in session history (model-visible).
- `ctx.session.compact({sessionID, id?, delivery?})` — request compaction manually.
- `ctx.session.context({sessionID})` → current message list (what the model sees).
- `ctx.generate.text({model, prompt})` — one-shot generation, no session.
- Instruction entries API (experimental): `PUT /api/experimental/session/{id}/instructions/entries/{key}` — attach/replace a *durable* per-session instruction entry; announced to the model at next step boundary. `DELETE` removes; `GET` lists. Key pattern `^[a-z0-9][a-z0-9._-]*$`. Whether it's exposed as `ctx.session.*` in the plugin SDK isn't documented — HTTP route exists regardless.

## (b) Mechanisms that enable "re-inject context after compaction"

Three independent mechanisms, combinable:

1. **Instruction baseline auto-reload (free, no plugin).** Compaction docs: *"After compaction, the current versions of your instruction files become the session's baseline."* The instructions doc adds: *"If compaction or a revert removes that entry, a later read can load the file again."* So `AGENTS.md` + `instructions[]` entries are **re-read from disk at compaction** — editing `.opencode/memory/gotchas.md` updates survive compaction automatically *if* the file is an instruction source.
2. **`compaction` hook — shape the summary itself.** `ctx.session.hook("compaction")` can push extra `system` text (e.g. "the summary MUST preserve: current spec slug, open tasks, .opencode/ decisions") or fully replace the summarizer via `event.result`.
3. **Event stream → synthetic message / instruction entry.** Subscribe to `ctx.event.subscribe`, watch for a compaction-completed event (`session.compaction.*` / `Session.Message.Compaction{status:"completed"}`), then call `ctx.session.synthetic({sessionID, text: <re-read gotchas.md/spec state>})` or PUT an instruction entry. Synthetic lands in durable history; instruction entry lands in the privileged instruction block (position 6 in ordering).

## (c) Does a dedicated compaction hook exist?

**Yes — `ctx.session.hook("compaction", cb)` is a first-class hook** (V2, documented). It is *pre*-model-call: fires while OpenCode assembles the summary request. There is no `session.compacted` *hook* (post-compaction), but the event stream covers the after side.

## (d) Config surface

- `compaction: {auto=true, keep:{tokens=15000}, buffer=~15% limit≥16k}` — already set `auto:true` in `systems/reversing/system.json`. `prune`, `tail_turns`, `preserve_recent_tokens`, `reserved` are **deprecated** (V1 leftovers) — don't use.
- `providers.<p>.settings.compaction: {type:"summary"|"native"}` — native = provider-side encrypted checkpoint (OpenAI Responses only). Ollama → stays `summary`.
- `instructions: ["path|glob|url"]` — **static list, but content is dynamic**: files re-load on change and re-establish after compaction. `{file:…}` substitution also exists in config.
- `experimental`: nothing context-related current (`todo`, `subagent_depth`, `portable_shell_scanner`, `location_idle_timeout`; old `batch_tool`/`primary_tools`/`mcp_timeout`/`openTelemetry`/`disable_paste_summary`/`continue_loop_on_deny` all deprecated).
- `tool_output.max_lines/max_bytes` — pre-compaction truncation of tool results (spills to disk).

## (e) Comparable tools

- Claude Code: `SessionStart`, `PreCompact`, `SessionEnd` hooks — OpenCode's equivalents: none for start/end; `compaction` hook ≈ PreCompact; event stream ≈ post-observe.
- Spec-kit / SDD: state lives on disk (`state.md`), so post-compaction re-injection = re-read file. OpenCode's instruction-baseline reload already does this for instruction files — the clean mirror of Claude's SessionStart-reload.

## (f) Recommendation for agentsys

1. **Immediate (zero code):** add `"instructions": [".opencode/memory/gotchas.md", ".opencode/memory/decisions.md", ".opencode/memory/models.md"]` to each `system.json`. They auto-load at session start and **auto-reload as the post-compaction baseline** — solves 80% of the re-injection need without a plugin. (Gotchas is already the canonical memory file; making it an instruction keeps it model-visible through compactions.)
2. **Plugin `context-keeper`** (new, beside `plugins/guard`): register `ctx.session.hook("compaction")` pushing a `system` text part: "Summary MUST preserve: active spec slug, tasks.md progress, files touched, pending delegations." Optionally subscribe to `ctx.event.subscribe` and on compaction-completed call `ctx.session.synthetic({sessionID, text: "Re-read .opencode/specs/<slug>/state.md and tasks.md before continuing"})`.
3. **Do not** use deprecated `prune`/`tail_turns`/`preserve_recent_tokens`/`reserved`.
4. Native compaction is irrelevant (Ollama); keep default `summary`.
5. Instruction entries API (`PUT .../instructions/entries/{key}`) is the privileged-position alternative if `synthetic` proves too far down the message list — experimental, HTTP-only for now.
