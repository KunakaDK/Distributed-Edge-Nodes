import requests
import json
import time

BASE_URL = "http://localhost:8001"

def afficher(titre, reponse):
    print(f"\n{'='*55}")
    print(f"  {titre}")
    print(f"{'='*55}")
    print(json.dumps(reponse.json(), indent=2, ensure_ascii=False))

# Payload de base 
def payload(temperature=25.0, humidity=60.0, pressure=1013.0,
            voltage=3.3, current=0.5, device_id="edge-node-01"):
    return {
        "device_id":    device_id,
        "timestamp":    "2026-05-05T14:32:01.123Z",
        "temperature":  temperature,
        "humidity":     humidity,
        "pressure":     pressure,
        "acceleration": {"x": 0.12, "y": -0.03, "z": 9.81},
        "gyroscope":    {"x": 0.001, "y": 0.002, "z": -0.001},
        "voltage":      voltage,
        "current":      current,
        "gps":          {"lat": 35.5765, "lon": -5.3682}
    }

# ── Test 1 : Health check ─────────────────────────────────────────────────
print("\n💚 Test 1 : Health check")
r = requests.get(f"{BASE_URL}/health")
afficher("GET /health", r)

# ── Test 2 : Donnée normale (aucune alerte attendue) ──────────────────────
print("\n🟢 Test 2 : Données normales (25°C, 60%, 1013 hPa)")
r = requests.post(f"{BASE_URL}/traiter", json=payload())
afficher("POST /traiter → normale", r)
assert r.json()["alertes_emises"] == 0, "Aucune alerte attendue"

# ── Test 3 : Température trop élevée (> 30°C) ────────────────────────────
print("\n🔴 Test 3 : Température trop élevée (35°C)")
r = requests.post(f"{BASE_URL}/traiter", json=payload(temperature=35.0))
afficher("POST /traiter → alerte température haute", r)
assert r.json()["alertes_emises"] >= 1, "Alerte température attendue"

# ── Test 4 : Température trop basse (< 10°C) ─────────────────────────────
print("\n🔵 Test 4 : Température trop basse (5°C)")
r = requests.post(f"{BASE_URL}/traiter", json=payload(temperature=5.0))
afficher("POST /traiter → alerte température basse", r)
assert r.json()["alertes_emises"] >= 1, "Alerte température attendue"

# ── Test 5 : Humidité trop élevée (> 85%) ────────────────────────────────
print("\n🔴 Test 5 : Humidité trop élevée (90%)")
r = requests.post(f"{BASE_URL}/traiter", json=payload(humidity=90.0))
afficher("POST /traiter → alerte humidité haute", r)
assert r.json()["alertes_emises"] >= 1, "Alerte humidité attendue"

# ── Test 6 : Voltage trop bas (< 2.5V) ───────────────────────────────────
print("\n🔵 Test 6 : Voltage trop bas (2.0V)")
r = requests.post(f"{BASE_URL}/traiter", json=payload(voltage=2.0))
afficher("POST /traiter → alerte voltage basse", r)
assert r.json()["alertes_emises"] >= 1, "Alerte voltage attendue"

# ── Test 7 : Plusieurs alertes simultanées ────────────────────────────────
print("\n🚨 Test 7 : Plusieurs alertes simultanées")
r = requests.post(f"{BASE_URL}/traiter", json=payload(
    temperature=35.0, humidity=90.0, voltage=2.0
))
afficher("POST /traiter → alertes multiples", r)
assert r.json()["alertes_emises"] >= 3, "3 alertes attendues"

# ── Test 8 : Simulation agrégation (envoyer 5 mesures puis demander agrégat)
print("\n📊 Test 8 : Agrégation (5 mesures puis GET /agregat)")
temps = [22.0, 24.5, 23.0, 25.5, 21.0]
for i, t in enumerate(temps):
    requests.post(f"{BASE_URL}/traiter", json=payload(temperature=t))
    print(f"  Mesure {i+1} envoyée : {t}°C")

r = requests.get(f"{BASE_URL}/agregat")
afficher("GET /agregat → moyenne calculée", r)
agregat = r.json()["agregat"]
moyenne_attendue = round(sum(temps) / len(temps), 2)
print(f"\n  Moyenne température attendue : {moyenne_attendue}°C")
print(f"  Moyenne retournée           : {agregat['temperature']}°C")
assert agregat["temperature"] == moyenne_attendue, "Moyenne incorrecte"

# ── Test 9 : Buffer vide après agrégat ────────────────────────────────────
print("\n🗑️  Test 9 : Buffer vide après GET /agregat")
r = requests.get(f"{BASE_URL}/agregat")
afficher("GET /agregat → buffer vide", r)
assert r.json()["statut"] == "vide", "Buffer devrait être vide"

# ── Test 10 : Consulter toutes les alertes générées ───────────────────────
print("\n🚨 Test 10 : Toutes les alertes générées")
r = requests.get(f"{BASE_URL}/alertes")
afficher("GET /alertes", r)

# ── Test 11 : Mesure de latence (doit être < 50 ms) ──────────────────────
print("\n⚡ Test 11 : Latence du traitement Edge")
debut = time.time()
requests.post(f"{BASE_URL}/traiter", json=payload(temperature=35.0))
latence_ms = (time.time() - debut) * 1000
print(f"\n  Latence mesurée : {latence_ms:.2f} ms")
print(f"  Objectif        : < 50 ms (réseau local)")
if latence_ms < 50:
    print("  ✅ Objectif atteint")
else:
    print("  ⚠️  Latence élevée -- vérifier le réseau")

print("\n✅ Tous les tests sont terminés !\n")
