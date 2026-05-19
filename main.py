from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime, timezone
from collections import deque
from typing import Optional
import statistics
import uvicorn

app = FastAPI(title="Microservice B - Traitement Edge")

# ── Schéma  ───────────────────────────────────

class Vec3(BaseModel):
    x: float
    y: float
    z: float

class GPS(BaseModel):
    lat: float
    lon: float

class DonneesBrutes(BaseModel):
    device_id:    str
    timestamp:    str
    temperature:  float
    humidity:     float
    pressure:     float
    acceleration: Vec3
    gyroscope:    Vec3
    voltage:      float
    current:      float
    gps:          GPS

# ── Seuils d'alerte  ───────────────────────

SEUILS = {
    "temperature": {"min": 10.0,  "max": 30.0},
    "humidity":    {"min": 20.0,  "max": 85.0},
    "pressure":    {"min": 950.0, "max": 1050.0},
    "voltage":     {"min": 2.5,   "max": 5.5},
    "current":     {"min": 0.0,   "max": 3.0},
}

# ── Stockage en mémoire ───────────────────────────────────────────────────
# Buffer pour agrégation (5 minutes = 300 entrées à 1/s)

buffer:   deque = deque(maxlen=300)   # données brutes en attente d'agrégation
alertes:  list  = []                  # alertes générées
agregats: list  = []                  # moyennes calculées toutes les 5 minutes

# ── Logique de filtrage ───────────────────────────────────────────────────

def detecter_alertes(donnee: DonneesBrutes) -> list:
    """Vérifie chaque capteur contre les seuils. Retourne la liste des alertes."""
    result = []
    champs = {
        "temperature": donnee.temperature,
        "humidity":    donnee.humidity,
        "pressure":    donnee.pressure,
        "voltage":     donnee.voltage,
        "current":     donnee.current,
    }
    for champ, valeur in champs.items():
        seuil = SEUILS[champ]
        if valeur > seuil["max"]:
            result.append({
                "type":      "ALERTE_HAUTE",
                "capteur":   champ,
                "device_id": donnee.device_id,
                "valeur":    valeur,
                "seuil_max": seuil["max"],
                "message":   f"{champ} trop élevé : {valeur} (max {seuil['max']})",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
        elif valeur < seuil["min"]:
            result.append({
                "type":      "ALERTE_BASSE",
                "capteur":   champ,
                "device_id": donnee.device_id,
                "valeur":    valeur,
                "seuil_min": seuil["min"],
                "message":   f"{champ} trop bas : {valeur} (min {seuil['min']})",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
    return result


def calculer_agregat() -> Optional[dict]:
    """
    Calcule la moyenne de toutes les valeurs dans le buffer.
    Appelé toutes les 5 minutes par le Microservice C via GET /agregat.
    Vide le buffer après calcul.
    """
    if not buffer:
        return None

    snap = list(buffer)
    buffer.clear()

    agregat = {
        "device_id":   snap[-1]["device_id"],
        "timestamp":   datetime.now(timezone.utc).isoformat(),
        "nb_mesures":  len(snap),
        "temperature": round(statistics.mean(d["temperature"] for d in snap), 2),
        "humidity":    round(statistics.mean(d["humidity"]    for d in snap), 2),
        "pressure":    round(statistics.mean(d["pressure"]    for d in snap), 2),
        "voltage":     round(statistics.mean(d["voltage"]     for d in snap), 2),
        "current":     round(statistics.mean(d["current"]     for d in snap), 2),
        "acceleration": {
            "x": round(statistics.mean(d["acceleration"]["x"] for d in snap), 4),
            "y": round(statistics.mean(d["acceleration"]["y"] for d in snap), 4),
            "z": round(statistics.mean(d["acceleration"]["z"] for d in snap), 4),
        },
        "gyroscope": {
            "x": round(statistics.mean(d["gyroscope"]["x"] for d in snap), 4),
            "y": round(statistics.mean(d["gyroscope"]["y"] for d in snap), 4),
            "z": round(statistics.mean(d["gyroscope"]["z"] for d in snap), 4),
        },
        "gps": {
            "lat": round(statistics.mean(d["gps"]["lat"] for d in snap), 6),
            "lon": round(statistics.mean(d["gps"]["lon"] for d in snap), 6),
        },
    }
    agregats.append(agregat)
    return agregat

# ── Endpoints ─────────────────────────────────────────────────────────────

@app.post("/traiter")
def recevoir(donnee: DonneesBrutes):
    """
    Reçoit une donnée brute du Microservice A.
    - Détecte les alertes immédiatement (< 10 ms, sans Internet)
    - Stocke dans le buffer pour agrégation
    """
    # 1. Détection alertes (chemin rapide, local)
    nouvelles_alertes = detecter_alertes(donnee)
    for a in nouvelles_alertes:
        alertes.append(a)
        print(f"[ALERTE] {a['message']}")

    # 2. Mise en buffer pour agrégation
    buffer.append({
        "device_id":   donnee.device_id,
        "timestamp":   donnee.timestamp,
        "temperature": donnee.temperature,
        "humidity":    donnee.humidity,
        "pressure":    donnee.pressure,
        "voltage":     donnee.voltage,
        "current":     donnee.current,
        "acceleration": donnee.acceleration.dict(),
        "gyroscope":    donnee.gyroscope.dict(),
        "gps":          donnee.gps.dict(),
    })

    return {
        "statut":           "traitée",
        "alertes_emises":   len(nouvelles_alertes),
        "alertes":          nouvelles_alertes,
        "buffer_taille":    len(buffer),
    }


@app.get("/agregat")
def get_agregat():
    """
    Appelé par le Microservice C toutes les 5 minutes.
    Retourne la moyenne du buffer et le vide.
    """
    agregat = calculer_agregat()
    if agregat is None:
        return {"statut": "vide", "message": "Aucune donnée dans le buffer"}
    return {"statut": "ok", "agregat": agregat}


@app.get("/alertes")
def get_alertes(limit: int = 50):
    """Retourne les dernières alertes."""
    return {
        "total":   len(alertes),
        "alertes": alertes[-limit:],
    }


@app.get("/health")
def health():
    return {
        "statut":          "ok",
        "buffer_taille":   len(buffer),
        "total_alertes":   len(alertes),
        "total_agregats":  len(agregats),
        "timestamp":       datetime.now(timezone.utc).isoformat(),
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
