import asyncio

import httpx

from app.core.config import Settings
from app.services.llm.openai_compatible import OpenAICompatibleLLMService
from app.services.llm.prompt_builder import EvidencePromptBuilder
from app.services.rag.base import RetrievedDocument


def documents() -> list[RetrievedDocument]:
    return [
        RetrievedDocument(
            title="灵山大佛",
            content="灵山大佛高88米，位于祥符禅寺北侧。",
            snippet="灵山大佛高88米。",
            source="官方景点资料.docx",
            score=0.98,
        ),
        RetrievedDocument(
            title="游览提示",
            content="请根据现场导览标识有序参观。",
            source="官方游览指南.docx",
            score=0.8,
        ),
    ]


def deepseek_settings(**overrides) -> Settings:
    values = {
        "llm_provider": "deepseek",
        "llm_api_key": "test-key",
        "llm_base_url": "https://api.deepseek.com",
        "llm_model": "deepseek-v4-pro",
        "llm_first_token_timeout_seconds": 1,
        "llm_read_timeout_seconds": 1,
        "llm_total_timeout_seconds": 3,
    }
    values.update(overrides)
    return Settings(**values)


def test_prompt_builder_numbers_and_limits_evidence() -> None:
    builder = EvidencePromptBuilder(max_documents=1, max_chars_per_document=12)
    prompt = builder.build("大佛有多高", documents())

    assert len(prompt.evidence) == 1
    assert prompt.evidence[0].evidence_id == "证据1"
    assert len(prompt.evidence[0].content) == 12
    assert "[证据1]" in prompt.messages[1]["content"]
    assert "官方景点资料.docx" in prompt.messages[1]["content"]
    assert "【回答依据】" in prompt.messages[0]["content"]
    assert "清岚" in prompt.messages[0]["content"]


def test_service_streams_content_usage_and_finish() -> None:
    sse = "\n".join(
        [
            'data: {"choices":[{"delta":{"content":"高88米"},"finish_reason":null}]}',
            "",
            'data: {"choices":[{"delta":{},"finish_reason":"stop"}]}',
            "",
            'data: {"choices":[],"usage":{"prompt_tokens":20,"completion_tokens":4,"total_tokens":24,"prompt_tokens_details":{"cached_tokens":3}}}',
            "",
            "data: [DONE]",
            "",
        ]
    )

    async def run():
        async def handler(request: httpx.Request) -> httpx.Response:
            assert request.url == "https://api.deepseek.com/chat/completions"
            assert request.headers["authorization"] == "Bearer test-key"
            payload = __import__("json").loads(request.content)
            assert payload["stream_options"] == {"include_usage": True}
            assert "[证据1]" in payload["messages"][1]["content"]
            return httpx.Response(200, text=sse, headers={"Content-Type": "text/event-stream"})

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            service = OpenAICompatibleLLMService(deepseek_settings(), client=client)
            return [event async for event in service.stream_generate("大佛有多高", documents())]

    events = asyncio.run(run())

    assert [event.type for event in events] == ["content", "finish", "usage"]
    assert events[0].text == "高88米"
    assert events[1].finish_reason == "stop"
    assert events[2].usage.total_tokens == 24
    assert events[2].usage.cached_tokens == 3


def test_service_falls_back_to_numbered_evidence_on_http_error() -> None:
    async def run():
        async def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(401, json={"error": {"message": "invalid key"}})

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            service = OpenAICompatibleLLMService(deepseek_settings(), client=client)
            return [event async for event in service.stream_generate("大佛有多高", documents())]

    events = asyncio.run(run())

    assert events[0].type == "content"
    assert "AI讲解服务暂时不可用" in events[0].text
    assert "[证据1]" in events[0].text
    assert "灵山大佛高88米" in events[0].text
    assert events[-1].finish_reason == "fallback_http_401"


def test_service_with_missing_configuration_does_not_make_request() -> None:
    settings = deepseek_settings(llm_api_key="")
    service = OpenAICompatibleLLMService(settings)

    async def run():
        return [event async for event in service.stream_generate("大佛有多高", documents())]

    events = asyncio.run(run())

    assert "[证据1]" in events[0].text
    assert events[-1].finish_reason == "fallback_configuration_error"


def test_service_does_not_append_full_fallback_after_partial_stream_failure() -> None:
    class BrokenStream(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield (
                'data: {"choices":[{"delta":{"content":"部分回答"},"finish_reason":null}]}\n\n'
            ).encode("utf-8")
            raise httpx.ReadError("stream interrupted")

    async def run():
        async def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                stream=BrokenStream(),
                headers={"Content-Type": "text/event-stream"},
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            service = OpenAICompatibleLLMService(deepseek_settings(), client=client)
            return [event async for event in service.stream_generate("大佛有多高", documents())]

    events = asyncio.run(run())
    answer = "".join(event.text for event in events if event.type == "content")

    assert answer.startswith("部分回答")
    assert "连接中断" in answer
    assert "先为你展示检索到的官方资料" not in answer
    assert events[-1].finish_reason == "interrupted_network"
