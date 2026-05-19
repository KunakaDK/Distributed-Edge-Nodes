# test_microservice_c.py
import requests, json

CLOUD_URL = "https://cloudserver-g09.southafricanorth.cloudapp.azure.com"
API_KEY   = "edge-secret-key-2026"

def test_health_cloud():
    """Test 1 : L'API Cloud répond"""
    r = requests.get(f"{CLOUD_URL}/health", timeout=10)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    print("[OK] API Cloud health check")

def test_post_data():
    """Test 2 : Envoi d'un payload de test"""
    payload = {
        "device_id":   "edge-node-01",
        "timestamp":   "2026-05-06T10:00:00.000Z",
        "temperature": 25.5,
        "humidity":    60.0,
        "pressure":    1013.0,
        "acceleration": {"x": 0.1, "y": -0.02, "z": 9.81},
        "gyroscope":    {"x": 0.001, "y": 0.001, "z": -0.001},
        "voltage":     3.3,
        "current":     0.5,
        "gps":         {"lat": 35.5765, "lon": -5.3682}
    }
    r = requests.post(
        f"{CLOUD_URL}/data",
        json=payload,
        headers={"x-api-key": API_KEY, "Content-Type": "application/json"},
        timeout=10
    )
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    print(f"[OK] POST /data – id={data['id']}")

def test_get_data():
    """Test 3 : Lecture de l'historique"""
    r = requests.get(
        f"{CLOUD_URL}/data",
        params={"limit": 5, "device_id": "edge-node-01"},
        headers={"x-api-key": API_KEY},
        timeout=10
    )
    assert r.status_code == 200
    data = r.json()
    print(f"[OK] GET /data – {len(data)} enregistrements retournés")

if __name__ == "__main__":
    test_health_cloud()
    test_post_data()
    test_get_data()
    print("\\n=== Tous les tests passés ===")
