from datetime import datetime
import smtplib
from email.message import EmailMessage
import os


def verifier_conditions(temperature: float, humidite: float, exploitation) -> bool:
    temp_min = exploitation.temp_ideale - exploitation.tolerance_temp
    temp_max = exploitation.temp_ideale + exploitation.tolerance_temp
    hum_min = exploitation.humidite_ideale - exploitation.tolerance_humidite
    hum_max = exploitation.humidite_ideale + exploitation.tolerance_humidite
    temp_hors_plage = not (temp_min <= temperature <= temp_max)
    hum_hors_plage = not (hum_min <= humidite <= hum_max)
    return temp_hors_plage or hum_hors_plage


def verifier_lot_perime(date_stockage: datetime) -> bool:
    return (datetime.utcnow() - date_stockage).days > 365


def envoyer_email_alerte(destinataire: str, sujet: str, corps: str):
    smtp_user = os.getenv("SMTP_USER", "")
    if not smtp_user:
        print(f"[ALERTE EMAIL simulé] À: {destinataire} | {sujet}")
        print(corps)
        return
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_pass = os.getenv("SMTP_PASS", "")
    msg = EmailMessage()
    msg["Subject"] = sujet
    msg["From"] = smtp_user
    msg["To"] = destinataire
    msg.set_content(corps)
    with smtplib.SMTP(smtp_host, smtp_port) as serveur:
        serveur.starttls()
        serveur.login(smtp_user, smtp_pass)
        serveur.send_message(msg)


def generer_message_alerte_conditions(lot_id, pays, temp, hum, temp_ideale, hum_ideale):
    return f"""ALERTE FutureKawa - Conditions hors plage
Lot : {lot_id}
Pays : {pays}
Température : {temp}°C (idéale : {temp_ideale}°C ±3)
Humidité : {hum}% (idéale : {hum_ideale}% ±2)
Horodatage : {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
"""


def generer_message_alerte_peremption(lot_id, pays, date_stockage):
    jours = (datetime.utcnow() - date_stockage).days
    return f"""ALERTE FutureKawa - Lot trop ancien
Lot : {lot_id}
Pays : {pays}
En stockage depuis : {jours} jours (seuil : 365 jours)
"""