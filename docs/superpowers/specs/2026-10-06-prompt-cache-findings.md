# Prompt caching: measured findings and local policy

OpenRouter Sidecar uses the Responses API, sends local conversation history,
and keeps `store: false`. Provider prompt caching reuses processed prefixes;
it does not replace conversation history with a server session.

## Live experiment, 2026-10-06

Three sequential turns per model, synthetic reference material only, one stable
session identifier per model. No containers or tools in this provider-level probe.
24 requests cost $0.094047853. The opening prompt contained roughly 13,000-15,000
visible reference tokens; provider-reported counts vary and can include overhead.

| Model | Cached tokens on third turn | Reported cache writes | Result |
| --- | ---: | --- | --- |
| Gemini 3.1 Flash Lite | 0 | 0 | No implicit hit observed |
| GPT 6 Luna Pro | 26,746 | 13,355 first turn; 18 third turn | Hit and writes reported |
| Grok Build 0.1 | 13,504 | Not reported | Hit |
| GLM 5.3 | 13,568 | 0 | Hit |
| Qwen 3.7 Flash | 15,360 | 0 | Hit |
| Kimi K2.7 Code | 13,344 | Not reported | Hit appeared on third turn |
| MiniMax M3 | 14,226 | Not reported | Hit |
| DeepSeek V4 Flash | 13,824 | Not reported | Hit |

A separate three-turn Gemini test used a Responses `input_text` block with
`prompt_cache_breakpoint: {mode: "explicit"}`. It reported 15,338 cache-write
tokens on the first request and 15,338 cached tokens on each request. Subsequent
write counts were zero. Those requests cost $0.0024435166666666666 combined;
the third-turn cost fell from $0.00384175 implicit to $0.00039045 explicit.
Combined cache-probe spend: $0.09649136966666667.

Two additional turns through the actual `AdvisorService`, with its stable assigned
container tool schema and no skill uploads or tool execution, cost $0.003742 and
$0.000540875. The follow-up reported 14,245 cached tokens out of 14,978 input
tokens; cache-write counts were not reported on this path. The temporary local
probe chat was removed. Total caching experiment spend: $0.10077424466666667.

These are observed examples, not guarantees for every model/provider or prompt.
A missing write count means unreported, not zero. First-turn hits may include
provider boilerplate/internal requests, not our unique entire reference prefix.
Catalog minimum prices differed from actual routed provider charges for some
models. Cost estimates cannot serve as a hard provider-enforced cap. The probe
does not retry paid failures and stops when usage cost is missing or uncertain.

## Implemented policy

- Each advisor request sends a stable opaque chat-specific `session_id` for
  best-effort sticky provider routing; this is not an access-control boundary.
- All normal providers keep their default implicit caching behavior.
- Gemini gets one explicit breakpoint on a large, stable opening user context
  (at least 16,384 characters, a heuristic rather than a token guarantee).
  Short prompts do not force storage-billed explicit caching.
- Explicit breakpoints are skipped when transient skill files are attached:
  upload IDs, tool schemas and system file paths change, undermining prefix
  reuse. Implicit caching and session routing remain available.
- Numeric cache reads/writes are normalized internally without retaining raw
  provider metadata. The current result viewer shows total cost, not these counts.
- Existing ownership checks, local history, upload cleanup and disabled sandbox
  network policy remain authoritative. There is no cross-student cache/file API.

Avoid padding prompts to meet cache minima: extra input and storage can outweigh
savings. Cache affinity expires independently of local saved chats. Provider
cache retention is not the same as container file retention.

Source: [OpenRouter prompt caching documentation](https://openrouter.ai/docs/guides/best-practices/prompt-caching).
Machine-readable observations: `experiments/cache-probe-results.json` and
`experiments/cache-probe-explicit-results.json`. Reusable probe:
`experiments/cache_probe.py`; default invocation only reads catalog/pricing.

## Verification

127 targeted Python tests and the complete offline suite (647 passed, one skipped,
four live tests deselected) passed. Provider probes exercise the real Responses API;
the two integration turns also exercise the production advisor request builder,
including its container reference. They do not invoke a shell or upload skills.
