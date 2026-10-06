from copy import deepcopy

import pytest

from openrouter_image_mcp.prompt_cache import cache_usage, configure_cache


def test_session_is_stable_per_chat_and_no_private_identity_is_sent():
    payload = {"model": "openai/gpt-test", "input": [{"role": "user", "content": "hello"}]}
    configure_cache(payload, "opaque-chat-a")
    assert payload["session_id"] == "sidecar-opaque-chat-a"
    assert payload["input"][0]["content"] == "hello"
    assert "prompt_cache_options" not in payload


def test_gemini_marks_only_large_stable_opening_context_without_mutating_history():
    history = [{"role": "user", "content": "reference " * 2000}, {"role": "assistant", "content": "OK"}]
    original = deepcopy(history)
    payload = {"model": "google/gemini-test", "input": history + [{"role": "user", "content": "follow up"}]}
    configure_cache(payload, "a")
    block = payload["input"][0]["content"][0]
    assert block == {"type": "input_text", "text": original[0]["content"], "prompt_cache_breakpoint": {"mode": "explicit"}}
    assert payload["input"][2]["content"] == "follow up"
    assert history == original


@pytest.mark.parametrize("model", ["google/gemini-test", "qwen/qwen-test", "openai/gpt-test", "x-ai/grok-test"])
def test_short_one_off_requests_do_not_force_paid_explicit_cache(model):
    payload = {"model": model, "input": [{"role": "user", "content": "hello"}]}
    configure_cache(payload, "a")
    assert payload["input"][0]["content"] == "hello"
    assert "prompt_cache_options" not in payload


def test_usage_distinguishes_unreported_writes_from_zero_and_rejects_invalid_values():
    assert cache_usage({"input_tokens": 100, "input_tokens_details": {"cached_tokens": 80}}) == {"input_tokens": 100, "cached_tokens": 80, "cache_write_tokens": None}
    assert cache_usage({"prompt_tokens": 100, "prompt_tokens_details": {"cached_tokens": 80, "cache_write_tokens": 0}})["cache_write_tokens"] == 0
    assert cache_usage({"input_tokens": True, "input_tokens_details": {"cached_tokens": -1, "cache_write_tokens": "secret"}}) == {"input_tokens": None, "cached_tokens": None, "cache_write_tokens": None}
