from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
import threading
import os

from app.models import Base, engine, get_db, Exploitation, Entrepot, Lot, Mesure
from app.alertes import verifier_lot_perime
from app.mqtt_client import demarrer_mqtt
from dotenv import load_dotenv
load_dotenv()

app = FastAPI(title="FutureKawa - Backend Pays", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    try:
        Base.metadata.create_all(bind=engine)
        print("[DB] Tables créées avec succès !")
    except Exception as e:
        print(f"[DB] Erreur création tables: {e}")
    threading.Thread(target=demarrer_mqtt, daemon=True).start()


class LotCreer(BaseModel):
    id: str
    exploitation_id: int
    entrepot_id: int
    poids_kg: Optional[float] = None
    qualite: Optional[str] = None


class LotReponse(BaseModel):
    id: str
    exploitation_id: int
    entrepot_id: int
    date_stockage: datetime
    statut: str
    poids_kg: Optional[float]
    qualite: Optional[str]
    jours_stockage: int
    class Config:
        from_attributes = True


class MesureReponse(BaseModel):
    id: int
    entrepot_id: int
    lot_id: Optional[str]
    temperature: float
    humidite: float
    timestamp: datetime
    est_alerte: bool
    class Config:
        from_attributes = True


class MesureIoT(BaseModel):
    temperature: float
    humidite: float
    entrepot_id: int
    lot_id: Optional[str] = None
    pays: Optional[str] = None


class ExploitationCreer(BaseModel):
    nom: str
    pays: str
    temp_ideale: float
    humidite_ideale: float
    tolerance_temp: float = 3.0
    tolerance_humidite: float = 2.0


@app.get("/")
def racine():
    return {"service": "FutureKawa Backend Pays", "statut": "ok"}


@app.get("/health")
def health():
    return {"statut": "ok", "timestamp": datetime.utcnow().isoformat()}


@app.post("/lots", response_model=LotReponse)
def creer_lot(lot: LotCreer, db: Session = Depends(get_db)):
    if db.query(Lot).filter(Lot.id == lot.id).first():
        raise HTTPException(status_code=400, detail="Lot déjà existant")
    nouveau_lot = Lot(**lot.dict(), date_stockage=datetime.utcnow(), statut="conforme")
    db.add(nouveau_lot)
    db.commit()
    db.refresh(nouveau_lot)
    return {**nouveau_lot.__dict__, "jours_stockage": (datetime.utcnow() - nouveau_lot.date_stockage).days}


@app.get("/lots", response_model=list[LotReponse])
def lister_lots(exploitation_id: Optional[int] = None, statut: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Lot)
    if exploitation_id:
        query = query.filter(Lot.exploitation_id == exploitation_id)
    if statut:
        query = query.filter(Lot.statut == statut)
    lots = query.order_by(Lot.date_stockage.asc()).all()
    return [{**lot.__dict__, "jours_stockage": (datetime.utcnow() - lot.date_stockage).days} for lot in lots]


@app.get("/lots/{lot_id}", response_model=LotReponse)
def obtenir_lot(lot_id: str, db: Session = Depends(get_db)):
    lot = db.query(Lot).filter(Lot.id == lot_id).first()
    if not lot:
        raise HTTPException(status_code=404, detail="Lot introuvable")
    return {**lot.__dict__, "jours_stockage": (datetime.utcnow() - lot.date_stockage).days}


@app.get("/lots/{lot_id}/mesures", response_model=list[MesureReponse])
def mesures_lot(lot_id: str, limite: int = 1000, db: Session = Depends(get_db)):
    lot = db.query(Lot).filter(Lot.id == lot_id).first()
    if not lot:
        raise HTTPException(status_code=404, detail="Lot introuvable")
    return db.query(Mesure).filter(Mesure.lot_id == lot_id).order_by(Mesure.timestamp.desc()).limit(limite).all()


@app.get("/mesures", response_model=list[MesureReponse])
def lister_mesures(entrepot_id: Optional[int] = None, limite: int = 1000, db: Session = Depends(get_db)):
    query = db.query(Mesure)
    if entrepot_id:
        query = query.filter(Mesure.entrepot_id == entrepot_id)
    return query.order_by(Mesure.timestamp.desc()).limit(limite).all()


@app.get("/alertes")
def lister_alertes(db: Session = Depends(get_db)):
    alertes = []
    for lot in db.query(Lot).all():
        if verifier_lot_perime(lot.date_stockage):
            jours = (datetime.utcnow() - lot.date_stockage).days
            alertes.append({
                "lot_id": lot.id,
                "type": "peremption",
                "message": f"Lot stocké depuis {jours} jours",
                "timestamp": datetime.utcnow().isoformat()
            })
        elif lot.statut == "en_alerte":
            alertes.append({
                "lot_id": lot.id,
                "type": "conditions",
                "message": "Conditions hors plage",
                "timestamp": datetime.utcnow().isoformat()
            })
    return alertes


@app.get("/exploitations")
def lister_exploitations(db: Session = Depends(get_db)):
    return db.query(Exploitation).all()


@app.get("/entrepots")
def lister_entrepots(db: Session = Depends(get_db)):
    return db.query(Entrepot).all()


@app.post("/mesures-iot")
def recevoir_mesure_iot(mesure: MesureIoT, db: Session = Depends(get_db)):
    from app.alertes import verifier_conditions, envoyer_email_alerte

    # 1. Trouver l'exploitation selon le pays
    pays = (mesure.pays or "bresil").strip().lower()
    exploitation = db.query(Exploitation).filter(Exploitation.pays == pays).first()
    if not exploitation:
        exploitation = db.query(Exploitation).first()

    # 2. Vérifier les seuils
    est_alerte = False
    if exploitation:
        est_alerte = verifier_conditions(mesure.temperature, mesure.humidite, exploitation)

    nouveau_statut = "en_alerte" if est_alerte else "conforme"
    print(f"[IoT] Pays: {pays} | Temp: {mesure.temperature} | Hum: {mesure.humidite} | Alerte: {est_alerte}")

    # 3. Récupérer TOUS les lots du pays
    lots_du_pays = []
    if exploitation:
        exploitations_pays = db.query(Exploitation).filter(Exploitation.pays == pays).all()
        ids_exploitations = [e.id for e in exploitations_pays]
        lots_du_pays = db.query(Lot).filter(Lot.exploitation_id.in_(ids_exploitations)).all()

    # 4. Mémoriser statuts AVANT modification
    statuts_avant = {lot.id: lot.statut for lot in lots_du_pays}
    print(f"[IoT] Statuts avant: {statuts_avant} → nouveau: {nouveau_statut}")

    # 5. Sauvegarder mesure pour CHAQUE lot
    for lot in lots_du_pays:
        db.add(Mesure(
            entrepot_id=mesure.entrepot_id,
            lot_id=lot.id,
            temperature=mesure.temperature,
            humidite=mesure.humidite,
            timestamp=datetime.utcnow(),
            est_alerte=est_alerte
        ))

    if not lots_du_pays:
        db.add(Mesure(
            entrepot_id=mesure.entrepot_id,
            lot_id=mesure.lot_id,
            temperature=mesure.temperature,
            humidite=mesure.humidite,
            timestamp=datetime.utcnow(),
            est_alerte=est_alerte
        ))

    # 6. Mettre à jour statut de TOUS les lots
    for lot in lots_du_pays:
        lot.statut = nouveau_statut

    # 7. Détecter changement sur au moins un lot
    changement = any(statuts_avant.get(lot.id) != nouveau_statut for lot in lots_du_pays)
    print(f"[IoT] Changement détecté: {changement}")

    # 8. Envoyer UN SEUL email pour tout le pays si changement
    if changement and exploitation and lots_du_pays:
        destinataire = os.getenv("DESTINATAIRE", "cyliahammadi4@gmail.com")
        liste_lots = ", ".join([lot.id for lot in lots_du_pays])

        if est_alerte:
            print(f"[EMAIL] ⚠️ Envoi alerte pays {pays.upper()}")
            envoyer_email_alerte(
                destinataire,
                f"⚠️ ALERTE FutureKawa - Conditions hors plage - {pays.upper()}",
                f"""ALERTE FutureKawa - Conditions hors plage

Pays     : {pays.upper()}
Temp     : {mesure.temperature}°C (idéale : {exploitation.temp_ideale}°C ±{exploitation.tolerance_temp})
Humidité : {mesure.humidite}% (idéale : {exploitation.humidite_ideale}% ±{exploitation.tolerance_humidite})
Lots     : {liste_lots}
Heure    : {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC

Action requise : vérifier les équipements de l'entrepôt !
"""
            )
        else:
            print(f"[EMAIL] ✅ Envoi retour normal pays {pays.upper()}")
            envoyer_email_alerte(
                destinataire,
                f"✅ FutureKawa - Retour à la normale - {pays.upper()}",
                f"""FutureKawa - Conditions revenues à la normale

Pays     : {pays.upper()}
Temp     : {mesure.temperature}°C
Humidité : {mesure.humidite}%
Lots     : {liste_lots}
Heure    : {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC

Les conditions sont revenues dans les limites acceptables. ✅
"""
            )

    db.commit()
    return {
        "statut": "ok",
        "alerte": est_alerte,
        "pays": pays,
        "lots_mis_a_jour": len(lots_du_pays)
    }


@app.delete("/lots/{lot_id}")
def supprimer_lot(lot_id: str, db: Session = Depends(get_db)):
    lot = db.query(Lot).filter(Lot.id == lot_id).first()
    if not lot:
        raise HTTPException(status_code=404, detail="Lot introuvable")
    db.query(Mesure).filter(Mesure.lot_id == lot_id).delete()
    db.delete(lot)
    db.commit()
    return {"message": f"Lot {lot_id} supprimé"}


@app.post("/exploitations")
def creer_exploitation(expl: ExploitationCreer, db: Session = Depends(get_db)):
    nouvelle = Exploitation(**expl.dict())
    db.add(nouvelle)
    db.commit()
    db.refresh(nouvelle)
    return nouvelle


@app.delete("/mesures/test")
def supprimer_mesures_test(db: Session = Depends(get_db)):
    n = db.query(Mesure).filter(Mesure.temperature >= 33).delete()
    db.commit()
    return {"message": f"{n} mesures supprimées"}
