import asyncio
from time import perf_counter

from app.core.config import Settings
from app.services.data_import.importer import ProcessedDataImporter
from app.services.qa.faq_matcher import FAQMatcher
from app.tests.async_db import open_test_session


def test_faq_load_and_exact_match_performance(tmp_path) -> None:
    db_path = tmp_path / "faq_perf.db"
    settings = Settings(database_url=f"sqlite:///{db_path}", enable_sample_data=False)

    async def scenario():
        engine, session = await open_test_session(str(db_path))
        try:
            await ProcessedDataImporter(session, settings).sync()

            matcher = FAQMatcher()
            load_ms = await matcher.reload(session)

            start = perf_counter()
            result = matcher.match("灵山大佛有多高")
            elapsed_ms = (perf_counter() - start) * 1000

            assert load_ms < 1000
            assert result.is_hit is True
            assert result.level == "exact"
            assert elapsed_ms < 5
        finally:
            await session.close()
            await engine.dispose()

    asyncio.run(scenario())
