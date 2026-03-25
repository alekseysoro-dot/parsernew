# tests/scraper/test_scheduler.py
import os
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")


def test_update_all_prices_runs_without_crash(mocker):
    """Scheduler doesn't crash on empty DB."""
    from scraper import scheduler

    mocker.patch.object(scheduler, "fetch_product_info", return_value=None)
    mocker.patch.object(scheduler, "notify_if_needed")

    # Mock Session so no real DB needed
    mock_session = mocker.MagicMock()
    mock_session.return_value.__enter__ = lambda s: mock_session.return_value
    mock_session.return_value.query.return_value.all.return_value = []
    mocker.patch.object(scheduler, "Session", mock_session)

    scheduler.update_all_prices()  # should not raise


def test_cleanup_old_prices_runs_without_crash(mocker):
    from scraper import scheduler

    mock_session = mocker.MagicMock()
    mock_session.return_value.query.return_value.filter.return_value.delete.return_value = 0
    mocker.patch.object(scheduler, "Session", mock_session)

    scheduler.cleanup_old_prices()
