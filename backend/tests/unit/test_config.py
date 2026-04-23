from app.config import Settings


def test_settings_has_recommendation_thresholds(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://test/test")
    s = Settings()
    assert s.rating_threshold == 3.8
    assert s.ratings_count_threshold == 20


def test_settings_thresholds_can_be_overridden(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://test/test")
    monkeypatch.setenv("RATING_THRESHOLD", "4.0")
    monkeypatch.setenv("RATINGS_COUNT_THRESHOLD", "50")
    s = Settings()
    assert s.rating_threshold == 4.0
    assert s.ratings_count_threshold == 50
