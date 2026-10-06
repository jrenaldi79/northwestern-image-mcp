"""Best-effort cache hints; local transcripts remain authoritative.

Session identifiers are routing hints, never authentication or ownership controls.
Do not cache dynamic skill-file prefixes explicitly: uploads change tool schemas
and file paths, and their content must remain fresh for each request.
"""

from copy import deepcopy


def configure_cache(payload: dict, chat_id: str, *, allow_explicit: bool = True) -> None:
    payload["session_id"] = "sidecar-" + chat_id
    if not allow_explicit or not payload["model"].startswith("google/gemini"):
        return
    items = payload.get("input", [])
    if not items or items[0].get("role") != "user":
        return
    text = items[0].get("content")
    # Conservative size heuristic, not a tokenizer. Provider minimums still apply.
    # A stable opening context avoids creating a new storage-billed cache each turn.
    if not isinstance(text, str) or len(text) < 16_384:
        return
    payload["input"] = deepcopy(items)
    payload["input"][0]["content"] = [{
        "type": "input_text", "text": text,
        "prompt_cache_breakpoint": {"mode": "explicit"},
    }]


def cache_usage(usage) -> dict:
    """Keep only numeric usage fields; missing write metrics are not zero writes."""
    if not isinstance(usage, dict):
        usage = {}
    details = usage.get("input_tokens_details", usage.get("prompt_tokens_details"))
    if not isinstance(details, dict):
        details = {}

    def count(value):
        return value if type(value) is int and value >= 0 else None

    return {
        "input_tokens": count(usage.get("input_tokens", usage.get("prompt_tokens"))),
        "cached_tokens": count(details.get("cached_tokens")),
        "cache_write_tokens": count(details.get("cache_write_tokens")),
    }
