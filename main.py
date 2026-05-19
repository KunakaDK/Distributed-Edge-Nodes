import time, logging, requests
from datetime import datetime, timezone

# ─── Configuration ─────────────────────────────────────────────
CLOUD_URL  = "https://cloudserver-g09.southafricanorth.cloudapp.azure.com"
CLOUD_KEY  = "edge-secret-key-2026"
import os
MSVC_B_URL = os.getenv("MSVC_B_URL", "http://microservice-b-service.edge.svc.cluster.local:8001")   # K3s namespace
# Pour test local avec Docker Compose:
# MSVC_B_URL = "http://microservice-b:8001"

SYNC_INTERVAL   = 5 * 60   # 5 minutes en secondes
MAX_RETRIES     = 5
RETRY_BASE_WAIT = 2         # secondes (backoff exponentiel x2)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S"
)
log = logging.getLogger("microservice-c")

HEADERS_CLOUD = {
    "x-api-key":    CLOUD_KEY,
    "Content-Type": "application/json",
}

# ─── Récupérer l'agrégat depuis Microservice B ─────────────────
def fetch_agregat():
    try:
        r = requests.get(f"{MSVC_B_URL}/agregat", timeout=10)
        r.raise_for_status()
        data = r.json()
        if data.get("statut") == "vide":
            log.info("Buffer vide – rien à envoyer ce cycle.")
            return None
        return data.get("agregat")
    except requests.RequestException as e:
        log.error(f"Erreur récupération agrégat: {e}")
        return None

# ─── Envoyer vers l'API Cloud avec retry exponentiel ──────────
def send_to_cloud(payload: dict) -> bool:
    wait = RETRY_BASE_WAIT
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            log.info(f"Envoi Cloud (tentative {attempt}/{MAX_RETRIES})...")
            start = time.time()
            r = requests.post(
                f"{CLOUD_URL}/data",
                json=payload,
                headers=HEADERS_CLOUD,
                timeout=15,
                # NE PAS mettre verify=False – le certificat est valide
            )
            r.raise_for_status()
            latency = (time.time() - start) * 1000
            log.info(f"Succes ! id={r.json().get('id')} latence={latency:.1f}ms")
            return True
        except requests.HTTPError as e:
            log.error(f"Erreur HTTP {e.response.status_code}: {e}")
            if e.response.status_code in (400, 401, 403):
                log.error("Erreur non-retriable. Abandon.")
                return False
        except requests.RequestException as e:
            log.warning(f"Erreur reseau: {e} – retry dans {wait}s")
        time.sleep(wait)
        wait = min(wait * 2, 120)   # cap à 2 minutes
    log.error("Echec apres tous les retries. Donnee perdue pour ce cycle.")
    return False

# ─── Boucle principale ─────────────────────────────────────────
def main():
    log.info("Microservice C demarre. Intervalle: 5 min.")
    while True:
        cycle_start = time.time()
        log.info("=== Nouveau cycle de synchronisation ===")

        agregat = fetch_agregat()
        if agregat:
            # Assurer que device_id est présent
            if "device_id" not in agregat:
                agregat["device_id"] = "edge-node-01"
            log.info(f"Agregat recu: {agregat.get('nb_mesures',0)} mesures, "
                     f"temp={agregat.get('temperature','N/A')}°C")
            send_to_cloud(agregat)

        elapsed = time.time() - cycle_start
        sleep_time = max(0, SYNC_INTERVAL - elapsed)
        log.info(f"Cycle termine en {elapsed:.1f}s. Prochain dans {sleep_time:.0f}s.")
        time.sleep(sleep_time)

if __name__ == "__main__":
    main()
