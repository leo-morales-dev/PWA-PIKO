from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
from datetime import datetime

app = FastAPI(title="API Cafetería Universitaria")

# ---------- MODELOS ----------
class Producto(BaseModel):
    id: int
    nombre: str
    precio: float
    disponible: bool = True

class Pedido(BaseModel):
    id: int
    productos: List[int]
    total: float
    estado: str = "pendiente"
    fecha: datetime = datetime.now()

# ---------- DATOS TEMPORALES ----------
menu = [
    Producto(id=1, nombre="Café americano", precio=25.0),
    Producto(id=2, nombre="Capuchino", precio=35.0),
    Producto(id=3, nombre="Latte", precio=30.0),
    Producto(id=4, nombre="Pan dulce", precio=15.0)
]

pedidos: List[Pedido] = []

# ---------- ENDPOINTS ----------
@app.get("/api/menu", response_model=List[Producto])
def get_menu():
    return menu

@app.get("/api/pedidos", response_model=List[Pedido])
def get_pedidos():
    return pedidos

@app.post("/api/pedidos", response_model=Pedido)
def crear_pedido(pedido: Pedido):
    pedidos.append(pedido)
    return pedido
