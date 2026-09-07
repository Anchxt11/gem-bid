from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_create_and_get_tender():
    response = client.post("/tenders/", json={"title": "Road Repair", "status": "open"})
    assert response.status_code == 200
    tender_id = response.json()["id"]

    response = client.get(f"/tenders/{tender_id}")
    assert response.status_code == 200
    assert response.json()["title"] == "Road Repair"