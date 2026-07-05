import paho.mqtt.client as mqtt
import json
import os
from datetime import datetime

MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "futurekawa/#")


def on_connect(client, userdata, flags, rc):
    print(f"[MQTT] Connecté au broker (code: {rc})")
    client.subscribe(MQTT_TOPIC)


def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        print(f"[MQTT] Reçu sur {msg.topic}: {payload}")

        from app.models import SessionLocal, Mesure, Lot, Exploitation
        from app.alertes import verifier_conditions, envoyer_email_alerte

        temperature  = payload.get("temperature")
        humidite     = payload.get("humidite")
        entrepot_id  = payload.get("entrepot_id", 1)
        pays         = payload.get("pays", "bresil").strip().lower()

        if temperature is None or humidite is None:
            return

        db = SessionLocal()
        try:
            # 1. Trouver l'exploitation selon le pays
            exploitation = db.query(Exploitation).filter(
                Exploitation.pays == pays
            ).first()
            if not exploitation:
                exploitation = db.query(Exploitation).first()

            # 2. Vérifier les seuils
            est_alerte = False
            if exploitation:
                est_alerte = verifier_conditions(temperature, humidite, exploitation)

            nouveau_statut = "en_alerte" if est_alerte else "conforme"

            # 3. Récupérer TOUS les lots du pays
            exploitations_pays = db.query(Exploitation).filter(
                Exploitation.pays == pays
            ).all()
            ids_exploitations = [e.id for e in exploitations_pays]
            lots_du_pays = db.query(Lot).filter(
                Lot.exploitation_id.in_(ids_exploitations)
            ).all()

            # 4. Mémoriser statuts AVANT
            statuts_avant = {lot.id: lot.statut for lot in lots_du_pays}

            # 5. Sauvegarder mesure pour CHAQUE lot
            for lot in lots_du_pays:
                db.add(Mesure(
                    entrepot_id=entrepot_id,
                    lot_id=lot.id,
                    temperature=temperature,
                    humidite=humidite,
                    timestamp=datetime.utcnow(),
                    est_alerte=est_alerte
                ))

            # 6. Mettre à jour statut de TOUS les lots
            for lot in lots_du_pays:
                lot.statut = nouveau_statut

            # 7. Détecter changement
            changement = any(
                statuts_avant.get(lot.id) != nouveau_statut
                for lot in lots_du_pays
            )
            print(f"[MQTT] Pays: {pays} | Alerte: {est_alerte} | Changement: {changement}")

            # 8. Envoyer UN SEUL email si changement
            if changement and exploitation and lots_du_pays:
                destinataire = os.getenv("DESTINATAIRE", "cyliahammadi4@gmail.com")
                liste_lots = ", ".join([lot.id for lot in lots_du_pays])

                if est_alerte:
                    print(f"[EMAIL] ⚠️ Alerte pays {pays.upper()}")
                    envoyer_email_alerte(
                        destinataire,
                        f"⚠️ ALERTE FutureKawa - Conditions hors plage - {pays.upper()}",
                        f"""ALERTE FutureKawa - Conditions hors plage

Pays     : {pays.upper()}
Temp     : {temperature}°C (idéale : {exploitation.temp_ideale}°C ±{exploitation.tolerance_temp})
Humidité : {humidite}% (idéale : {exploitation.humidite_ideale}% ±{exploitation.tolerance_humidite})
Lots     : {liste_lots}
Heure    : {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC

Action requise : vérifier les équipements de l'entrepôt !
"""
                    )
                else:
                    print(f"[EMAIL] ✅ Retour normal pays {pays.upper()}")
                    envoyer_email_alerte(
                        destinataire,
                        f"✅ FutureKawa - Retour à la normale - {pays.upper()}",
                        f"""FutureKawa - Conditions revenues à la normale

Pays     : {pays.upper()}
Temp     : {temperature}°C
Humidité : {humidite}%
Lots     : {liste_lots}
Heure    : {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC

Les conditions sont revenues dans les limites acceptables. ✅
"""
                    )

            db.commit()

        finally:
            db.close()

    except Exception as e:
        print(f"[MQTT] Erreur: {e}")


def demarrer_mqtt():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    tentatives = 0
    while tentatives < 10:
        try:
            client.connect(MQTT_HOST, MQTT_PORT, 60)
            client.loop_forever()
            break
        except Exception as e:
            tentatives += 1
            print(f"[MQTT] Retry ({tentatives}/10): {e}")
            import time
            time.sleep(5)