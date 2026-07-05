CREATE TABLE IF NOT EXISTS exploitations (
    id SERIAL PRIMARY KEY,
    nom VARCHAR(100) NOT NULL,
    pays VARCHAR(50) NOT NULL,
    temp_ideale FLOAT NOT NULL,
    humidite_ideale FLOAT NOT NULL,
    tolerance_temp FLOAT DEFAULT 3.0,
    tolerance_humidite FLOAT DEFAULT 2.0
);

CREATE TABLE IF NOT EXISTS entrepots (
    id SERIAL PRIMARY KEY,
    nom VARCHAR(100) NOT NULL,
    exploitation_id INTEGER REFERENCES exploitations(id),
    localisation VARCHAR(200)
);

CREATE TABLE IF NOT EXISTS lots (
    id VARCHAR(50) PRIMARY KEY,
    exploitation_id INTEGER REFERENCES exploitations(id),
    entrepot_id INTEGER REFERENCES entrepots(id),
    date_stockage TIMESTAMP NOT NULL DEFAULT NOW(),
    statut VARCHAR(20) DEFAULT 'conforme',
    poids_kg FLOAT,
    qualite VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS mesures (
    id SERIAL PRIMARY KEY,
    entrepot_id INTEGER REFERENCES entrepots(id),
    lot_id VARCHAR(50) REFERENCES lots(id),
    temperature FLOAT NOT NULL,
    humidite FLOAT NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    est_alerte BOOLEAN DEFAULT FALSE
);

INSERT INTO exploitations (nom, pays, temp_ideale, humidite_ideale) VALUES
    ('Fazenda São João', 'bresil', 29.0, 55.0),
    ('Fazenda Boa Vista', 'bresil', 29.0, 55.0)
ON CONFLICT DO NOTHING;

INSERT INTO entrepots (nom, exploitation_id, localisation) VALUES
    ('Entrepôt Principal Brasilia', 1, 'Brasilia, DF'),
    ('Entrepôt São Paulo', 1, 'São Paulo, SP'),
    ('Entrepôt Boa Vista', 2, 'Boa Vista, RR')
ON CONFLICT DO NOTHING;

INSERT INTO lots (id, exploitation_id, entrepot_id, date_stockage, statut, poids_kg, qualite) VALUES
    ('LOT-BR-2024-001', 1, 1, '2024-01-15 08:00:00', 'conforme', 500.0, 'premium'),
    ('LOT-BR-2024-002', 1, 1, '2024-03-10 09:00:00', 'conforme', 750.0, 'standard'),
    ('LOT-BR-2024-003', 2, 2, '2024-06-01 10:00:00', 'en_alerte', 300.0, 'premium'),
    ('LOT-BR-2025-001', 1, 3, '2025-01-20 07:00:00', 'conforme', 600.0, 'standard')
ON CONFLICT DO NOTHING;