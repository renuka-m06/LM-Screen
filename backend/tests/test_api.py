from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] in ["ok", "starting"]

def test_reports_endpoint():
    payload = {
        "gtin": "8901234567890",
        "issue_category": "Suspicious MRP",
        "description": "MRP overwritten with sticker",
        "location_city": "Delhi"
    }
    response = client.post("/api/v1/reports", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "UNVERIFIED"
    assert "report_id" in data

def test_officer_queue_endpoint():
    response = client.get("/api/v1/officer/queue")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_dashboard_statistics():
    response = client.get("/api/v1/dashboard/statistics")
    assert response.status_code == 200
    data = response.json()
    assert "scans" in data
    assert "citizen_intelligence" in data
