"""
modulos/ventas/__init__.py
============================
Módulo Ventas — Venta, Cotizaciones, CxC.
"""
import customtkinter as ctk
import datetime
from tkinter import messagebox
from core.permisos import puede


# ─── Placeholder genérico ──────────────────────────────────────────────────────

def _placeholder(parent, estilos, icono, titulo, desc):
    col = estilos["colores"]
    f = ctk.CTkFrame(parent, corner_radius=0, fg_color=col["fondo_oscuro"])
    ctk.CTkLabel(f, text=f"{icono}  {titulo}",
                 font=estilos["fuentes"]["titulo"],
                 text_color=col["texto_oscuro"]).pack(pady=(30, 10))
    t = ctk.CTkFrame(f, fg_color=col["tarjetas"], corner_radius=12)
    t.pack(pady=10, padx=30, fill="both", expand=True)
    ctk.CTkLabel(t, text=icono, font=("Roboto Mono", 48),
                 text_color=col["principal"]).pack(pady=(50, 10))
    ctk.CTkLabel(t, text=f"{desc}\nSubmódulo en desarrollo.",
                 font=estilos["fuentes"]["normal"],
                 text_color="#4A6FA5", justify="center").pack()
    return f


# ══════════════════════════════════════════════════════════════════════════════
# COTIZACIONES
# ══════════════════════════════════════════════════════════════════════════════

class SubmoduloCotizaciones(ctk.CTkFrame):
    """Submódulo de Cotizaciones — lista + modal de creación/edición."""

    COLS   = ["Número", "Fecha", "Cliente", "Total (USD)", "Estado", ""]
    WIDTHS = [130, 100, 280, 110, 110, 76]

    ESTADO_COLOR = {
        "Pendiente":  "#F4A261",
        "Enviada":    "#00B4D8",
        "Aprobada":   "#2EC4B6",
        "Rechazada":  "#E63946",
    }

    def __init__(self, parent, estilos, permisos=None):
        super().__init__(parent, corner_radius=0,
                         fg_color=estilos["colores"]["fondo_oscuro"])
        self.estilos  = estilos
        self.permisos = permisos or {}
        self.col      = estilos["colores"]
        self.fnt      = estilos["fuentes"]
        self._construir_ui()
        self.after(0, self.cargar_datos)

    # ─── UI ──────────────────────────────────────────────────────────────────

    def _construir_ui(self):
        col = self.col
        fnt = self.fnt

        # ── barra superior ────────────────────────────────────────────────
        bar = ctk.CTkFrame(self, height=52, corner_radius=0, fg_color="#020C1B")
        bar.pack(fill="x")
        bar.pack_propagate(False)

        ctk.CTkLabel(bar, text="📋  Cotizaciones",
                     font=fnt["titulo"],
                     text_color=col["principal"]).pack(side="left", padx=16, pady=8)

        ctk.CTkButton(bar, text="➕ Nueva Cotización",
                      fg_color=col["principal"], text_color="#0A192F",
                      hover_color=col.get("principal_hover", "#00C8D4"),
                      width=180, height=34,
                      command=self._abrir_modal).pack(side="right", padx=12, pady=8)

        self.busq_var = ctk.StringVar()
        ctk.CTkEntry(bar, textvariable=self.busq_var, width=240, height=32,
                     placeholder_text="🔍 Buscar por número o cliente…"
                     ).pack(side="right", padx=4, pady=10)

        # ── contenedor tabla ──────────────────────────────────────────────
        cont = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        cont.pack(fill="both", expand=True, padx=12, pady=8)

        # cabecera fija
        hdr = ctk.CTkFrame(cont, corner_radius=0, fg_color="#0A192F", height=34)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        for c, w in zip(self.COLS, self.WIDTHS):
            ctk.CTkLabel(hdr, text=c, width=w, anchor="center",
                         text_color=col["texto_claro"],
                         font=fnt["normal"]).pack(side="left")

        # área scrollable de filas
        self.scroll = ctk.CTkScrollableFrame(cont, corner_radius=0,
                                             fg_color=col["fondo_oscuro"])
        self.scroll.pack(fill="both", expand=True)

        # trace después de construir scroll
        self.busq_var.trace_add("write", lambda *_: self.cargar_datos(self.busq_var.get()))

    # ─── Datos ───────────────────────────────────────────────────────────────

    def cargar_datos(self, filtro: str = ""):
        from core.database import listar_cotizaciones
        col = self.col
        fnt = self.fnt

        for w in self.scroll.winfo_children():
            w.destroy()

        try:
            rows = listar_cotizaciones(filtro)
        except Exception as e:
            ctk.CTkLabel(self.scroll, text=f"Error al cargar: {e}",
                         text_color="#E63946", font=fnt["normal"]).pack(pady=20)
            return

        for i, r in enumerate(rows):
            bg = col["tarjetas"] if i % 2 == 0 else col["fondo_oscuro"]
            fila = ctk.CTkFrame(self.scroll, corner_radius=0, fg_color=bg, height=34)
            fila.pack(fill="x")
            fila.pack_propagate(False)

            estado_c = self.ESTADO_COLOR.get(r["estado"], col["texto_claro"])
            vals = [
                (r["numero"],           col["texto_claro"]),
                (r["fecha"],            col["texto_claro"]),
                (r["cliente_nombre"],   col["texto_claro"]),
                (f'$ {r["total"]:.2f}', col["principal"]),
                (r["estado"],           estado_c),
            ]
            for (v, tc), w in zip(vals, self.WIDTHS[:-1]):
                ctk.CTkLabel(fila, text=v, width=w, anchor="center",
                             text_color=tc, font=fnt["normal"]).pack(side="left")

            btn_f = ctk.CTkFrame(fila, width=76, corner_radius=0,
                                 fg_color="transparent")
            btn_f.pack(side="left")
            btn_f.pack_propagate(False)

            ctk.CTkButton(btn_f, text="🗑", width=36, height=28,
                          fg_color="#1A3550",
                          hover_color=col.get("error", "#E63946"),
                          text_color=col.get("error", "#E63946"),
                          command=lambda rid=r["id"]: self._eliminar(rid)
                          ).pack(side="right", padx=2)
            ctk.CTkButton(btn_f, text="✏️", width=32, height=28,
                          fg_color="#1A3550",
                          hover_color=col["principal"],
                          text_color=col["texto_claro"],
                          command=lambda rid=r["id"]: self._abrir_modal(rid)
                          ).pack(side="right", padx=2)

    # ─── Acciones ─────────────────────────────────────────────────────────────

    def _eliminar(self, rid):
        from core.database import eliminar_cotizacion
        if messagebox.askyesno("Eliminar", "¿Eliminar esta cotización?"):
            eliminar_cotizacion(rid)
            self.cargar_datos(self.busq_var.get())

    # ─── MODAL ────────────────────────────────────────────────────────────────

    def _abrir_modal(self, cot_id=None):
        from core.database import (obtener_clientes, get_items_inventario,
                                   listar_modelos_sistemas, listar_modelos_maquinas,
                                   add_cotizacion, update_cotizacion,
                                   get_cotizacion_completa, get_next_cotizacion_numero)
        col = self.col
        fnt = self.fnt

        row_data = get_cotizacion_completa(cot_id) if cot_id else {}

        modal = ctk.CTkToplevel(self)
        modal.title("Editar Cotización" if cot_id else "Nueva Cotización")
        modal.geometry("920x720")
        modal.grab_set()
        modal.configure(fg_color=col["fondo_oscuro"])

        # ── helpers ──
        def lbl(parent, text):
            ctk.CTkLabel(parent, text=text, text_color=col["texto_claro"],
                         font=fnt["normal"]).pack(anchor="w", padx=20, pady=(6, 1))

        def ent(parent, width=380, val=""):
            e = ctk.CTkEntry(parent, width=width, height=32)
            e.pack(padx=20, anchor="w")
            if val:
                e.insert(0, val)
            return e

        # ── fila 1: número / fecha / estado ──
        r1 = ctk.CTkFrame(modal, fg_color="transparent")
        r1.pack(fill="x", padx=20, pady=(12, 0))

        ctk.CTkLabel(r1, text="Número", text_color=col["texto_claro"],
                     font=fnt["normal"]).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(r1, text="Fecha *", text_color=col["texto_claro"],
                     font=fnt["normal"]).grid(row=0, column=1, sticky="w", padx=(16, 0))
        ctk.CTkLabel(r1, text="Estado", text_color=col["texto_claro"],
                     font=fnt["normal"]).grid(row=0, column=2, sticky="w", padx=(16, 0))

        e_num = ctk.CTkEntry(r1, width=180, height=32)
        e_num.grid(row=1, column=0)
        e_num.insert(0, row_data.get("numero") or get_next_cotizacion_numero())

        e_fecha = ctk.CTkEntry(r1, width=130, height=32)
        e_fecha.grid(row=1, column=1, padx=(16, 0))
        e_fecha.insert(0, row_data.get("fecha") or
                       datetime.date.today().strftime("%d/%m/%Y"))

        estados = ["Pendiente", "Enviada", "Aprobada", "Rechazada"]
        cb_estado = ctk.CTkComboBox(r1, values=estados, width=140, state="readonly")
        cb_estado.grid(row=1, column=2, padx=(16, 0))
        cb_estado.set(row_data.get("estado", "Pendiente"))

        # ── cliente ──
        lbl(modal, "Cliente *")
        clientes_list = obtener_clientes()
        cli_nombres = ["(Sin cliente)"] + [
            f'{c["rif"]} — {c["razon_social"]}' for c in clientes_list
        ]
        cb_cli = ctk.CTkComboBox(modal, values=cli_nombres,
                                 width=880, state="readonly")
        cb_cli.pack(padx=20, anchor="w")
        if row_data.get("cliente_id"):
            match = next((f'{c["rif"]} — {c["razon_social"]}'
                          for c in clientes_list
                          if c["id"] == row_data["cliente_id"]), None)
            cb_cli.set(match or cli_nombres[0])
        else:
            cb_cli.set(cli_nombres[0])

        # ── sección agregar ítem ──
        ctk.CTkFrame(modal, height=2, fg_color=col["principal"]).pack(
            fill="x", padx=20, pady=(10, 4))
        ctk.CTkLabel(modal, text="  Agregar ítem",
                     text_color=col["principal"],
                     font=fnt["subtitulo"]).pack(anchor="w", padx=20)

        add_row = ctk.CTkFrame(modal, fg_color=col["tarjetas"], corner_radius=8)
        add_row.pack(fill="x", padx=20, pady=(4, 0))

        ctk.CTkLabel(add_row, text="Tipo", text_color=col["texto_claro"],
                     font=fnt["normal"]).grid(row=0, column=0,
                                              sticky="w", padx=(10, 4), pady=(6, 1))
        tipos = ["Inventario", "Sistema", "Máquina Fiscal"]
        cb_tipo = ctk.CTkComboBox(add_row, values=tipos, width=140,
                                  state="readonly",
                                  command=lambda v: _on_tipo_change(v))
        cb_tipo.grid(row=1, column=0, padx=(10, 4), pady=(0, 8))
        cb_tipo.set("Inventario")

        ctk.CTkLabel(add_row, text="Ítem / Servicio",
                     text_color=col["texto_claro"],
                     font=fnt["normal"]).grid(row=0, column=1,
                                              sticky="w", padx=4, pady=(6, 1))
        cb_item_add = ctk.CTkComboBox(add_row, values=[""], width=360,
                                      state="readonly",
                                      command=lambda v: _on_item_select(v))
        cb_item_add.grid(row=1, column=1, padx=4, pady=(0, 8))

        ctk.CTkLabel(add_row, text="Cant.", text_color=col["texto_claro"],
                     font=fnt["normal"]).grid(row=0, column=2, sticky="w",
                                              padx=4, pady=(6, 1))
        e_cant_add = ctk.CTkEntry(add_row, width=70, height=32)
        e_cant_add.grid(row=1, column=2, padx=4, pady=(0, 8))
        e_cant_add.insert(0, "1")

        ctk.CTkLabel(add_row, text="Precio USD",
                     text_color=col["texto_claro"],
                     font=fnt["normal"]).grid(row=0, column=3, sticky="w",
                                              padx=4, pady=(6, 1))
        e_precio_add = ctk.CTkEntry(add_row, width=90, height=32)
        e_precio_add.grid(row=1, column=3, padx=4, pady=(0, 8))
        e_precio_add.insert(0, "0.00")

        ctk.CTkButton(add_row, text="➕ Agregar",
                      fg_color=col["principal"], text_color="#0A192F",
                      hover_color=col.get("principal_hover", "#00C8D4"),
                      width=110, height=32,
                      command=lambda: _agregar_item()
                      ).grid(row=1, column=4, padx=(8, 10), pady=(0, 8))

        # datos para lookup
        _items_inv   = get_items_inventario()
        _mods_sis    = listar_modelos_sistemas()
        _mods_maq    = listar_modelos_maquinas()
        _current_ref = {"id": None, "tipo": "Inventario"}

        def _on_tipo_change(tipo):
            _current_ref["tipo"] = tipo
            if tipo == "Inventario":
                opts = [f'{it["codigo"]} — {it["nombre"]}' for it in _items_inv]
            elif tipo == "Sistema":
                opts = [m[1] for m in _mods_sis]
            else:
                opts = [m[1] for m in _mods_maq]
            cb_item_add.configure(values=opts if opts else ["(Sin registros)"])
            cb_item_add.set(opts[0] if opts else "")
            _on_item_select(cb_item_add.get())

        def _on_item_select(val):
            tipo = _current_ref["tipo"]
            if tipo == "Inventario":
                match = next((it for it in _items_inv
                              if f'{it["codigo"]} — {it["nombre"]}' == val), None)
                if match:
                    _current_ref["id"] = match["id"]
                    e_precio_add.delete(0, "end")
                    e_precio_add.insert(0, f'{match.get("precio_venta", 0):.2f}')
            elif tipo == "Sistema":
                match = next((m for m in _mods_sis if m[1] == val), None)
                _current_ref["id"] = match[0] if match else None
            else:
                match = next((m for m in _mods_maq if m[1] == val), None)
                _current_ref["id"] = match[0] if match else None

        _on_tipo_change("Inventario")

        # ── tabla de ítems ──
        items_outer = ctk.CTkFrame(modal, fg_color="transparent")
        items_outer.pack(fill="x", padx=20, pady=(8, 0))

        IT_COLS   = ["Tipo", "Descripción", "Cant.", "Precio USD", "Subtotal", ""]
        IT_WIDTHS = [100, 350, 60, 100, 100, 38]
        it_hdr = ctk.CTkFrame(items_outer, corner_radius=0,
                              fg_color="#0A192F", height=28)
        it_hdr.pack(fill="x")
        it_hdr.pack_propagate(False)
        for c, w in zip(IT_COLS, IT_WIDTHS):
            ctk.CTkLabel(it_hdr, text=c, width=w, anchor="center",
                         text_color=col["texto_claro"],
                         font=fnt["normal"]).pack(side="left")

        it_scroll = ctk.CTkScrollableFrame(items_outer, corner_radius=0,
                                           height=160, fg_color=col["tarjetas"])
        it_scroll.pack(fill="x")

        total_var = ctk.StringVar(value="Total:  $ 0.00")
        ctk.CTkLabel(modal, textvariable=total_var,
                     text_color=col["principal"],
                     font=fnt["subtitulo"]).pack(anchor="e", padx=24, pady=(4, 0))

        _items_cot = []
        if row_data.get("items"):
            for it in row_data["items"]:
                _items_cot.append({
                    "tipo":            it["tipo"],
                    "item_ref_id":     it["item_ref_id"],
                    "descripcion":     it["descripcion"],
                    "cantidad":        it["cantidad"],
                    "precio_unitario": it["precio_unitario"],
                })

        def _render_items():
            for w in it_scroll.winfo_children():
                w.destroy()
            total = 0.0
            for idx, it in enumerate(_items_cot):
                bg2 = col["tarjetas"] if idx % 2 == 0 else col["fondo_oscuro"]
                sub = it["cantidad"] * it["precio_unitario"]
                total += sub
                fila2 = ctk.CTkFrame(it_scroll, corner_radius=0,
                                     fg_color=bg2, height=28)
                fila2.pack(fill="x")
                fila2.pack_propagate(False)
                vals2 = [
                    it["tipo"],
                    it["descripcion"],
                    f'{it["cantidad"]:.2f}',
                    f'$ {it["precio_unitario"]:.2f}',
                    f'$ {sub:.2f}',
                ]
                for v, w in zip(vals2, IT_WIDTHS[:-1]):
                    ctk.CTkLabel(fila2, text=v, width=w, anchor="center",
                                 text_color=col["texto_claro"],
                                 font=fnt["normal"]).pack(side="left")
                ctk.CTkButton(fila2, text="🗑", width=34, height=22,
                              fg_color="transparent",
                              hover_color=col.get("error", "#E63946"),
                              text_color=col.get("error", "#E63946"),
                              command=lambda i=idx: _quitar_item(i)
                              ).pack(side="left")
            total_var.set(f"Total:  $ {total:.2f}")

        def _agregar_item():
            tipo = _current_ref["tipo"]
            desc = cb_item_add.get().strip()
            if not desc or desc == "(Sin registros)":
                return
            try:
                cant = float(e_cant_add.get() or 1)
                prec = float(e_precio_add.get() or 0)
            except ValueError:
                return
            _items_cot.append({
                "tipo":            tipo,
                "item_ref_id":     _current_ref["id"],
                "descripcion":     desc,
                "cantidad":        cant,
                "precio_unitario": prec,
            })
            _render_items()

        def _quitar_item(idx):
            if 0 <= idx < len(_items_cot):
                _items_cot.pop(idx)
                _render_items()

        _render_items()

        # ── observaciones ──
        lbl(modal, "Observaciones")
        e_obs = ctk.CTkEntry(modal, width=880, height=32)
        e_obs.pack(padx=20, anchor="w")
        if row_data.get("observaciones"):
            e_obs.insert(0, row_data["observaciones"])

        # ── error + guardar ──
        err_lbl = ctk.CTkLabel(modal, text="", text_color="#E63946",
                               font=fnt["normal"])
        err_lbl.pack(pady=(4, 0))

        def _guardar():
            from core.session import get_usuario_actual
            num    = e_num.get().strip()
            fecha  = e_fecha.get().strip()
            estado = cb_estado.get()
            obs    = e_obs.get().strip()

            if not num or not fecha:
                err_lbl.configure(text="Número y Fecha son obligatorios.")
                return
            if not _items_cot:
                err_lbl.configure(text="Agregue al menos un ítem.")
                return

            cli_id = None
            sel = cb_cli.get()
            if sel != "(Sin cliente)":
                rif_sel = sel.split(" — ")[0]
                match = next((c for c in clientes_list
                              if c["rif"] == rif_sel), None)
                if match:
                    cli_id = match["id"]

            usuario = get_usuario_actual() or ""
            if cot_id:
                ok = update_cotizacion(cot_id, num, fecha, cli_id,
                                       obs, estado, _items_cot)
            else:
                ok = add_cotizacion(num, fecha, cli_id, obs,
                                    estado, usuario, _items_cot) > 0
            if not ok:
                err_lbl.configure(text="Error al guardar. ¿Número duplicado?")
                return
            modal.destroy()
            self.cargar_datos(self.busq_var.get())

        ctk.CTkButton(modal, text="💾 Guardar Cotización",
                      fg_color=col["principal"], text_color="#0A192F",
                      hover_color=col.get("principal_hover", "#00C8D4"),
                      width=220, height=36,
                      command=_guardar).pack(pady=10)


# ══════════════════════════════════════════════════════════════════════════════
class SubmoduloVenta(ctk.CTkFrame):
    def __init__(self, parent, estilos, permisos=None):
        super().__init__(parent, corner_radius=0,
                         fg_color=estilos["colores"]["fondo_oscuro"])
        self.estilos = estilos
        _placeholder(self, estilos, "🧾", "Venta",
                     "Registro y gestión de ventas.").pack(fill="both", expand=True)


class SubmoduloCxC(ctk.CTkFrame):
    def __init__(self, parent, estilos, permisos=None):
        super().__init__(parent, corner_radius=0,
                         fg_color=estilos["colores"]["fondo_oscuro"])
        self.estilos = estilos
        _placeholder(self, estilos, "💰", "Cuentas por Cobrar",
                     "Control de cuentas por cobrar.").pack(fill="both", expand=True)


# ─── Módulo principal ─────────────────────────────────────────────────────────

class ModuloVentas(ctk.CTkFrame):
    def __init__(self, parent, estilos, permisos=None):
        super().__init__(parent, corner_radius=0,
                         fg_color=estilos["colores"]["fondo_oscuro"])
        self.estilos     = estilos
        self.permisos    = permisos or {}
        self._btn_activo = None
        self._construir_barra_nav()
        self.area = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.area.pack(fill="both", expand=True)
        self._activar_inicial()

    def _construir_barra_nav(self):
        col = self.estilos["colores"]
        barra = ctk.CTkFrame(self, height=50, corner_radius=0, fg_color="#020C1B")
        barra.pack(side="top", fill="x")
        barra.pack_propagate(False)

        self._submodulos = [
            ("Ventas.Venta",        "🧾 Venta",        SubmoduloVenta),
            ("Ventas.Cotizaciones", "📋 Cotizaciones",  SubmoduloCotizaciones),
            ("Ventas.CxC",          "💰 CxC",           SubmoduloCxC),
        ]

        self._nav_btns = []
        for perm_key, label, clase in self._submodulos:
            btn = ctk.CTkButton(
                barra, text=label,
                fg_color="transparent", text_color=col["texto_claro"],
                hover_color=col["tarjetas"],
                width=150, height=40, corner_radius=0,
            )
            btn.configure(command=lambda b=btn, c=clase: self._activar(b, c))
            btn.pack(side="left", padx=2)
            self._nav_btns.append((btn, clase))

    def _activar_inicial(self):
        if self._nav_btns:
            btn, clase = self._nav_btns[0]
            self._activar(btn, clase)

    def _activar(self, btn, clase):
        col = self.estilos["colores"]
        if self._btn_activo:
            self._btn_activo.configure(
                fg_color="transparent", text_color=col["texto_claro"])
        btn.configure(fg_color=col["tarjetas"],
                      text_color=col["texto_oscuro"])
        self._btn_activo = btn
        for w in self.area.winfo_children():
            w.destroy()
        clase(self.area, self.estilos, self.permisos).pack(fill="both", expand=True)
