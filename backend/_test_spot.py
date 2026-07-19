import asyncio
import httpx

async def test_spot_explanation():
    """测试景点讲解响应速度"""
    url = "http://localhost:8000/api/chat/stream"
    payload = {
        "query": "介绍一下九龙灌浴",
        "session_id": "test-spot-001",
        "selection": {
            "mode": "attraction",
            "attraction_id": "attraction_001"
        }
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        async with client.stream("POST", url, json=payload) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if '"type":"done"' in data:
                        print(f"收到完成事件: {data[:200]}")
                        break

asyncio.run(test_spot_explanation())
