from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import httpx, asyncio, os

app = FastAPI(title="FutureKawa - Backend Siège", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BACKENDS = {
    "bresil":   os.getenv("API_BRESIL",   "http://localhost:8000"),
    "equateur": os.getenv("API_EQUATEUR", "http://localhost:8001"),
    "colombie": os.getenv("API_COLOMBIE", "http://localhost:8002"),
}

async def get_pays(pays, chemin):
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{BACKENDS[pays]}{chemin}")
            return r.json()
    except:
        return None

@app.get("/")
def racine():
    return {"service": "FutureKawa Backend Siège", "statut": "ok"}

@app.get("/health")
async def health():
    statuts = {}
    for pays in BACKENDS:
        r = await get_pays(pays, "/health")
        statuts[pays] = "en_ligne" if r else "hors_ligne"
    return {"statut": "ok", "pays": statuts}

@app.get("/stocks")
async def stocks():
    tous = []
    for pays in BACKENDS:
        lots = await get_pays(pays, "/lots")
        if lots:
            for lot in lots:
                lot["pays"] = pays
            tous.extend(lots)
    tous.sort(key=lambda x: x.get("date_stockage", ""))
    return {"total": len(tous), "lots": tous}

@app.get("/alertes")
async def alertes():
    toutes = []
    for pays in BACKENDS:
        alertes = await get_pays(pays, "/alertes")
        if alertes:
            for a in alertes:
                a["pays"] = pays
            toutes.extend(alertes)
    return {"total": len(toutes), "alertes": toutes}

@app.get("/pays/{pays}/lots")
async def lots_pays(pays: str):
    lots = await get_pays(pays, "/lots")
    return {"pays": pays, "lots": lots or [], "total": len(lots) if lots else 0}