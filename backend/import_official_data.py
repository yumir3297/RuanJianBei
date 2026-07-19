"""一键导入官方赛题数据到数据库"""
import asyncio
import sys

# 先执行 alembic 确保表存在
print(">>> 确保数据库表结构最新...")
from alembic.config import Config as AlembicConfig
from alembic import command as alembic_command
from pathlib import Path
import os

os.chdir(Path(__file__).parent)
cfg = AlembicConfig("alembic.ini")
alembic_command.upgrade(cfg, "head")
print(">>> 表结构确认完成")

# 导入数据
async def import_data():
    from app.core.config import get_settings
    from app.db.session import AsyncSessionLocal
    from app.services.data_import.importer import ProcessedDataImporter

    settings = get_settings()
    if not settings.processed_data_available:
        print(">>> 未找到已处理数据文件，正在检查数据目录...")
        missing = []
        for f in [settings.knowledge_entries_file, settings.guide_sections_file,
                   settings.faq_file, settings.route_recommendations_file,
                   settings.visitor_behavior_summary_file]:
            if not f.exists():
                missing.append(str(f))
        if missing:
            print(">>> 找不到以下文件：")
            for f in missing:
                print(f"    {f}")
            return
        print(">>> 所有数据文件存在")

    async with AsyncSessionLocal() as session:
        importer = ProcessedDataImporter(session, settings)
        report = await importer.sync()
        print(f">>> 导入完成！")
        print(f"    知识条目: {report.knowledge_imported}")
        print(f"    知识分块: {report.chunk_imported}")
        print(f"    FAQ条目:  {report.faq_imported}")
        print(f"    路线模板: {report.route_imported}")
        print(f"    行为摘要: {report.behavior_imported}")
        print(f"    耗时:     {report.duration_ms}ms")

asyncio.run(import_data())
print(">>> 数据导入完毕")
