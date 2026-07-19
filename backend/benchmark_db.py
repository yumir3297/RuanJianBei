"""
数据库性能对比评测：SQLite 同步 vs PostgreSQL 异步

用法：
  # 用 SQLite 跑（模拟原始方案）
  python benchmark_db.py --db sqlite

  # 用 PG + async 跑（模拟改造后）
  python benchmark_db.py --db pg

输出：控制台会打印各项指标对比表格，可直接截图放入 PPT。
"""
from __future__ import annotations

import argparse
import asyncio
import time
from dataclasses import dataclass
from datetime import datetime, timezone

# ──────────────────────────────────────────────────────────────
# SQLite 同步方案
# ──────────────────────────────────────────────────────────────
def run_sqlite_bench():
    from sqlalchemy import create_engine, text, Column, Integer, String, DateTime, Float
    from sqlalchemy.orm import DeclarativeBase, Session
    import tempfile, os, threading

    class Base(DeclarativeBase):
        pass

    class ChatLog(Base):
        __tablename__ = "chat_logs"
        id = Column(Integer, primary_key=True)
        session_id = Column(String)
        raw_query = Column(String)
        answer = Column(String)
        latency_ms = Column(Float)
        created_at = Column(DateTime)

    tmpdir = tempfile.mkdtemp()
    db_path = os.path.join(tmpdir, "bench.db")
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)

    results = {}

    # ─── 测试1: 单线程写入 1000 条日志 ───
    start = time.perf_counter()
    with Session(engine) as s:
        for i in range(1000):
            s.add(ChatLog(session_id=f"user_{i%50}", raw_query=f"查询内容_{i}", answer=f"回答_{i}", latency_ms=120.0, created_at=datetime.now(timezone.utc)))
        s.commit()
    results["单线程写入1000条"] = round(time.perf_counter() - start, 2)

    # ─── 测试2: 并发 50 用户写入 ───
    def writer(uid):
        with Session(engine) as s:
            for j in range(20):
                s.add(ChatLog(session_id=f"user_{uid}", raw_query=f"并发查询_{uid}_{j}", answer=f"回答_{uid}_{j}", latency_ms=100.0, created_at=datetime.now(timezone.utc)))
            try:
                s.commit()
            except Exception:
                s.rollback()

    start = time.perf_counter()
    threads = [threading.Thread(target=writer, args=(i,)) for i in range(50)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    results["50并发写入(各20条)"] = round(time.perf_counter() - start, 2)

    # ─── 测试3: 并发读取 ───
    def reader():
        with Session(engine) as s:
            for _ in range(100):
                s.execute(text("SELECT * FROM chat_logs WHERE session_id = 'user_0' ORDER BY created_at DESC LIMIT 10")).fetchall()

    start = time.perf_counter()
    threads = [threading.Thread(target=reader) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    results["20并发读取(各100次)"] = round(time.perf_counter() - start, 2)

    # ─── 测试4: 聚合查询 ───
    start = time.perf_counter()
    with Session(engine) as s:
        for _ in range(50):
            s.execute(text("SELECT session_id, COUNT(*) as cnt FROM chat_logs GROUP BY session_id ORDER BY cnt DESC LIMIT 20")).fetchall()
    results["50次聚合查询"] = round(time.perf_counter() - start, 2)

    # 清理
    engine.dispose()
    for f in os.listdir(tmpdir):
        os.remove(os.path.join(tmpdir, f))
    os.rmdir(tmpdir)

    return "SQLite 同步", results


# ──────────────────────────────────────────────────────────────
# PostgreSQL 异步方案
# ──────────────────────────────────────────────────────────────
async def run_pg_bench():
    from sqlalchemy import text, Column, Integer, String, DateTime, Float
    from sqlalchemy.orm import DeclarativeBase
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

    class Base(DeclarativeBase):
        pass

    class ChatLog(Base):
        __tablename__ = "chat_logs"
        id = Column(Integer, primary_key=True)
        session_id = Column(String)
        raw_query = Column(String)
        answer = Column(String)
        latency_ms = Column(Float)
        created_at = Column(DateTime)

    engine = create_async_engine(
        "postgresql+asyncpg://postgres:postgres@localhost:5432/a5_scenic_guide",
        pool_size=20, max_overflow=10,
    )
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    results = {}

    # ─── 测试1: 单协程写入 1000 条日志 ───
    start = time.perf_counter()
    async with SessionLocal() as s:
        for i in range(1000):
            s.add(ChatLog(session_id=f"user_{i%50}", raw_query=f"查询内容_{i}", answer=f"回答_{i}", latency_ms=120.0, created_at=datetime.now(timezone.utc)))
        await s.commit()
    results["单协程写入1000条"] = round(time.perf_counter() - start, 2)

    # ─── 测试2: 并发 50 用户写入 ───
    async def writer(uid):
        async with SessionLocal() as s:
            for j in range(20):
                s.add(ChatLog(session_id=f"user_{uid}", raw_query=f"并发查询_{uid}_{j}", answer=f"回答_{uid}_{j}", latency_ms=100.0, created_at=datetime.now(timezone.utc)))
            await s.commit()

    start = time.perf_counter()
    await asyncio.gather(*(writer(i) for i in range(50)))
    results["50并发写入(各20条)"] = round(time.perf_counter() - start, 2)

    # ─── 测试3: 并发读取 ───
    async def reader():
        async with SessionLocal() as s:
            for _ in range(100):
                await s.execute(text("SELECT * FROM chat_logs WHERE session_id = 'user_0' ORDER BY created_at DESC LIMIT 10"))

    start = time.perf_counter()
    await asyncio.gather(*(reader() for _ in range(20)))
    results["20并发读取(各100次)"] = round(time.perf_counter() - start, 2)

    # ─── 测试4: 聚合查询 ───
    start = time.perf_counter()
    async with SessionLocal() as s:
        for _ in range(50):
            await s.execute(text("SELECT session_id, COUNT(*) as cnt FROM chat_logs GROUP BY session_id ORDER BY cnt DESC LIMIT 20"))
    results["50次聚合查询"] = round(time.perf_counter() - start, 2)

    # 清理测试表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()
    return "PostgreSQL 异步", results


# ──────────────────────────────────────────────────────────────
# 输出格式化
# ──────────────────────────────────────────────────────────────
def print_table(results: dict[str, tuple[str, dict]], total_width=70):
    """打印对比表格"""
    labels = list(results.values())[0][1].keys()
    border = "─" * total_width

    print(f"\n{border}")
    print(f"{'性能对比评测结果':^{total_width}}")
    print(f"{border}")

    # 表头
    header = f"{'测试场景':<28} "
    for name in results:
        header += f"{name:>18} "
    header += f"{'提速':>8}"
    print(header)
    print(border)

    # 数据行
    for label in labels:
        row = f"{label:<28} "
        vals = []
        for name, data in results.items():
            v = data[label]
            row += f"{v:>14.2f}s  "
            vals.append(v)
        if len(vals) == 2 and vals[0] > 0:
            speedup = vals[0] / vals[1]
            row += f"{speedup:>5.1f}x"
        print(row)

    print(f"{border}\n")


def main():
    parser = argparse.ArgumentParser(description="数据库性能对比评测")
    parser.add_argument("--db", choices=["sqlite", "pg"], required=True, help="选择评测方案")
    args = parser.parse_args()

    if args.db == "sqlite":
        print("\n>>> 运行 SQLite 同步方案评测...")
        label, data = run_sqlite_bench()
        for k, v in data.items():
            print(f"  {k}: {v:.2f}s")
        print("\n[SQLite 评测完成]")
        print("注意：要查看对比表格，需先运行 --db sqlite 保存结果，再运行 --db pg")

    elif args.db == "pg":
        print("\n>>> 运行 PostgreSQL 异步方案评测...")
        try:
            label, data = asyncio.run(run_pg_bench())
            for k, v in data.items():
                print(f"  {k}: {v:.2f}s")
            print("\n[PostgreSQL 评测完成]")
        except Exception as e:
            print(f"\n[错误] PostgreSQL 连接失败: {e}")
            print("请确保 PostgreSQL 已启动，且数据库 a5_scenic_guide 已创建。")
            return

    print("\n提示：将两次评测结果填入下方表格即可做 PPT 对比图：")
    print("""
┌─────────────────────────────────┬─────────────────┬─────────────────┬────────┐
│ 测试场景                        │ SQLite 同步     │ PostgreSQL 异步  │  提速  │
├─────────────────────────────────┼─────────────────┼─────────────────┼────────┤
│ 单线程/协程写入 1000 条         │       ?         │       ?         │   ?x   │
│ 50 并发写入（各 20 条）         │       ?         │       ?         │   ?x   │
│ 20 并发读取（各 100 次）        │       ?         │       ?         │   ?x   │
│ 50 次聚合查询                   │       ?         │       ?         │   ?x   │
└─────────────────────────────────┴─────────────────┴─────────────────┴────────┘
""")


if __name__ == "__main__":
    main()
