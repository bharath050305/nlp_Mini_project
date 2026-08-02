from config import Settings


def test_default_llm_provider_is_mock():
    """The app must run with zero API keys out of the box."""
    s = Settings(_env_file=None)
    assert s.llm_provider == "mock"


def test_directories_are_created(tmp_path):
    s = Settings(
        _env_file=None,
        database_path=tmp_path / "db" / "mediagent.db",
        upload_dir=tmp_path / "uploads",
        reports_dir=tmp_path / "reports",
        data_dir=tmp_path / "data",
        logs_dir=tmp_path / "logs",
    )
    s.ensure_directories()
    assert s.upload_dir.exists()
    assert s.reports_dir.exists()
    assert s.database_path.parent.exists()
