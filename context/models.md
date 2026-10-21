# Models (benched 2026-10-21, RTX 4060 Ti 16GB + 32GB RAM)

| alias | base | size | eval t/s @16k ctx | role |
|---|---|---|---|---|
| glmflash-abl | huihui_ai/glm-4.7-flash-abliterated:q4_K_S | 17GB (~2.5GB offload) | ~53 | workers (explorer/coder/analyst) |
| gptoss-abl | huihui_ai/gpt-oss-abliterated:20b | 13GB, no offload | ~63 | orchestrator (fast prefill ~4700 t/s) |
| qwen38-abl | huihui_ai/Qwen3.8-abliterated:27b | 18GB (~3GB offload) | ~14-22 | deep escalation only |

## Quirks

- gpt-oss-abliterated: `think:false` does NOT disable thinking; thinking can
  loop and exhaust num_predict leaving empty content. Always `think:"low"`.
- glm-4.7-flash: respects think modes; one think-overflow seen on think:true.
- num_ctx 32768 forces KV offload on gpt-oss (-28% speed). 16384 = sweet spot.
- Devin cloud models (optional): swe-2-high (strong), swe-2-medium (cheap),
  swe-2-max (hardest). Provided by `opencode-devin` npm plugin.

## Untested candidates

- huihui_ai/devstral-abliterated:24b (agentic coding, 14GB)
- huihui_ai/huihui-moe-abliterated:23b (MoE, 14GB)
- richardyoung/qwen3.6-27b-abliterated:IQ3_M (Heretic, 12GB)
