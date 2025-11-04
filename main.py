# main.py (FRONTEND / Flet)
import flet as ft
import requests
import asyncio
from typing import List, Dict, Any, Optional
from flet.core.page import PageDisconnectedException

# --------------------- Config ---------------------
API_URL = "http://127.0.0.1:9000/api"
POLL_SECONDS = 3

# --------------------- Paleta (hex) ---------------------
BG      = "#0b0f14"
PANEL   = "#111827"
BORDER  = "#1f2937"
BOX     = "#0f172a"
MUTED   = "#9aa3af"
BADGE   = "#1f2937"
BLUE600 = "#2563eb"
BLUE700 = "#1d4ed8"
WHITE   = "#ffffff"

def money(n: float) -> str:
    try:
        return f"${float(n or 0):.2f}"
    except Exception:
        return "$0.00"

def tag_chip(text: str, color: str = "#374151"):
    return ft.Container(
        content=ft.Text(text, size=12, color="#e5e7eb"),
        bgcolor=color,
        padding=ft.padding.symmetric(5, 10),
        border_radius=999,
    )

def card_container(content: ft.Control, pad: int = 16):
    return ft.Container(
        bgcolor=PANEL,
        border=ft.border.all(1, BORDER),
        border_radius=14,
        padding=pad,
        content=content,
    )

def box_container(content: ft.Control, pad: int = 14):
    return ft.Container(
        bgcolor=BOX,
        border=ft.border.all(1, BORDER),
        border_radius=12,
        padding=pad,
        content=content,
    )

def state_color(estado: str) -> str:
    e = (estado or "").lower()
    if e == "pendiente":   return "#7c5c00"
    if e == "preparando":  return "#1d4ed8"
    if e == "listo":       return "#16a34a"
    if e == "confirmado":  return "#059669"
    return "#374151"

# --------------------- Estado app ---------------------
class AppState:
    def __init__(self):
        self.modo: Optional[str] = None
        self.menu: List[Dict[str, Any]] = []
        self.carrito: List[Dict[str, Any]] = []
        self.pedido_id: Optional[int] = None
        self.cliente_nombre: str = ""

    def total(self) -> float:
        return sum(float(p.get("precio", 0)) for p in self.carrito)

    def clear_cart(self):
        self.carrito.clear()

state = AppState()

# --------------------- Vistas ---------------------
def LandingView(page: ft.Page):
    page.appbar = ft.AppBar(
        bgcolor=PANEL,
        toolbar_height=64,
        leading=ft.Icon(name="local_cafe_rounded"),
        title=ft.Text("Cafetería Universitaria", weight=ft.FontWeight.W_700),
        actions=[
            ft.Container(
                content=ft.Text("PWA", size=12, color="#cbd5e1"),
                bgcolor=BADGE,
                padding=ft.padding.symmetric(5, 10),
                border_radius=999,
            ),
            ft.Container(width=8),
        ],
    )

    def pick(mode: str):
        state.modo = mode
        state.cliente_nombre = state.cliente_nombre or ""
        page.go("/menu")

    def option_card(title: str, desc: str, icon_name: str, on_click):
        c = box_container(
            ft.Column(
                controls=[
                    ft.Icon(name=icon_name, size=64),
                    ft.Text(title, weight=ft.FontWeight.W_700, size=20),
                    ft.Text(desc, color=MUTED, size=14, text_align=ft.TextAlign.CENTER),
                    ft.FilledButton("Elegir", on_click=on_click),
                ],
                spacing=10,
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            pad=22
        )
        c.width = 520
        c.height = 260
        return c

    content = ft.Column(
        [
            card_container(
                ft.Column(
                    [
                        ft.Text("Bienvenido 👋", size=30, weight=ft.FontWeight.W_700, text_align=ft.TextAlign.CENTER),
                        ft.Text("Elige cómo será tu pedido:", color=MUTED, size=15, text_align=ft.TextAlign.CENTER),
                    ],
                    spacing=6,
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                pad=20,
            ),
            ft.Row(
                [
                    option_card("Comer aquí", "Prepara tu pedido para consumo en sala.", "restaurant",
                                lambda e: pick("Comer aquí")),
                    option_card("Para llevar", "Empacaremos tu pedido para llevar.", "takeout_dining",
                                lambda e: pick("Para llevar")),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=24,
                wrap=True,
            ),
        ],
        spacing=22,
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    page.views.append(
        ft.View(
            route="/",
            controls=[
                ft.Container(content=content, expand=True, alignment=ft.alignment.center, bgcolor=BG, padding=16)
            ],
        )
    )

def MenuView(page: ft.Page):
    # Header
    cart_badge = ft.Container(
        content=ft.Text("0 productos", size=12, color="#cbd5e1"),
        bgcolor=BADGE,
        padding=ft.padding.symmetric(5, 10),
        border_radius=999,
    )
    dot = ft.Container(width=10, height=10, border_radius=999, bgcolor="#ef4444")
    ws_text = ft.Text("Conectando…", color=MUTED)

    page.appbar = ft.AppBar(
        bgcolor=PANEL,
        toolbar_height=64,
        leading=ft.Icon(name="local_cafe_rounded"),
        title=ft.Row(
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[ft.Text("Cafetería Universitaria", size=22, weight=ft.FontWeight.W_700), cart_badge],
        ),
        actions=[ft.Row(spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[ws_text, dot])]
    )

    # Carrito
    cart_list = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)
    total_text = ft.Text("$0.00", weight=ft.FontWeight.W_800)

    def update_badges_and_total():
        cart_badge.content = ft.Text(
            f"{len(state.carrito)} producto{'s' if len(state.carrito)!=1 else ''}",
            size=12, color="#cbd5e1"
        )
        total_text.value = money(state.total())
        page.update()

    def render_cart():
        cart_list.controls.clear()
        if not state.carrito:
            cart_list.controls.append(
                ft.Container(content=ft.Text("Agrega productos del menú", color=MUTED),
                             padding=10, alignment=ft.alignment.center)
            )
        else:
            for idx, p in enumerate(state.carrito):
                cart_list.controls.append(
                    box_container(
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                ft.Text(p["nombre"], weight=ft.FontWeight.W_600),
                                ft.Text(money(p["precio"]), color=MUTED),
                                ft.TextButton("Quitar", style=ft.ButtonStyle(color="#fca5a5"),
                                              on_click=lambda e, i=idx: remove_from_cart(i)),
                            ],
                        ),
                        pad=10,
                    )
                )
        page.update()

    def add_to_cart(prod: Dict[str, Any]):
        state.carrito.append(prod); render_cart(); update_badges_and_total()

    def remove_from_cart(index: int):
        del state.carrito[index]; render_cart(); update_badges_and_total()

    def clear_cart(e=None):
        state.clear_cart(); render_cart(); update_badges_and_total()

    # Grid de menú
    menu_grid = ft.ResponsiveRow(run_spacing=14, spacing=14)

    def render_menu():
        menu_grid.controls.clear()
        for p in state.menu:
            card = box_container(
                ft.Column(
                    spacing=8,
                    controls=[
                        ft.Text(p["nombre"], weight=ft.FontWeight.W_600, size=16),
                        ft.Text(p.get("descripcion", ""), color=MUTED),
                        ft.Text(money(p["precio"]), weight=ft.FontWeight.W_700),
                        ft.Row(
                            alignment=ft.MainAxisAlignment.END,
                            controls=[
                                ft.FilledButton(
                                    "Agregar",
                                    icon="add_rounded",
                                    style=ft.ButtonStyle(
                                        shape=ft.RoundedRectangleBorder(radius=10),
                                        bgcolor={"": BLUE600, "hovered": BLUE700},
                                        color=WHITE,
                                    ),
                                    on_click=lambda e, prod=p: add_to_cart(prod),
                                )
                            ],
                        ),
                    ],
                ),
                pad=14,
            )
            menu_grid.controls.append(ft.Container(card, col={"xs": 12, "md": 6, "lg": 4}))
        page.update()

    # Cards
    menu_card = card_container(
        ft.Column(
            spacing=0,
            controls=[
                ft.Container(
                    padding=ft.padding.symmetric(12, 16),
                    border=ft.border.only(bottom=ft.BorderSide(1, BORDER)),
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[ft.Text("Menú", size=18, weight=ft.FontWeight.W_700), tag_chip("elige tus productos", BADGE)],
                    ),
                ),
                ft.Container(menu_grid, padding=16),
            ],
        )
    )

    name_field = ft.TextField(
        value=state.cliente_nombre,
        label="Nombre para el pedido",
        hint_text="Ej. Ana Pérez",
        bgcolor=BOX,
        border_color=BORDER,
        focused_border_color=BLUE600,
        cursor_color=WHITE,
        text_size=14,
        border_radius=10,
        on_change=lambda e: setattr(state, "cliente_nombre", e.control.value.strip()),
    )

    name_wrapper = box_container(
        ft.Column(
            spacing=6,
            controls=[
                ft.Text("¿Cómo te llamas?", size=12, color=MUTED),
                name_field,
            ],
        ),
        pad=12,
    )

    cart_card = ft.Container(
        bgcolor=PANEL, border=ft.border.all(1, BORDER), border_radius=14, padding=14,
        content=ft.Column(
            spacing=12,
            controls=[
                ft.Text("Tu pedido", size=18, weight=ft.FontWeight.W_700),
                name_wrapper,
                ft.Container(content=cart_list, height=320),
                ft.Container(
                    border=ft.border.only(top=ft.BorderSide(1, BORDER)), padding=ft.padding.only(top=8),
                    content=ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                   controls=[ft.Text("Total", color=MUTED), total_text]),
                ),
                ft.FilledButton("Enviar pedido", icon="send_rounded",
                                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
                                on_click=lambda e: enviar_pedido()),
                ft.OutlinedButton("Vaciar", icon="delete_outline",
                                  style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10),
                                                       side=ft.BorderSide(1, BORDER), color="#cbd5e1"),
                                  on_click=clear_cart),
                ft.Text("Al enviar, verás el estado del pedido.", color=MUTED, size=12),
            ],
        ),
    )

    # Layout
    layout = ft.ResponsiveRow(
        controls=[ft.Container(menu_card, col={"xs": 12, "md": 12, "lg": 8}),
                  ft.Container(cart_card, col={"xs": 12, "md": 12, "lg": 4})],
        run_spacing=18, spacing=18, expand=True,
    )
    layout_wrapper = ft.Container(layout, expand=True, bgcolor=BG, padding=16)

    # Carga inicial menú
    try:
        state.menu = requests.get(f"{API_URL}/menu", timeout=10).json()
    except Exception:
        state.menu = []
        menu_grid.controls.append(ft.Text("No se pudo cargar el menú.", color=MUTED))
        page.update()
    else:
        render_menu()
    render_cart()
    update_badges_and_total()

    # Enviar pedido
    def enviar_pedido():
        if not state.carrito:
            page.snack_bar = ft.SnackBar(ft.Text("Añade al menos un producto.")); page.snack_bar.open = True; page.update(); return
        payload = {
            "productos": [p["id"] for p in state.carrito],
            "total": state.total(),
            "estado": "pendiente",
            "modo": state.modo or "",
            "cliente_nombre": state.cliente_nombre.strip(),
        }
        try:
            r = requests.post(f"{API_URL}/pedidos", json=payload, timeout=10)
        except Exception:
            page.snack_bar = ft.SnackBar(ft.Text("Sin conexión. Intenta de nuevo.")); page.snack_bar.open = True; page.update(); return

        if r.status_code == 200:
            d = r.json()
            state.pedido_id = d.get("id")
            state.clear_cart()
            page.go(f"/estado/{state.pedido_id}")
        else:
            page.snack_bar = ft.SnackBar(ft.Text(f"Error: {r.status_code}")); page.snack_bar.open = True; page.update()

    # Indicador conexión (ping)
    running = True

    async def ping_loop():
        nonlocal running
        while running:
            ok = False
            try:
                rr = requests.get(f"{API_URL}/menu", timeout=6)
                ok = rr.ok
            except Exception:
                ok = False

            if ok:
                ws_text.value = "Conectado"
                dot.bgcolor = "#22c55e"
            else:
                ws_text.value = "Desconectado"
                dot.bgcolor = "#ef4444"

            try:
                page.update()
            except PageDisconnectedException:
                # la vista ya no existe; cortamos el loop
                break

            await asyncio.sleep(8)

    def dispose(_):
        nonlocal running
        running = False

    page.views.append(ft.View(route="/menu", controls=[layout_wrapper]))
    page.views[-1].on_dispose = dispose
    page.run_task(ping_loop)

def StatusView(page: ft.Page, pedido_id: int):
    page.appbar = ft.AppBar(
        bgcolor=PANEL, toolbar_height=64,
        leading=ft.IconButton(icon="arrow_back", on_click=lambda e: page.go("/menu")),
        title=ft.Text(f"Pedido #{str(pedido_id).zfill(3)}", weight=ft.FontWeight.W_700),
        actions=[tag_chip("seguimiento", BADGE), ft.Container(width=8)],
    )

    estado_text = ft.Text("Estado: —", size=20, weight=ft.FontWeight.W_700)
    estado_chip = tag_chip("—", "#374151")
    prods_list = ft.Column(spacing=6)
    total_text = ft.Text("$0.00", weight=ft.FontWeight.W_800)

    cliente_text = ft.Text("", color=MUTED, size=13, italic=True, opacity=0.0)

    info_card = card_container(
        ft.Column(
            spacing=10,
            controls=[
                ft.Row([ft.Text("Estado del pedido", weight=ft.FontWeight.W_700, size=18), estado_chip],
                       alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                estado_text,
                cliente_text,
                ft.Text("Productos", weight=ft.FontWeight.W_700),
                box_container(prods_list, pad=10),
                ft.Row([ft.Text("Total", color=MUTED), total_text], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ],
        ),
        pad=14,
    )
    hint = ft.Text("Esta pantalla se actualiza automáticamente.", color=MUTED, size=12)

    page.views.append(
        ft.View(route=f"/estado/{pedido_id}",
                controls=[ft.Container(content=ft.Column([info_card, hint], spacing=12),
                                       padding=16, expand=True, bgcolor=BG)])
    )

    is_running = True
    async def poll_status():
        nonlocal is_running
        while is_running:
            try:
                pedido = None
                try:
                    r = requests.get(f"{API_URL}/pedidos/{pedido_id}", timeout=8)
                    if r.status_code == 200:
                        pedido = r.json()
                except Exception:
                    pedido = None
                if not pedido:
                    data = requests.get(f"{API_URL}/pedidos", timeout=8).json()
                    for it in data:
                        if int(it.get("id")) == int(pedido_id):
                            pedido = it; break
                if pedido:
                    est = str(pedido.get("estado", "pendiente"))
                    estado_text.value = f"Estado: {est.capitalize()}"
                    estado_chip.content = ft.Text(est, size=12, color="#e5e7eb")
                    estado_chip.bgcolor = state_color(est)
                    nombre_cliente = (pedido.get("cliente_nombre") or "").strip()
                    if nombre_cliente:
                        cliente_text.value = f"Para: {nombre_cliente}"
                        cliente_text.opacity = 1.0
                    else:
                        cliente_text.value = ""
                        cliente_text.opacity = 0.0
                    prods_list.controls.clear()
                    for name in (pedido.get("productos_nombres") or []):
                        prods_list.controls.append(ft.Text(f"• {name}"))
                    total_text.value = money(pedido.get("total", 0))
                    page.update()
            except Exception:
                pass
            await asyncio.sleep(POLL_SECONDS)

    def on_dispose(e: ft.ControlEvent):
        nonlocal is_running
        is_running = False

    page.run_task(poll_status)
    page.views[-1].on_dispose = on_dispose

def BaristaView(page: ft.Page):
    # ---------- AppBar ----------
    page.appbar = ft.AppBar(
        bgcolor=PANEL,
        toolbar_height=64,
        title=ft.Text("Pedidos en curso", weight=ft.FontWeight.W_700),
    )

    # ---------- UI helpers ----------
    def chip_estado(e: str):
        return tag_chip((e or "").lower(), state_color(e))

    def pill(text: str):
        return ft.Container(
            content=ft.Text(text, size=12, color="#cbd5e1"),
            bgcolor=BADGE,
            padding=ft.padding.symmetric(5, 10),
            border_radius=999,
        )

    # ---------- Controles cabecera ----------
    show_ready = ft.Switch(label="Mostrar listos", value=False)
    count_badge = pill("0 pedidos")
    refresh_btn = ft.FilledTonalButton("Actualizar", icon="refresh", on_click=lambda e: reload())

    header = ft.Row(
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            count_badge,
            ft.Row(controls=[show_ready, refresh_btn], spacing=12),
        ],
    )

    # ---------- Lista scrollable ----------
    list_view = ft.ListView(expand=True, spacing=10, auto_scroll=False)

    root = ft.Container(
        content=ft.Column(
            [
                header,
                ft.Container(
                    content=list_view,
                    expand=True,
                    bgcolor=PANEL,
                    border=ft.border.all(1, BORDER),
                    border_radius=14,
                    padding=12,
                ),
            ],
            expand=True,
            spacing=12,
        ),
        expand=True,
        padding=16,
        bgcolor=BG,
    )

    page.views.append(ft.View("/barista", controls=[root]))

    # ========== API helpers ==========
    def api_get_pedidos() -> list[dict]:
        try:
            r = requests.get(f"{API_URL}/pedidos", timeout=10)
            r.raise_for_status()
            return r.json()
        except Exception as ex:
            page.snack_bar = ft.SnackBar(ft.Text(f"Error cargando pedidos: {ex}"))
            page.snack_bar.open = True
            page.update()
            return []

    def api_put_estado(pid: int, estado: str) -> tuple[bool, str]:
        try:
            r = requests.put(
                f"{API_URL}/pedidos/{pid}/estado",
                json={"estado": estado},
                timeout=10,
            )
            if r.status_code == 200:
                return True, "OK"
            return False, f"{r.status_code}: {r.text}"
        except Exception as ex:
            return False, str(ex)

    # ========== Acciones ==========
    def set_preparando(pid: int):
        ok, msg = api_put_estado(pid, "preparando")
        if not ok:
            page.snack_bar = ft.SnackBar(ft.Text(f"No se pudo poner en PREPARANDO: {msg}"))
            page.snack_bar.open = True
        reload()

    def set_listo(pid: int):
        # Diálogo de confirmación robusto
        def close():
            dlg.open = False
            page.update()

        def do_listo(_):
            ok, msg = api_put_estado(pid, "listo")
            close()
            if not ok:
                page.snack_bar = ft.SnackBar(ft.Text(f"No se pudo poner en LISTO: {msg}"))
                page.snack_bar.open = True
            reload()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Confirmar"),
            content=ft.Text(f"¿Notificar al cliente que el pedido #{pid} está LISTO?"),
            actions_alignment=ft.MainAxisAlignment.END,
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: close()),
                ft.FilledButton("Sí, notificar", icon="check_circle", on_click=do_listo),
            ],
        )
        page.dialog = dlg
        dlg.open = True
        page.update()

    # ========== Render ==========
    current: list[dict] = []

    def make_row(p: dict) -> ft.Control:
        pid = int(p["id"])
        prods = ", ".join(p.get("productos_nombres") or [])
        total = money(p.get("total", 0))
        est = (p.get("estado") or "pendiente").lower()

        left = ft.Column(
            spacing=4,
            controls=[
                ft.Text(str(pid).zfill(3), weight=ft.FontWeight.W_800, size=16),
                ft.Text(prods, selectable=True),
            ],
        )

        middle = ft.Row(
            spacing=16,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[ft.Text(total, weight=ft.FontWeight.W_700), chip_estado(est)],
        )

        right = ft.Row(
            spacing=8,
            controls=[
                ft.FilledTonalButton("Preparando", icon="coffee", on_click=lambda e, _pid=pid: set_preparando(_pid)),
                ft.FilledTonalButton("Listo", icon="check_circle", on_click=lambda e, _pid=pid: set_listo(_pid)),
            ],
        )

        return ft.Container(
            bgcolor=BOX,
            border=ft.border.all(1, BORDER),
            border_radius=10,
            padding=12,
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[left, middle, right],
            ),
        )

    def render(data: list[dict]):
        items = data
        if not show_ready.value:
            items = [x for x in data if (x.get("estado", "").lower() not in ("listo", "confirmado"))]

        list_view.controls.clear()
        for p in items:
            list_view.controls.append(make_row(p))

        count_badge.content = ft.Text(
            f"{len(items)} pedido{'s' if len(items)!=1 else ''}",
            size=12, color="#cbd5e1",
        )
        page.update()

    def reload():
        nonlocal current
        current = api_get_pedidos()
        render(current)

    # Cambiar filtro
    show_ready.on_change = lambda e: render(current)

    # Primera carga
    reload()

    # Auto-refresh cada 3s
    running = True
    
    async def loop_refresh():
        nonlocal running
        while running:
            await asyncio.sleep(3)
            # si la vista ya está cerrada, sal del loop
            try:
                reload()
            except PageDisconnectedException:
                break
            # reload() hace page.update() indirectamente; por si acaso:
            try:
                page.update()
            except PageDisconnectedException:
                running = False
                return

    def on_dispose(_):
        nonlocal running
        running = False

    page.views[-1].on_dispose = on_dispose
    page.run_task(loop_refresh)


def WallboardView(page: ft.Page):
    page.appbar = ft.AppBar(
        bgcolor=PANEL, toolbar_height=64,
        title=ft.Text("Pantalla de pedidos", weight=ft.FontWeight.W_700),
        actions=[tag_chip("live", BADGE), ft.Container(width=8)],
    )

    # Grids
    prep_grid = ft.GridView(expand=1, runs_count=4, max_extent=220, child_aspect_ratio=1.6, spacing=12, run_spacing=12)
    ready_grid = ft.GridView(expand=1, runs_count=4, max_extent=220, child_aspect_ratio=1.6, spacing=12, run_spacing=12)

    def make_card(p):
        is_ready = str(p.get("estado", "")).lower() in ("listo", "confirmado")
        return box_container(
            ft.Container(
                content=ft.Text(str(p["id"]).zfill(3), size=44, weight=ft.FontWeight.W_800,
                                color="#86efac" if is_ready else "#a5b4fc"),
                alignment=ft.alignment.center, height=86
            ),
            pad=10
        )

    def render_from_data(data: list[dict]):
        prep_grid.controls.clear(); ready_grid.controls.clear()
        for p in sorted(data, key=lambda x: int(x["id"]), reverse=True):
            (ready_grid if str(p.get("estado","")).lower() in ("listo","confirmado") else prep_grid).controls.append(
                make_card(p)
            )
        page.update()

    async def load_all():
        try:
            def _do():
                r = requests.get(f"{API_URL}/pedidos", timeout=8); r.raise_for_status(); return r.json()
            data = await asyncio.to_thread(_do)
        except Exception:
            data = []
        render_from_data(data)

    cols = ft.ResponsiveRow(
        controls=[
            ft.Container(
                card_container(ft.Column([
                    ft.Row([ft.Text("En preparación", size=20, weight=ft.FontWeight.W_700),
                            tag_chip("pendiente / preparando", "#1d4ed8")],
                           alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Container(prep_grid, height=520, expand=True)
                ])),
                col={"xs": 12, "md": 6}
            ),
            ft.Container(
                card_container(ft.Column([
                    ft.Row([ft.Text("Para retirar", size=20, weight=ft.FontWeight.W_700),
                            tag_chip("listo", "#16a34a")],
                           alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Container(ready_grid, height=520, expand=True)
                ])),
                col={"xs": 12, "md": 6}
            ),
        ],
        run_spacing=16, spacing=16, expand=True
    )
    page.views.append(ft.View("/pantalla", controls=[ft.Container(content=cols, padding=16, bgcolor=BG)]))

    # Loop de refresco
    running = True
    async def loop_refresh():
        nonlocal running
        while running:
            await load_all()
            await asyncio.sleep(3)

    def dispose(_):
        nonlocal running
        running = False

    page.views[-1].on_dispose = dispose
    page.run_task(loop_refresh)

# --------------------- Router ---------------------
def app(page: ft.Page):
    page.title = "Cafetería Universitaria"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = BG

    def route_change(e: ft.RouteChangeEvent):
        page.views.clear()
        if page.route == "/":
            LandingView(page)
        elif page.route.startswith("/menu"):
            MenuView(page)
        elif page.route.startswith("/estado/"):
            try:
                pedido_id = int(page.route.split("/estado/")[1])
            except Exception:
                pedido_id = state.pedido_id or 0
            StatusView(page, pedido_id)
        elif page.route.startswith("/barista"):
            BaristaView(page)
        elif page.route.startswith("/pantalla"):
            WallboardView(page)
        else:
            page.go("/")
        page.update()

    page.on_route_change = route_change
    page.go(page.route or "/")

ft.app(target=app, view=ft.AppView.WEB_BROWSER)
