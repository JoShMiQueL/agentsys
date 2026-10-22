// guard — replaces silent `deny` permission rules with agent-visible feedback.
//
// How it works:
//   A configured `deny` rule is FINAL and never reaches hooks. So instead of
//   denying destructive bash commands in `permissions`, this plugin registers a
//   `permission.hook("evaluate")` handler that sees every allow/ask decision,
//   re-checks the requested command against the destructive-pattern list, and
//   flips `event.effect` to "deny" with a `message`. The message becomes a
//   Tool.Error the model can read and reason about (ask the user, pick a
//   safer approach) instead of a silent block.
//
// Event shape (per https://opencode.ai/v2/docs/build/plugins#permissions):
//   interface PermissionEvaluation {
//     readonly sessionID: string
//     readonly agent?: string
//     readonly action: string            // e.g. "bash", "edit", "read"
//     readonly resources: readonly string[]  // matched resource strings (command)
//     readonly metadata?: Record<string, unknown>
//     readonly source?: { type: "tool"; messageID: string; id: string }
//     effect: "allow" | "ask" | "deny"   // mutable
//     message?: string                   // mutable — becomes the denial reason
//   }
// The handler below still reads fields defensively (optional chaining + a
// resource-normalization fallback) so an unexpected event shape degrades to a
// logged no-op instead of throwing inside the permission pipeline.

import { Plugin } from "@opencode/plugin"

interface GuardPattern {
  name: string
  re: RegExp
}

// Mirrors the six `deny` rules previously in systems/reversing/system.json,
// plus small defensive variants (reordered flags).
const DESTRUCTIVE: GuardPattern[] = [
  {
    // rm -rf, rm -fr, rm -r -f, rm --recursive --force, etc.
    name: "rm -rf",
    re: /\brm\b(?=[^;&|`]*\s-{1,2}[a-zA-Z]*r)(?=[^;&|`]*\s-{1,2}[a-zA-Z]*f)/i,
  },
  {
    name: "Remove-Item -Recurse -Force",
    re: /\bRemove-Item\b(?=[^;&|`]*-Recurse)(?=[^;&|`]*-Force)/i,
  },
  {
    name: "git push --force",
    re: /\bpush\b[^;&|`]*--force/i,
  },
  {
    name: "git push -f",
    re: /\bpush\b[^;&|`]*\s-f(\s|$)/i,
  },
  {
    name: "git reset --hard",
    re: /\breset\s+--hard\b/i,
  },
  {
    name: "git clean -fd",
    re: /\bclean\s+-(?:[a-zA-Z]*f[a-zA-Z]*d|d[a-zA-Z]*f)[a-zA-Z]*\b/i,
  },
]

function blockMessage(pattern: GuardPattern, command: string): string {
  return (
    `BLOCKED: '${pattern.name}' matched destructive-command guard ` +
    `(command: ${command.slice(0, 200)}). ` +
    `If the user explicitly wants this, ask them to confirm, then retry — ` +
    `do not work around with an equivalent destructive command.`
  )
}

// Extract candidate command strings from whatever the event gives us.
function resourcesOf(event: any): string[] {
  const out: string[] = []
  const push = (v: unknown) => {
    if (typeof v === "string" && v) out.push(v)
    else if (Array.isArray(v)) v.forEach(push)
  }
  push(event?.resources)
  push(event?.resource)
  // Fallbacks if a future version nests the command elsewhere.
  push(event?.input?.command)
  push(event?.metadata?.command)
  return out
}

export default Plugin.define({
  id: "guard",
  async setup(ctx) {
    try {
      await ctx.permission.hook("evaluate", async (event: any) => {
        try {
          const action = event?.action
          // Only bash/shell actions carry free-form destructive commands.
          if (action !== "bash" && action !== "shell") return
          const resources = resourcesOf(event)
          if (resources.length === 0) {
            console.log(
              `[guard] evaluate event for '${action}' had no resources; ` +
                `fields: ${Object.keys(event ?? {}).join(",")}`,
            )
            return
          }
          for (const cmd of resources) {
            for (const p of DESTRUCTIVE) {
              if (p.re.test(cmd)) {
                event.effect = "deny"
                event.message = blockMessage(p, cmd)
                return
              }
            }
          }
        } catch (err) {
          // Never break the permission pipeline from inside a hook.
          console.error("[guard] evaluate hook error:", err)
        }
      })
      console.log("[guard] destructive-command guard active")
    } catch (err) {
      console.error("[guard] failed to register permission hook:", err)
    }
  },
})
