import asyncio

from eval.scripts.deepseek_smoke import (
    build_chat_completions_url,
    iter_sse_data,
    parse_stream_payload,
)


def test_build_chat_completions_url_avoids_duplicate_path() -> None:
    assert build_chat_completions_url("https://api.deepseek.com") == (
        "https://api.deepseek.com/chat/completions"
    )
    assert build_chat_completions_url("https://api.deepseek.com/chat/completions/") == (
        "https://api.deepseek.com/chat/completions"
    )


def test_parse_stream_payload_handles_content_usage_and_done() -> None:
    content = parse_stream_payload(
        '{"choices":[{"delta":{"content":"连接"},"finish_reason":null}]}'
    )
    usage = parse_stream_payload(
        '{"choices":[],"usage":{"prompt_tokens":10,"completion_tokens":2,"total_tokens":12}}'
    )

    assert content["choices"][0]["delta"]["content"] == "连接"
    assert usage["usage"]["total_tokens"] == 12
    assert parse_stream_payload("[DONE]") is None


def test_iter_sse_data_ignores_non_data_lines() -> None:
    async def lines():
        for line in ("event: message", "", "data: {\"ok\":true}", "data: [DONE]"):
            yield line

    async def collect():
        return [payload async for payload in iter_sse_data(lines())]

    assert asyncio.run(collect()) == ['{"ok":true}', "[DONE]"]
