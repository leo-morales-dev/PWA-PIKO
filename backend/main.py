# backend/main.py
from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from datetime import datetime
from pathlib import Path
import json

# ------------------------ Imports de modelos ------------------------
try:
    from backend.models import SessionLocal, Producto as ProductoModel, Pedido as PedidoModel
except ModuleNotFoundError:  # ejecutando desde la carpeta backend (Render Root Dir)
    from models import SessionLocal, Producto as ProductoModel, Pedido as PedidoModel

# ------------------------ App & CORS ------------------------
app = FastAPI(title="API Cafetería Universitaria", version="0.1.0")

# CORS amplio para desarrollo (ajusta dominios en producción)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],           # <--- en producción, restringe
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------ Servir PWA (carpeta build/) ------------------------
# Estructura asumida:
# repo/
# ├─ build/           <-- salida ya comiteada del front (index.html, assets, etc.)
# └─ backend/
#     └─ main.py
STATIC_DIR = Path(__file__).parent.parent / "build"

# Si tu bundler usa subcarpeta "assets", esto ayuda a servir recursos pesados con /static/*
# (aunque no es obligatorio, es útil para cacheo/CDN)
if (STATIC_DIR / "assets").exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR / "assets"), name="static")

# Ruta raíz: devuelve la SPA
@app.get("/", include_in_schema=False)
def serve_index_root():
    index = STATIC_DIR / "index.html"
    if index.exists():
        return FileResponse(index)
    return {"detail": "index.html no encontrado en /build"}

# Fallback de SPA: para cualquier GET que no empiece con "api" ni "ws", devuelve index.html
@app.get("/{full_path:path}", include_in_schema=False)
def spa_fallback(full_path: str):
    # preserva /api/* para el backend y deja libres posibles rutas de websockets (/ws/*)
    if full_path.startswith("api") or full_path.startswith("ws"):
        return {"detail": "Not Found"}
    index = STATIC_DIR / "index.html"
    if index.exists():
        return FileResponse(index)
    return {"detail": "index.html no encontrado en /build"}

# ------------------------ DB helpers ------------------------
def get_db():
    db = SessionLocal()
    try:
