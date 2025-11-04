# backend/models.py
from __future__ import annotations

import os
from datetime import datetime

from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Boolean, DateTime, Text
)
from sqlalchemy.orm import declarative_base, sessionmaker

# ---- Ruta absoluta a test.db (en la raíz del proyecto) ----
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_FILE = os.path.join(BASE_DIR, "test.db")
DATABASE_URL = f"sqlite:///{DB_FILE}"

# ---- Engine y sesión ----
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # necesario para SQLite + FastAPI
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# ---- Modelos ----
class Producto(Base):
    __tablename__ = "productos"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False, index=True)
    precio = Column(Float, nullable=False, default=0.0)
    disponible = Column(Boolean, default=True, index=True)


class Pedido(Base):
    __tablename__ = "pedidos"

    id = Column(Integer, primary_key=True, index=True)
    # Guardaremos los IDs de productos como JSON en texto (ej: "[1,2,3]")
    productos = Column(Text, nullable=False, default="[]")
    total = Column(Float, nullable=False, default=0.0)
    estado = Column(String, nullable=False, default="pendiente", index=True)
    fecha = Column(DateTime, nullable=False, default=datetime.utcnow)
    modo = Column(String, default="")   # <-- NUEVO

# ---- Crear tablas si no existen ----
Base.metadata.create_all(bind=engine)
