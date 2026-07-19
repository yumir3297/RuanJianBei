import asyncio, sys
sys.path.insert(0, '.')
from app.db.session import AsyncSessionLocal
from sqlalchemy import text

async def main():
    async with AsyncSessionLocal() as s:
        result = await s.execute(
            text("""
            SELECT id, raw_query, hit_level, latency_ms,
                   LENGTH(answer) as answer_len,
                   created_at
            FROM chat_logs
            WHERE hit_level LIKE 'faq%'
            ORDER BY id DESC LIMIT 5
            """)
        )
        for row in result:
            print(f"ID={row[0]} | hit={row[2]} | lat={row[3]}ms | answer_len={row[4]} | {row[5]}")
            print(f"  query: {repr(row[1])}")
            print()

asyncio.run(main())
