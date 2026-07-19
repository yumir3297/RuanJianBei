"""重建 RAG 向量索引（ChromaDB），基于最新数据库内容"""
import asyncio
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s")

async def rebuild():
    from pathlib import Path
    from app.core.config import get_settings
    from app.db.session import AsyncSessionLocal
    from app.api.chat import get_cached_embedder
    from app.repositories.knowledge_chunk import KnowledgeChunkRepository
    from app.services.rag.index_builder import RAGIndexBuilder
    from app.services.rag.vector_store import ChromaVectorStore

    settings = get_settings()
    print(">>> 加载 embedding 模型...")
    embedder = get_cached_embedder(settings.embedding_model_name, str(settings.model_cache_root))
    print(">>> 加载向量存储...")
    vector_store = ChromaVectorStore(
        settings.chroma_persist_root,
        settings.rag_collection_name,
    )
    print(">>> 从数据库读取知识分块...")
    async with AsyncSessionLocal() as session:
        chunk_repo = KnowledgeChunkRepository(session)
        chunks = await chunk_repo.list_all()
        print(f"   共 {len(chunks)} 个分块")

        print(">>> 开始构建向量索引（可能需要几分钟）...")
        builder = RAGIndexBuilder(
            chunk_repository=chunk_repo,
            embedder=embedder,
            vector_store=vector_store,
            batch_size=settings.rag_index_batch_size,
        )
        report = await builder.build()
        print(f">>> 向量索引构建完成！已索引 {report.indexed_chunks}/{report.total_chunks} 个分块")
        print(f"    耗时: {report.duration_ms}ms")

asyncio.run(rebuild())
