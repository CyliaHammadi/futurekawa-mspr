from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, create_engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from datetime import datetime
import os

DATABASE_URL = "sqlite:///./futurekawa.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Exploitation(Base):
    __tablename__ = "exploitations"
    id = Column(Integer, primary_key=True)
    nom = Column(String(100), nullable=False)
    pays = Column(String(50), nullable=False)
    temp_ideale = Column(Float, nullable=False)
    humidite_ideale = Column(Float, nullable=False)
    tolerance_temp = Column(Float, default=3.0)
    tolerance_humidite = Column(Float, default=2.0)
    entrepots = relationship("Entrepot", back_populates="exploitation")
    lots = relationship("Lot", back_populates="exploitation")


class Entrepot(Base):
    __tablename__ = "entrepots"
    id = Column(Integer, primary_key=True)
    nom = Column(String(100), nullable=False)
    exploitation_id = Column(Integer, ForeignKey("exploitations.id"))
    localisation = Column(String(200))
    exploitation = relationship("Exploitation", back_populates="entrepots")
    mesures = relationship("Mesure", back_populates="entrepot")


class Lot(Base):
    __tablename__ = "lots"
    id = Column(String(50), primary_key=True)
    exploitation_id = Column(Integer, ForeignKey("exploitations.id"))
    entrepot_id = Column(Integer, ForeignKey("entrepots.id"))
    date_stockage = Column(DateTime, default=datetime.utcnow)
    statut = Column(String(20), default="conforme")
    poids_kg = Column(Float)
    qualite = Column(String(50))
    exploitation = relationship("Exploitation", back_populates="lots")
    mesures = relationship("Mesure", back_populates="lot")


class Mesure(Base):
    __tablename__ = "mesures"
    id = Column(Integer, primary_key=True)
    entrepot_id = Column(Integer, ForeignKey("entrepots.id"))
    lot_id = Column(String(50), ForeignKey("lots.id"))
    temperature = Column(Float, nullable=False)
    humidite = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    est_alerte = Column(Boolean, default=False)
    entrepot = relationship("Entrepot", back_populates="mesures")
    lot = relationship("Lot", back_populates="mesures")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()