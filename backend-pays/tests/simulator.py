import paho.mqtt.client as mqtt
import json, time, random, argparse
from datetime import datetime

CONFIG_PAYS = {
    "bresil":   {"temp_ideale": 29.0, "humidite_ideale": 55.0, "entrepot_id": 1, "lots": ["LOT-BR-2024-001", "LOT-BR-2024-002"]},
    "equateur": {"temp_ideale": 31.0, "humidite_ideale": 60.0, "entrepot_id": 4, "lots": ["LOT-EQ-2024-001"]},
    "colombie": {"temp_ideale": 26.0, "humidite_ideale": 80.0, "entrepot_id": 7, "lots": ["LOT-CO-2024-001"]},
}

def demarrer_simulateur(pays, intervalle=30, mode="normal", mqtt_host="localhost", mqtt_port=1883):
    config = CONFIG_PAYS.get(pays)
    print(f"Simulateur IoT — {pays.upper()} | Mode: {mode} | Intervalle: {intervalle}s")
    client = mqtt.Client()
    for t in range(10):
        try:
            client.connect(mqtt_host, mqtt_port, 60)
            client.loop_start()
            break
        except Exception as e:
            print(f"Retry ({t+1}/10): {e}")
            time.sleep(3)
    lot_idx, compteur = 0, 0
    try:
        while True:
            if compteur % 10 == 0:
                lot_idx = (lot_idx + 1) % len(config["lots"])
            if mode == "derive":
                temp = config["temp_ideale"] + random.uniform(4, 7)
                hum  = config["humidite_ideale"] + random.uniform(3, 5)
            else:
                temp = config["temp_ideale"] + random.uniform(-2, 2)
                hum  = config["humidite_ideale"] + random.uniform(-1.5, 1.5)
            payload = {"temperature": round(temp,2), "humidite": round(hum,2),
                       "entrepot_id": config["entrepot_id"],
                       "lot_id": config["lots"][lot_idx],
                       "timestamp": datetime.utcnow().isoformat()}
            topic = f"futurekawa/{pays}/entrepot{config['entrepot_id']}/mesures"
            client.publish(topic, json.dumps(payload), qos=1)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {temp:.1f}°C / {hum:.1f}% → {topic}")
            compteur += 1
            time.sleep(intervalle)
    except KeyboardInterrupt:
        print("Simulateur arrêté.")
        client.loop_stop()

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--pays", default="bresil", choices=["bresil","equateur","colombie"])
    p.add_argument("--intervalle", type=int, default=30)
    p.add_argument("--mode", default="normal", choices=["normal","derive"])
    p.add_argument("--host", default="localhost")
    p.add_argument("--port", type=int, default=1883)
    a = p.parse_args()
    demarrer_simulateur(a.pays, a.intervalle, a.mode, a.host, a.port)