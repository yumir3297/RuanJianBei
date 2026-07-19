import asyncio, httpx, json, time

async def test():
    url = "http://localhost:8000/api/chat/stream"
    body = {
        "query": "帮我推荐灵山游览路线，避开人流",
        "session_id": f"test-debug-{int(time.time())}",
        "input_mode": "text",
        "text_only": False,
    }
    print(f"=== Sending ===", flush=True)
    async with httpx.AsyncClient(timeout=40.0) as client:
        async with client.stream("POST", url, json=body) as resp:
            full_text = []
            async for line in resp.aiter_lines():
                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    if "text" in data:
                        full_text.append(data["text"])
                    if "hit_level" in data:
                        print(f">>> HIT_LEVEL: {data['hit_level']}", flush=True)
            print(f"=== Answer ({len(''.join(full_text))} chars) ===", flush=True)

asyncio.run(test())
