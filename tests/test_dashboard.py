from fastapi.testclient import TestClient

from app.dashboard import create_app


def test_dashboard_and_paper_health():
    client = TestClient(create_app())
    assert client.get("/").status_code == 200
    health = client.get("/health").json()
    assert health == {"status": "ok", "trading_mode": "paper"}


def test_radar_api_returns_cited_rows():
    client = TestClient(create_app())
    response = client.post("/api/radar", json={"query": "Find whale trades"})
    assert response.status_code == 200
    rows = response.json()["rows"]
    assert rows and len({signal["source"] for signal in rows[0]["signals"]}) >= 2
