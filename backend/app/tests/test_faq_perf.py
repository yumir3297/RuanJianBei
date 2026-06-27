from time import perf_counter

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.db.base import Base
from app.services.data_import.importer import ProcessedDataImporter
from app.services.qa.faq_matcher import FAQMatcher


def test_faq_load_and_exact_match_performance(tmp_path) -> None:
    db_path = tmp_path / "faq_perf.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    settings = Settings(database_url=f"sqlite:///{db_path}", enable_sample_data=False)

    session = session_local()
    try:
        ProcessedDataImporter(session, settings).sync()

        matcher = FAQMatcher()
        load_ms = matcher.reload(session)

        start = perf_counter()
        result = matcher.match("灵山大佛有多高")
        elapsed_ms = (perf_counter() - start) * 1000

        assert load_ms < 1000
        assert result.is_hit is True
        assert result.level == "exact"
        assert elapsed_ms < 5
    finally:
        session.close()
