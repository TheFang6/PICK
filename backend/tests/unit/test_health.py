from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

with patch("app.config.Settings", return_value=MagicMock(database_url="sqlite:///:memory:", google_maps_api_key="", debug=False)):
    with patch("app.database.create_engine"):
        from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
