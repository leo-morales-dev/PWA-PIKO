# backend/main.py
from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
import json

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="API Cafetería Universitaria", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # <-- abrir para desarrollo
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from backend.models import SessionLocal, Producto as ProductoModel, Pedido as PedidoModel

app = FastAPI(title="API Cafetería Universitaria", version="0.1.0")

# CORS amplio para desarrollo (Flet lanza en puertos aleatorios)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],           # <--- en producción, restringe
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------ DB helpers ------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def seed_menu(db: Session):
    if db.query(ProductoModel).count() == 0:
        items = [
            {"id": 1, "nombre": "Café americano", "precio": 25.0, "disponible": True},
            {"id": 2, "nombre": "Capuchino",      "precio": 35.0, "disponible": True},
            {"id": 3, "nombre": "Latte",          "precio": 30.0, "disponible": True},
            {"id": 4, "nombre": "Pan dulce",      "precio": 15.0, "disponible": True},
        ]
        db.add_all([ProductoModel(**it) for it in items])
        db.commit()

# ===== Mapa en memoria: pedido_id -> cliente_id (para notificaciones) =====
CLIENTES: dict[int, str] = {}

# ------------------------ WS manager ------------------------
class ConnectionManager:
    def __init__(self):
        self.active: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active.discard(websocket)

    async def broadcast_json(self, payload: dict):
        dead = []
        for ws in list(self.active):
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

manager = ConnectionManager()

# ------------------------ Utils ------------------------
def productos_map(db: Session) -> dict[int, str]:
    return {p.id: p.nombre for p in db.query(ProductoModel).all()}

def serialize_pedido(p: PedidoModel, name_map: dict[int, str]) -> dict:
    try:
        ids = json.loads(p.productos)
    except Exception:
        ids = []
    nombres = [name_map.get(pid, str(pid)) for pid in ids]
    return {
        "id": p.id,
        "productos": ids,
        "productos_nombres": nombres,
        "total": p.total,
        "estado": p.estado,
        "fecha": p.fecha.isoformat(),
        "modo": getattr(p, "modo", ""),   # <--- evita AttributeError si la columna no existe
        "cliente_nombre": getattr(p, "cliente_nombre", ""),
    }

# ------------------------ Startup ------------------------
@app.on_event("startup")
def _startup():
    # seed de productos y ALTER defensivo para columna 'modo'
    with SessionLocal() as db:
        seed_menu(db)
        conn = db.connection()

        def ensure_column(sql: str) -> None:
            try:
                conn.execute(text(sql))
            except Exception:
                # si la columna ya existe (o el ALTER falla), lo ignoramos
                pass

        ensure_column("ALTER TABLE pedidos ADD COLUMN modo VARCHAR DEFAULT ''")
        ensure_column("ALTER TABLE pedidos ADD COLUMN cliente_nombre VARCHAR DEFAULT ''")

# ------------------------ Endpoints ------------------------
@app.get("/api/menu")
def get_menu(db: Session = Depends(get_db)):
    rows = db.query(ProductoModel).filter(ProductoModel.disponible == True).all()
    return [
        {"id": r.id, "nombre": r.nombre, "precio": float(r.precio or 0), "disponible": r.disponible}
        for r in rows
    ]

@app.get("/api/pedidos")
def get_pedidos(db: Session = Depends(get_db)):
    names = productos_map(db)
    rows = db.query(PedidoModel).order_by(PedidoModel.id.desc()).all()
    return [serialize_pedido(r, names) for r in rows]

@app.get("/api/pedidos/{pedido_id}")
def get_pedido_by_id(pedido_id: int, db: Session = Depends(get_db)):
    p = db.query(PedidoModel).filter(PedidoModel.id == pedido_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    names = productos_map(db)
    return serialize_pedido(p, names)

# ===== Crear pedido: guarda 'modo' y 'cliente_id' =====
@app.post("/api/pedidos")
async def crear_pedido(pedido: dict, db: Session = Depends(get_db)):
    productos  = pedido.get("productos", [])
    total      = float(pedido.get("total", 0))
    estado     = str(pedido.get("estado", "pendiente"))
    cliente_id = str(pedido.get("cliente_id", ""))     # origen: PWA
    modo       = str(pedido.get("modo", ""))           # "Comer aquí" / "Para llevar"
    cliente_nombre = str(pedido.get("cliente_nombre", ""))

    nuevo = PedidoModel(
        productos=json.dumps(productos),
        total=total,
        estado=estado,
        fecha=datetime.utcnow(),
        modo=modo,                                      # <--- guardar modo
        cliente_nombre=cliente_nombre,
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)

    # guarda relación temporal en memoria
    if cliente_id:
        CLIENTES[nuevo.id] = cliente_id

    names = productos_map(db)
    payload = serialize_pedido(nuevo, names)
    payload["cliente_id"] = cliente_id  # reenvía para que el cliente se auto-identifique

    await manager.broadcast_json({"type": "nuevo_pedido", "pedido": payload})
    return {"ok": True, "id": nuevo.id, **payload}

# ===== Actualizar estado: reemite con cliente_id si lo conoce =====
@app.put("/api/pedidos/{pedido_id}/estado")
async def actualizar_estado(pedido_id: int, body: dict, db: Session = Depends(get_db)):
    estado = str(body.get("estado", "pendiente"))
    p = db.query(PedidoModel).filter(PedidoModel.id == pedido_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")

    p.estado = estado
    db.commit()
    db.refresh(p)

    names = productos_map(db)
    payload = serialize_pedido(p, names)
    payload["cliente_id"] = CLIENTES.get(pedido_id, "")

    await manager.broadcast_json({"type": "estado_actualizado", "pedido": payload})
    return {"ok": True}

# ===== WebSocket para tablero / barista / clientes =====
@app.websocket("/ws/pedidos")
async def ws_pedidos(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # no esperamos mensajes específicos; mantenemos la conexión viva
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
