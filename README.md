
# FutureKawa — Solution IoT de suivi des stocks de café vert

> **Projet MSPR — Bloc 4 — RNCP35584**  
> Candidat : Cylia Hammadi  
> Année académique : 2025-2026

---

##  Présentation du projet

FutureKawa est une entreprise internationale spécialisée dans la caféiculture et la logistique de café vert, opérant dans trois pays d'Amérique du Sud : le **Brésil**, l'**Équateur** et la **Colombie**.

Ce projet MSPR consiste à développer une solution applicative complète intégrant un dispositif IoT pour :

- Centraliser le suivi des stocks par pays et par entrepôt
- Garantir la traçabilité des lots avec la logique FIFO
- Surveiller automatiquement les conditions de conservation (température et humidité)
- Alerter instantanément par email les responsables en cas de dérive

---

##  Architecture

```
ESP32 + DHT22 (capteur physique)
        ↓ MQTT
Mosquitto (broker port 1883)
        ↓
mqtt_client.py (réception + traitement)
        ↓
FastAPI + SQLite (API REST port 8000)
        ↓
Frontend HTML/JS + Chart.js
        ↓
Gmail SMTP (alertes email automatiques)
```

---

##  Structure du projet

```
futurekawa/
├── backend-pays/
│   ├── app/
│   │   ├── main.py          # Routes FastAPI
│   │   ├── models.py        # Modèles SQLAlchemy
│   │   ├── alertes.py       # Logique alertes + emails
│   │   └── mqtt_client.py   # Client MQTT
│   ├── tests/
│   │   ├── test_backend.py  # 15 tests automatiques
│   │   └── jenkins/
│   │       └── Jenkinsfile  # Pipeline CI/CD
│   ├── requirements.txt
│   └── .env.example
├── backend-siege/
│   └── app/main.py          # Agrégation multi-pays (port 9000)
├── frontend/
│   └── index.html           # Interface web
├── iot-simulator/
│   └── simulator.py         # Simulateur ESP32
└── README.md
```

---

##  Technologies utilisées

| Composant | Technologie | Justification |
|-----------|-------------|---------------|
| Microcontrôleur | ESP32 + MicroPython v1.28 | Wi-Fi intégré, faible coût |
| Capteur | DHT22 | Mesure température + humidité |
| Protocole IoT | MQTT / Mosquitto | Ultra-léger, adapté IoT |
| Backend | FastAPI Python | Swagger auto, performances |
| Base de données | SQLite | Portable, prototype |
| Frontend | HTML5/JS + Chart.js | Léger, graphiques interactifs |
| Tests | pytest | Standard Python |
| CI/CD | Jenkins + GitHub | Pipeline automatisé |
| Emails | Gmail SMTP | Alertes automatiques |

---

##  Seuils d'alerte par pays

| Pays | Température idéale | Plage | Humidité idéale | Plage |
|------|-------------------|-------|-----------------|-------|
| Brésil | 29°C | 26°C – 32°C | 55% | 53% – 57% |
| Équateur | 31°C | 28°C – 34°C | 60% | 58% – 62% |
| Colombie | 26°C | 23°C – 29°C | 80% | 78% – 82% |

---

##  Lancement du projet

### Prérequis

- Python 3.10+
- Mosquitto 2.0 installé sur Windows
- ESP32 avec MicroPython v1.28 (optionnel)
- Java 21 pour Jenkins (optionnel)

### Étape 1 — Démarrer Mosquitto

```powershell
# PowerShell en administrateur
net start mosquitto
```

### Étape 2 — Installer les dépendances

```bash
cd backend-pays
pip install -r requirements.txt
```

### Étape 3 — Configurer les variables d'environnement

Copier le fichier `.env.example` en `.env` et remplir les valeurs :

```bash
cp .env.example .env
```

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=votre.email@gmail.com
SMTP_PASS=mot_de_passe_application_gmail
DESTINATAIRE=responsable@futurekawa.com
```

### Étape 4 — Lancer le backend pays

```bash
cd backend-pays
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Étape 5 — Lancer le backend siège (optionnel)

```bash
cd backend-siege
uvicorn app.main:app --host 0.0.0.0 --port 9000 --reload
```

### Étape 6 — Ouvrir le frontend

Ouvrir le fichier `frontend/index.html` dans un navigateur.

### Étape 7 — Lancer l'ESP32

Dans Thonny, ouvrir et exécuter `main.py` sur le device MicroPython.

---

##  Tests automatiques

```bash
cd backend-pays
python -m pytest tests/ -v
```

### Résultat attendu

```
15 passed in 5.61s 
```

### Détail des 15 tests

**9 tests unitaires — Logique d'alertes :**
- Conditions normales Brésil (29°C/55%) → pas d'alerte
- Température trop haute (33°C > 32°C) → alerte
- Humidité trop basse (50% < 53%) → alerte
- Conditions limite acceptables → pas d'alerte
- Conditions normales Équateur → pas d'alerte
- Conditions normales Colombie → pas d'alerte
- Lot périmé (400 jours) → alerte péremption
- Lot frais (100 jours) → pas d'alerte
- Lot exactement 365 jours → pas encore périmé

**6 tests d'intégration API :**
- GET /health → 200 OK
- GET /lots vide → liste vide
- POST /lots + GET /lots → lot créé
- POST /lots doublon → code 400
- GET /lots/INEXISTANT → code 404
- Ordre FIFO strictement respecté

---

##  Pipeline CI/CD Jenkins

Le pipeline Jenkins comprend 5 étapes automatisées à chaque commit :

```
Checkout SCM → Récupération code → Installation deps → Tests → Post Actions
     ✅               ✅                  ✅              ✅          ✅
```

Le Jenkinsfile est disponible dans `backend-pays/tests/jenkins/Jenkinsfile`.

---

## 📧 Système d'alertes email

Le système envoie **un seul email par pays** lors de chaque changement de statut :

- ** Alerte** : quand les conditions passent de conformes à hors plage
- ** Retour normale** : quand les conditions redeviennent acceptables

L'anti-doublon garantit qu'aucun email n'est envoyé si le statut ne change pas.

---

##  Format des identifiants de lots

```
LOT-BR-AAAA-NNN  → Brésil
LOT-EQ-AAAA-NNN  → Équateur
LOT-CO-AAAA-NNN  → Colombie

Exemple : LOT-BR-2026-001
```

---

##  Câblage ESP32 + DHT22

```
ESP32        DHT22
─────        ─────
3V3   ──→   + (VCC)    fil rouge
D4    ──→   OUT (DATA)  fil jaune
GND   ──→   - (GND)    fil noir
```

---

##  Topics MQTT

```
futurekawa/bresil/mesures
futurekawa/equateur/mesures
futurekawa/colombie/mesures
```

---

##  Routes API principales

| Méthode | Route | Description |
|---------|-------|-------------|
| GET | /health | État de l'API |
| POST | /lots | Créer un lot |
| GET | /lots | Lister les lots (FIFO) |
| GET | /lots/{id}/mesures | Historique des mesures |
| GET | /alertes | Alertes actives |
| POST | /mesures-iot | Recevoir une mesure IoT |
| GET | /exploitations | Lister les exploitations |

Documentation Swagger disponible sur : **http://localhost:8000/docs**

---

##  Sécurité

- Le fichier `.env` est exclu du dépôt Git via `.gitignore`
- Le fichier `futurekawa.db` est exclu du dépôt Git
- Changer le mot de passe Gmail après la démonstration
