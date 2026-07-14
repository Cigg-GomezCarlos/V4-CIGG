"""
modulos/ventas/sub_cotizaciones.py
==================================
Submódulo Cotizaciones — lista + modal de creación/edición.

Arreglos:
  • Botón "Guardar" SIEMPRE visible (footer fijo abajo, cuerpo scrollable).
  • Campo "Tipo" es un ComboBox seleccionable (readonly).
  • El precio de la cotización actualiza el precio del producto (en database.py).
  • Selector de Moneda base + panel de equivalencias en vivo.
"""
import customtkinter as ctk
import datetime
from tkinter import messagebox


# ─── Entry con autocompletado (filtra mientras escribes) ───────────────────────

class AutocompleteEntry(ctk.CTkFrame):
    """Entry con dropdown que filtra las opciones a medida que se escribe."""

    def __init__(self, master, values=None, width=300, height=32,
                 placeholder="", on_select=None, colores=None, fuentes=None,
                 allow_free=True, **kw):
        super().__init__(master, fg_color="transparent", **kw)
        self._values     = list(values or [])
        self._on_select  = on_select
        self._col        = colores or {}
        self._fnt        = fuentes or {}
        self._allow_free = allow_free
        self._pop        = None
        self._suppress   = False
        self._var        = ctk.StringVar()

        self.entry = ctk.CTkEntry(self, textvariable=self._var, width=width,
                                  height=height, placeholder_text=placeholder)
        self.entry.pack(fill="both", expand=True)

        self._var.trace_add("write", lambda *_: self._on_type())
        self.entry.bind("<FocusOut>", lambda e: self.after(200, self._close))
        self.entry.bind("<Down>",     lambda e: self._open(force=True))
        self.entry.bind("<Escape>",   lambda e: self._close())

    # API pública ------------------------------------------------------------
    def set_values(self, values):
        self._values = list(values or [])

    def set(self, text):
        self._suppress = True
        self._var.set(text or "")
        self._suppress = False

    def get(self):
        return self._var.get().strip()

    # interno ----------------------------------------------------------------
    def _on_type(self):
        if self._suppress:
            return
        self._open()

    def _open(self, force=False):
        txt = self._var.get().strip().lower()
        if txt:
            matches = [v for v in self._values if txt in v.lower()]
        else:
            matches = list(self._values) if force else []
        if not matches:
            self._close()
            return
        self._render(matches[:60])

    def _render(self, matches):
        self._close()
        top = ctk.CTkToplevel(self)
        top.overrideredirect(True)
        try:
            top.attributes("-topmost", True)
        except Exception:
            pass
        self._pop = top
        x = self.entry.winfo_rootx()
        y = self.entry.winfo_rooty() + self.entry.winfo_height()
        w = max(self.entry.winfo_width(), 180)
        h = min(len(matches) * 30 + 8, 230)
        top.geometry(f"{w}x{h}+{x}+{y}")
        top.configure(fg_color=self._col.get("tarjetas", "#112240"))
        frame = ctk.CTkScrollableFrame(top, corner_radius=0,
                                       fg_color=self._col.get("tarjetas", "#112240"))
        frame.pack(fill="both", expand=True)
        for m in matches:
            ctk.CTkButton(frame, text=m, anchor="w", height=26,
                          fg_color="transparent",
                          text_color=self._col.get("texto_claro", "#E2E8F0"),
                          hover_color=self._col.get("principal_hover", "#00C8D4"),
                          command=lambda val=m: self._pick(val)
                          ).pack(fill="x", padx=2, pady=1)

    def _pick(self, val):
        self.set(val)
        self._close()
        if self._on_select:
            self._on_select(val)

    def _close(self):
        if self._pop is not None:
            try:
                self._pop.destroy()
            except Exception:
                pass
            self._pop = None


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

        cont = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        cont.pack(fill="both", expand=True, padx=12, pady=8)

        hdr = ctk.CTkFrame(cont, corner_radius=0, fg_color="#0A192F", height=34)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        for c, w in zip(self.COLS, self.WIDTHS):
            ctk.CTkLabel(hdr, text=c, width=w, anchor="center",
                         text_color=col["texto_claro"],
                         font=fnt["normal"]).pack(side="left")

        self.scroll = ctk.CTkScrollableFrame(cont, corner_radius=0,
                                             fg_color=col["fondo_oscuro"])
        self.scroll.pack(fill="both", expand=True)

        self.busq_var.trace_add("write",
                                 lambda *_: self.cargar_datos(self.busq_var.get()))

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

        # ══ FOOTER FIJO (siempre visible) — se crea PRIMERO y se ancla abajo ══
        footer = ctk.CTkFrame(modal, height=64, corner_radius=0,
                              fg_color="#020C1B")
        footer.pack(side="bottom", fill="x")
        footer.pack_propagate(False)

        err_lbl = ctk.CTkLabel(footer, text="", text_color="#E63946",
                               font=fnt["normal"])
        err_lbl.pack(side="left", padx=20)

        # ══ CUERPO SCROLLABLE (todo el formulario) ══
        body = ctk.CTkScrollableFrame(modal, corner_radius=0,
                                      fg_color=col["fondo_oscuro"])
        body.pack(side="top", fill="both", expand=True)

        # ── helpers ──
        def lbl(parent, text):
            ctk.CTkLabel(parent, text=text, text_color=col["texto_claro"],
                         font=fnt["normal"]).pack(anchor="w", padx=20, pady=(6, 1))

        # ── fila 1: número / fecha / estado ──
        r1 = ctk.CTkFrame(body, fg_color="transparent")
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

        # ── tasas de cambio (para equivalencias) ──
        try:
            from modulos.monedas.db import leer_todas
            _tasas = leer_todas()
        except Exception:
            _tasas = {}

        # ── cliente (autocomplete: filtra mientras escribes) ──
        lbl(body, "Cliente *  (escribe para filtrar)")
        clientes_list = obtener_clientes()
        cli_nombres = ["(Sin cliente)"] + [
            f'{c["rif"]} — {c["razon_social"]}' for c in clientes_list
        ]
        cb_cli = AutocompleteEntry(body, values=cli_nombres, width=880,
                                   placeholder="RIF o razón social…",
                                   colores=col, fuentes=fnt)
        cb_cli.pack(padx=20, anchor="w")
        if row_data.get("cliente_id"):
            match = next((f'{c["rif"]} — {c["razon_social"]}'
                          for c in clientes_list
                          if c["id"] == row_data["cliente_id"]), None)
            cb_cli.set(match or cli_nombres[0])
        else:
            cb_cli.set(cli_nombres[0])

        # ── sección agregar ítem ──
        ctk.CTkFrame(body, height=2, fg_color=col["principal"]).pack(
            fill="x", padx=20, pady=(10, 4))
        ctk.CTkLabel(body, text="  Agregar ítem",
                     text_color=col["principal"],
                     font=fnt["subtitulo"]).pack(anchor="w", padx=20)

        add_row = ctk.CTkFrame(body, fg_color=col["tarjetas"], corner_radius=8)
        add_row.pack(fill="x", padx=20, pady=(4, 0))

        # datos para lookup
        _items_inv   = get_items_inventario()
        _mods_sis    = listar_modelos_sistemas()
        _mods_maq    = listar_modelos_maquinas()
        _current_ref = {"id": None, "tipo": "Inventario"}

        # Tipo → ComboBox SELECCIONABLE (readonly)
        ctk.CTkLabel(add_row, text="Tipo", text_color=col["texto_claro"],
                     font=fnt["normal"]).grid(row=0, column=0,
                                              sticky="w", padx=(10, 4), pady=(6, 1))
        tipos = ["Inventario", "Sistema", "Máquina Fiscal"]
        cb_tipo = ctk.CTkComboBox(add_row, values=tipos, width=150,
                                  state="readonly",
                                  command=lambda v: _on_tipo_change(v))
        cb_tipo.grid(row=1, column=0, padx=(10, 4), pady=(0, 8))
        cb_tipo.set("Inventario")

        ctk.CTkLabel(add_row, text="Ítem / Servicio",
                     text_color=col["texto_claro"],
                     font=fnt["normal"]).grid(row=0, column=1,
                                              sticky="w", padx=4, pady=(6, 1))
        cb_item_add = AutocompleteEntry(add_row, values=[""], width=340,
                                        placeholder="Escribe para filtrar…",
                                        colores=col, fuentes=fnt,
                                        on_select=lambda v: _on_item_select(v))
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

        def _on_tipo_change(tipo):
            _current_ref["tipo"] = tipo
            _current_ref["id"]   = None
            if tipo == "Inventario":
                opts = [f'{it["codigo"]} — {it["nombre"]}' for it in _items_inv]
            elif tipo == "Sistema":
                opts = [m[1] for m in _mods_sis]
            else:
                opts = [m[1] for m in _mods_maq]
            cb_item_add.set_values(opts if opts else ["(Sin registros)"])
            cb_item_add.set("")

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

        # ── tabla de ítems (frame plano; el body ya scrollea) ──
        items_outer = ctk.CTkFrame(body, fg_color="transparent")
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

        it_body = ctk.CTkFrame(items_outer, corner_radius=0,
                               fg_color=col["tarjetas"])
        it_body.pack(fill="x")

        # ── moneda base + total + equivalencias ──
        MON_LABELS = {
            "USD":      "💵 USD — Dólar",
            "EUR":      "💶 EUR — Euro",
            "VES":      "🇻🇪 VES — Bolívar",
            "USDT":     "🟡 USDT",
            "TASA_EXT": "⚙️ Tasa Externa",
        }
        MON_SIMB = {"USD": "$", "EUR": "€", "VES": "Bs.",
                    "USDT": "₮", "TASA_EXT": "★"}
        _label_to_cod = {v: k for k, v in MON_LABELS.items()}

        mon_row = ctk.CTkFrame(body, fg_color="transparent")
        mon_row.pack(fill="x", padx=20, pady=(6, 0))
        ctk.CTkLabel(mon_row, text="Moneda de la cotización:",
                     text_color=col["texto_claro"],
                     font=fnt["normal"]).pack(side="left")
        cb_moneda = ctk.CTkComboBox(
            mon_row, values=list(MON_LABELS.values()), width=200,
            state="readonly", command=lambda v: _render_items())
        cb_moneda.pack(side="left", padx=(8, 0))
        cb_moneda.set(MON_LABELS.get(row_data.get("moneda", "USD"),
                                     MON_LABELS["USD"]))

        total_var = ctk.StringVar(value="Total:  $ 0.00")
        ctk.CTkLabel(body, textvariable=total_var,
                     text_color=col["principal"],
                     font=fnt["subtitulo"]).pack(anchor="e", padx=24, pady=(4, 0))

        equiv_var = ctk.StringVar(value="")
        ctk.CTkLabel(body, textvariable=equiv_var,
                     text_color=col["texto_claro"],
                     font=fnt["normal"]).pack(anchor="e", padx=24, pady=(0, 2))

        def _cod_moneda():
            return _label_to_cod.get(cb_moneda.get(), "USD")

        def _convertir(total_usd, destino):
            """USD → destino usando tasas en Bs. (tasa = Bs por unidad)."""
            t_usd = (_tasas.get("USD", {}) or {}).get("tasa", 0) or 0
            total_bs = total_usd * t_usd
            if destino == "VES":
                return total_bs
            t = (_tasas.get(destino, {}) or {}).get("tasa", 0) or 0
            return (total_bs / t) if t > 0 else 0.0

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
            for w in it_body.winfo_children():
                w.destroy()
            total = 0.0
            for idx, it in enumerate(_items_cot):
                bg2 = col["tarjetas"] if idx % 2 == 0 else col["fondo_oscuro"]
                sub = it["cantidad"] * it["precio_unitario"]
                total += sub
                fila2 = ctk.CTkFrame(it_body, corner_radius=0,
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
            base = _cod_moneda()
            tot_base = _convertir(total, base)
            total_var.set(f"Total:  {MON_SIMB.get(base, '')} "
                          f"{tot_base:,.2f} {base}")
            otras = [c for c in ["USD", "EUR", "VES", "USDT", "TASA_EXT"]
                     if c != base]
            partes = []
            for c in otras:
                val = _convertir(total, c)
                if val > 0 or c == "VES":
                    partes.append(f"≈ {MON_SIMB.get(c, '')} {val:,.2f} {c}")
            equiv_var.set("Equivalente:   " + "     ".join(partes)
                          if partes else "")

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
        lbl(body, "Observaciones")
        e_obs = ctk.CTkEntry(body, width=880, height=32)
        e_obs.pack(padx=20, anchor="w", pady=(0, 12))
        if row_data.get("observaciones"):
            e_obs.insert(0, row_data["observaciones"])

        # ── acción guardar (en el footer fijo) ──
        def _guardar():
            from core.session import get_usuario_actual
            num    = e_num.get().strip()
            fecha  = e_fecha.get().strip()
            estado = cb_estado.get()
            obs    = e_obs.get().strip()
            moneda = _cod_moneda()

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
            try:
                if cot_id:
                    ok = update_cotizacion(cot_id, num, fecha, cli_id,
                                           obs, estado, _items_cot, moneda)
                else:
                    ok = add_cotizacion(num, fecha, cli_id, obs,
                                        estado, usuario, _items_cot, moneda) > 0
            except TypeError:
                # compatibilidad con firmas sin 'moneda'
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

        ctk.CTkButton(footer, text="💾 Guardar Cotización",
                      fg_color=col["principal"], text_color="#0A192F",
                      hover_color=col.get("principal_hover", "#00C8D4"),
                      width=220, height=40,
                      command=_guardar).pack(side="right", padx=20, pady=12)
