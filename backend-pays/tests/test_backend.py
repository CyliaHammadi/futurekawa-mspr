import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock


def test_conditions_normales_bresil():
    from app.alertes import verifier_conditions
    e = MagicMock()
    e.temp_ideale, e.humidite_ideale = 29.0, 55.0
    e.tolerance_temp, e.tolerance_humidite = 3.0, 2.0
    assert verifier_conditions(29.0, 55.0, e) is False

def test_temperature_trop_haute_bresil():
    from app.alertes import verifier_conditions
    e = MagicMock()
    e.temp_ideale, e.humidite_ideale = 29.0, 55.0
    e.tolerance_temp, e.tolerance_humidite = 3.0, 2.0
    assert verifier_conditions(33.0, 55.0, e) is True

def test_humidite_trop_basse():
    from app.alertes import verifier_conditions
    e = MagicMock()
    e.temp_ideale, e.humidite_ideale = 29.0, 55.0
    e.tolerance_temp, e.tolerance_humidite = 3.0, 2.0
    assert verifier_conditions(29.0, 50.0, e) is True

def test_conditions_limite_acceptables():
    from app.alertes import verifier_conditions
    e = MagicMock()
    e.temp_ideale, e.humidite_ideale = 29.0, 55.0
    e.tolerance_temp, e.tolerance_humidite = 3.0, 2.0
    assert verifier_conditions(32.0, 57.0, e) is False

def test_conditions_equateur():
    from app.alertes import verifier_conditions
    e = MagicMock()
    e.temp_ideale, e.humidite_ideale = 31.0, 60.0
    e.tolerance_temp, e.tolerance_humidite = 3.0, 2.0
    assert verifier_conditions(31.0, 60.0, e) is False

def test_conditions_colombie():
    from app.alertes import verifier_conditions
    e = MagicMock()
    e.temp_ideale, e.humidite_ideale = 26.0, 80.0
    e.tolerance_temp, e.tolerance_humidite = 3.0, 2.0
    assert verifier_conditions(26.0, 80.0, e) is False

def test_lot_perime():
    from app.alertes import verifier_lot_perime
    assert verifier_lot_perime(datetime.utcnow() - timedelta(days=400)) is True

def test_lot_frais():
    from app.alertes import verifier_lot_perime
    assert verifier_lot_perime(datetime.utcnow() - timedelta(days=100)) is False

def test_lot_exactement_365_jours():
    from app.alertes import verifier_lot_perime
    assert verifier_lot_perime(datetime.utcnow() - timedelta(days=365)) is False


@pytest.fixture
def client_test():
    import os, tempfile
    from unittest.mock import patch
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.models import Base, get_db
    from app.main import app

    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)
    test_engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with patch("app.main.demarrer_mqtt"), patch("app.models.Base.metadata.create_all"):
        with TestClient(app) as c:
            yield c
    app.dependency_overrides.clear()
    test_engine.dispose()
    os.unlink(db_path)


def test_health(client_test):
    r = client_test.get("/health")
    assert r.status_code == 200

def test_lister_lots_vide(client_test):
    r = client_test.get("/lots")
    assert r.status_code == 200
    assert r.json() == []

def test_creer_et_lister_lot(client_test):
    r = client_test.post("/lots", json={"id": "LOT-TEST-001", "exploitation_id": 1, "entrepot_id": 1, "poids_kg": 500.0, "qualite": "premium"})
    assert r.status_code == 200
    assert r.json()["statut"] == "conforme"
    assert len(client_test.get("/lots").json()) == 1

def test_lot_duplique(client_test):
    client_test.post("/lots", json={"id": "LOT-DUP-001", "exploitation_id": 1, "entrepot_id": 1})
    assert client_test.post("/lots", json={"id": "LOT-DUP-001", "exploitation_id": 1, "entrepot_id": 1}).status_code == 400

def test_lot_introuvable(client_test):
    assert client_test.get("/lots/LOT-INEXISTANT").status_code == 404

def test_ordre_fifo(client_test):
    for lot_id in ["LOT-C", "LOT-A", "LOT-B"]:
        client_test.post("/lots", json={"id": lot_id, "exploitation_id": 1, "entrepot_id": 1})
    ids = [l["id"] for l in client_test.get("/lots").json()]
    assert len(ids) == 3