from fastapi import FastAPI, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import os

from database import engine, get_db, Base
from models import SensorRecord, SensorPayload, SensorResponse

# Créer les tables au démarrage
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Cloud API : Projet Edge Computing",
    description="Reçoit, stocke et expose les données des capteurs IoT depuis le nœud Edge.",
    version="1.0.0"
)

# Clé API simple pour authentifier le Microservice C
API_KEY = os.getenv("API_KEY", "edge-secret-key-2026")


def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Clé API invalide")
    return x_api_key


# ── POST /data ─────────────────────────────────────────────────────────────
# Reçoit un paquet JSON du Microservice C et l'écrit en base

@app.post("/data", response_model=SensorResponse, status_code=201)
def receive_data(
    payload: SensorPayload,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    record = SensorRecord(
        device_id    = payload.device_id,
        timestamp    = payload.timestamp,
        temperature  = payload.temperature,
        humidity     = payload.humidity,
        pressure     = payload.pressure,
        voltage      = payload.voltage,
        current      = payload.current,
        acceleration = payload.acceleration.dict(),
        gyroscope    = payload.gyroscope.dict(),
        gps          = payload.gps.dict()
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


# ── GET /data ──────────────────────────────────────────────────────────────
# Expose l'historique pour le Dashboard
# Paramètres optionnels : limit, device_id, depuis (date ISO)

@app.get("/data", response_model=List[SensorResponse])
def get_data(
    limit:     int      = 100,
    device_id: Optional[str]      = None,
    since:     Optional[datetime] = None,
    db:        Session  = Depends(get_db),
    _:         str      = Depends(verify_api_key)
):
    query = db.query(SensorRecord)

    if device_id:
        query = query.filter(SensorRecord.device_id == device_id)
    if since:
        query = query.filter(SensorRecord.timestamp >= since)

    return query.order_by(SensorRecord.timestamp.desc()).limit(limit).all()


# ── GET /health ────────────────────────────────────────────────────────────
# Vérifie que l'API est vivante (utilisé par K3s pour les liveness probes)

@app.get("/health")
def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}