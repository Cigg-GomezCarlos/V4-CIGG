"""
modulos/ventas/sub_venta.py
===========================
Submódulo Venta — lista + modal de creación/edición.

Igual que Cotizaciones, pero además:
  • Recibe PAGOS según los métodos de pago creados (💳 Métodos de Pago).
  • Condición Contado / Crédito.
  • En crédito: inicial + Nº de cuotas + monto de cuota + cada cuántos días +
    fecha de la primera cuota → genera un PLAN DE PAGO.
  • Al guardar: imprime la FACTURA (con plan de pago si es crédito) y, si es a
    crédito, también el CONTRATO DE COMPROMISO DE PAGO (editable en Documentos).
"""
import customtkinter as ctk
import datetime
from tkinter import messagebox

# Reutilizamos el Entry con autocompletado de cotizaciones
from .sub_cotizaciones import AutocompleteEntry


# Moneda base por tipo de ítem (idéntico a cotizaciones)
TIPO_MONEDA = {"Inventario": "USDT", "Máquina Fiscal": "USDT", "Sistema": "EUR"}
SIMB_ITEM   = {"USD": "$", "EUR": "€", "USDT": "₮"}
MON_LABELS  = {
    "USD":      "💵 USD — Dólar",
    "EUR":      "💶 EUR — Euro",
    "VES":      "🇻🇪 VES — Bolívar",
    "USDT":     "🟡 USDT",
    "TASA_EXT": "⚙️ Tasa Externa",
}
MON_SIMB = {"USD": "$", "EUR": "€", "VES": "Bs.", "USDT": "₮", "TASA_EXT": "★"}
_LABEL_TO_COD = {v: k for k, v in MON_LABELS.items()}


def _trunc(texto, width_px):
    """Recorta el texto con '…' para que no exceda el ancho de su columna
    (evita que un nombre largo desalinee toda la tabla)."""
    s = str(texto or "")
    max_chars = max(4, int(width_px / 7.5))
    if len(s) > max_chars:
        return s[:max_chars - 1].rstrip() + "…"
    return s


class _ToolTip:
    """Muestra el texto completo en un globo al pasar el cursor."""
    _tip = None

    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        widget.bind("<Enter>", self._show, add="+")
        widget.bind("<Leave>", self._hide, add="+")

    def _show(self, _=None):
        import tkinter as tk
        if _ToolTip._tip is not None:
            return
        try:
            x = self.widget.winfo_rootx() + 12
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
            tip = tk.Toplevel(self.widget)
            tip.wm_overrideredirect(True)
            tip.wm_geometry(f"+{x}+{y}")
            tk.Label(tip, text=self.text, justify="left",
                     bg="#0A192F", fg="#E2E8F0", relief="solid", borderwidth=1,
                     font=("Segoe UI", 9), padx=6, pady=3).pack()
            _ToolTip._tip = tip
        except Exception:
            pass

    def _hide(self, _=None):
        if _ToolTip._tip is not None:
            try:
                _ToolTip._tip.destroy()
            except Exception:
                pass
            _ToolTip._tip = None


def _cell(parent, full_text, width, height, text_color, font):
    """Celda de ancho fijo con texto truncado + tooltip del texto completo."""
    disp = _trunc(full_text, width)
    frame = ctk.CTkFrame(parent, width=width, height=height, corner_radius=0,
                         fg_color="transparent")
    frame.pack(side="left")
    frame.pack_propagate(False)
    lbl = ctk.CTkLabel(frame, text=disp, anchor="center",
                       text_color=text_color, font=font)
    lbl.pack(fill="both", expand=True)
    if disp != str(full_text or ""):
        _ToolTip(lbl, str(full_text))
    return frame


# ══════════════════════════════════════════════════════════════════════════════
# VENTA
# ══════════════════════════════════════════════════════════════════════════════

class SubmoduloVenta(ctk.CTkFrame):
    """Submódulo de Venta — lista + modal de creación/edición."""

    COLS   = ["Número", "Fecha", "Cliente", "Total", "Condición", ""]
    WIDTHS = [130, 100, 260, 120, 110, 118]

    COND_COLOR = {"Contado": "#2EC4B6", "Crédito": "#F4A261"}

    def __init__(self, parent, estilos, permisos=None):
        super().__init__(parent, corner_radius=0,
                         fg_color=estilos["colores"]["fondo_oscuro"])
        self.estilos  = estilos
        self.permisos = permisos or {}
        self.col      = estilos["colores"]
        self.fnt      = estilos["fuentes"]
        self._construir_ui()
        self.after(0, self.cargar_datos)

    # ─── UI ────────────────────────────────────────────────────────────────
    def _construir_ui(self):
        col, fnt = self.col, self.fnt

        bar = ctk.CTkFrame(self, height=52, corner_radius=0, fg_color="#020C1B")
        bar.pack(fill="x")
        bar.pack_propagate(False)

        ctk.CTkLabel(bar, text="🧾  Venta", font=fnt["titulo"],
                     text_color=col["principal"]).pack(side="left", padx=16, pady=8)

        ctk.CTkButton(bar, text="➕ Nueva Venta",
                      fg_color=col["principal"], text_color="#0A192F",
                      hover_color=col.get("principal_hover", "#00C8D4"),
                      width=160, height=34,
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
        from core.database import listar_ventas
        col, fnt = self.col, self.fnt

        for w in self.scroll.winfo_children():
            w.destroy()

        try:
            rows = listar_ventas(filtro)
        except Exception as e:
            ctk.CTkLabel(self.scroll, text=f"Error al cargar: {e}",
                         text_color="#E63946", font=fnt["normal"]).pack(pady=20)
            return

        for i, r in enumerate(rows):
            bg = col["tarjetas"] if i % 2 == 0 else col["fondo_oscuro"]
            fila = ctk.CTkFrame(self.scroll, corner_radius=0, fg_color=bg, height=34)
            fila.pack(fill="x")
            fila.pack_propagate(False)

            cond_c = self.COND_COLOR.get(r["condicion"], col["texto_claro"])
            simb   = MON_SIMB.get(r.get("moneda", "USD"), "$")
            vals = [
                (r["numero"],                    col["texto_claro"]),
                (r["fecha"],                     col["texto_claro"]),
                (r["cliente_nombre"],            col["texto_claro"]),
                (f'{simb} {r["total"]:,.2f}',    col["principal"]),
                (r["condicion"],                 cond_c),
            ]
            for (v, tc), w in zip(vals, self.WIDTHS[:-1]):
                _cell(fila, v, w, 34, tc, fnt["normal"])

            btn_f = ctk.CTkFrame(fila, width=118, corner_radius=0,
                                 fg_color="transparent")
            btn_f.pack(side="left")
            btn_f.pack_propagate(False)

            ctk.CTkButton(btn_f, text="🗑", width=34, height=28,
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
            ctk.CTkButton(btn_f, text="🖨", width=34, height=28,
                          fg_color="#1A3550",
                          hover_color=col["principal"],
                          text_color=col["principal"],
                          command=lambda rid=r["id"]: self._imprimir(rid)
                          ).pack(side="right", padx=2)

    # ─── Modal crear / editar ──────────────────────────────────────────────────
    def _abrir_modal(self, venta_id=None):
        # Envoltorio: si algo falla al construir el modal, muestra la traza
        # completa en pantalla en vez de "no hacer nada" (fallo silencioso).
        print(">>> [Ventas] click Nueva/Editar Venta (venta_id=%r)" % venta_id)
        try:
            self._abrir_modal_impl(venta_id)
        except Exception:
            import traceback
            tb = traceback.format_exc()
            print(tb)
            try:
                messagebox.showerror("Error al abrir Venta", tb)
            except Exception:
                pass

    def _abrir_modal_impl(self, venta_id=None):
        from core.database import (obtener_clientes, get_items_inventario,
                                   listar_modelos_sistemas, listar_modelos_maquinas,
                                   listar_metodos_pago,
                                   add_venta, update_venta,
                                   get_venta_completa, get_next_venta_numero)
        from modulos.ventas.sub_cotizaciones import AutocompleteEntry
        col, fnt = self.col, self.fnt

        row_data = get_venta_completa(venta_id) if venta_id else {}

        modal = ctk.CTkToplevel(self)
        modal.title("Editar Venta" if venta_id else "Nueva Venta")
        modal.geometry("960x760")
        modal.configure(fg_color=col["fondo_oscuro"])
        modal.transient(self.winfo_toplevel())
        modal.lift()
        # grab_set/focus diferidos: en Windows llamarlos antes de que la
        # ventana sea visible hace que el Toplevel abra detrás de la principal
        # (síntoma: "el botón no hace nada").
        modal.after(60, lambda: (modal.lift(), modal.focus_force(),
                                 modal.grab_set()))

        # ══ FOOTER FIJO (Guardar siempre visible) ══
        footer = ctk.CTkFrame(modal, height=64, corner_radius=0, fg_color="#020C1B")
        footer.pack(side="bottom", fill="x")
        footer.pack_propagate(False)
        err_lbl = ctk.CTkLabel(footer, text="", text_color="#E63946",
                               font=fnt["normal"])
        err_lbl.pack(side="left", padx=20)

        body = ctk.CTkScrollableFrame(modal, corner_radius=0,
                                      fg_color=col["fondo_oscuro"])
        body.pack(side="top", fill="both", expand=True)

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
        e_num.insert(0, row_data.get("numero") or get_next_venta_numero())

        e_fecha = ctk.CTkEntry(r1, width=130, height=32)
        e_fecha.grid(row=1, column=1, padx=(16, 0))
        e_fecha.insert(0, row_data.get("fecha") or
                       datetime.date.today().strftime("%d/%m/%Y"))

        estados = ["Emitida", "Pagada", "Anulada"]
        cb_estado = ctk.CTkComboBox(r1, values=estados, width=140, state="readonly")
        cb_estado.grid(row=1, column=2, padx=(16, 0))
        cb_estado.set(row_data.get("estado", "Emitida"))

        # ── tasas ──
        try:
            from modulos.monedas.db import leer_todas
            _tasas = leer_todas()
        except Exception:
            _tasas = {}

        # ── cliente ──
        lbl(body, "Cliente *  (escribe para filtrar)")
        clientes_list = obtener_clientes()
        cli_nombres = ["(Sin cliente)"] + [
            f'{c["rif"]} — {c["razon_social"]}' for c in clientes_list]
        cb_cli = AutocompleteEntry(body, values=cli_nombres, width=900,
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
        ctk.CTkLabel(body, text="  Agregar ítem", text_color=col["principal"],
                     font=fnt["subtitulo"]).pack(anchor="w", padx=20)

        add_row = ctk.CTkFrame(body, fg_color=col["tarjetas"], corner_radius=8)
        add_row.pack(fill="x", padx=20, pady=(4, 0))

        _items_inv = get_items_inventario()
        _mods_sis  = listar_modelos_sistemas()
        _mods_maq  = listar_modelos_maquinas()
        _current_ref = {"id": None, "tipo": "Inventario"}

        ctk.CTkLabel(add_row, text="Tipo", text_color=col["texto_claro"],
                     font=fnt["normal"]).grid(row=0, column=0, sticky="w",
                                              padx=(10, 4), pady=(6, 1))
        tipos = ["Inventario", "Sistema", "Máquina Fiscal"]
        cb_tipo = ctk.CTkComboBox(add_row, values=tipos, width=150, state="readonly",
                                  command=lambda v: _on_tipo_change(v))
        cb_tipo.grid(row=1, column=0, padx=(10, 4), pady=(0, 8))
        cb_tipo.set("Inventario")

        ctk.CTkLabel(add_row, text="Ítem / Servicio", text_color=col["texto_claro"],
                     font=fnt["normal"]).grid(row=0, column=1, sticky="w",
                                              padx=4, pady=(6, 1))
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

        precio_lbl_var = ctk.StringVar(value="Precio USDT")
        ctk.CTkLabel(add_row, textvariable=precio_lbl_var,
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
            precio_lbl_var.set(f"Precio {TIPO_MONEDA.get(tipo, 'USD')}")
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

        # ── tabla de ítems ──
        items_outer = ctk.CTkFrame(body, fg_color="transparent")
        items_outer.pack(fill="x", padx=20, pady=(8, 0))
        IT_COLS   = ["Tipo", "Descripción", "Cant.", "Precio", "Subtotal", ""]
        IT_WIDTHS = [100, 360, 60, 100, 100, 38]
        it_hdr = ctk.CTkFrame(items_outer, corner_radius=0,
                              fg_color="#0A192F", height=28)
        it_hdr.pack(fill="x")
        it_hdr.pack_propagate(False)
        for c, w in zip(IT_COLS, IT_WIDTHS):
            ctk.CTkLabel(it_hdr, text=c, width=w, anchor="center",
                         text_color=col["texto_claro"],
                         font=fnt["normal"]).pack(side="left")
        it_body = ctk.CTkFrame(items_outer, corner_radius=0, fg_color=col["tarjetas"])
        it_body.pack(fill="x")

        # ── moneda + total + equivalencias ──
        mon_row = ctk.CTkFrame(body, fg_color="transparent")
        mon_row.pack(fill="x", padx=20, pady=(6, 0))
        ctk.CTkLabel(mon_row, text="Moneda de la venta:",
                     text_color=col["texto_claro"],
                     font=fnt["normal"]).pack(side="left")
        cb_moneda = ctk.CTkComboBox(mon_row, values=list(MON_LABELS.values()),
                                    width=200, state="readonly",
                                    command=lambda v: _render_items())
        cb_moneda.pack(side="left", padx=(8, 0))
        cb_moneda.set(MON_LABELS.get(row_data.get("moneda", "USD"),
                                     MON_LABELS["USD"]))

        total_var = ctk.StringVar(value="Total:  $ 0.00")
        ctk.CTkLabel(body, textvariable=total_var, text_color=col["principal"],
                     font=fnt["subtitulo"]).pack(anchor="e", padx=24, pady=(4, 0))
        equiv_var = ctk.StringVar(value="")
        ctk.CTkLabel(body, textvariable=equiv_var, text_color=col["texto_claro"],
                     font=fnt["normal"]).pack(anchor="e", padx=24, pady=(0, 2))

        # estado mutable compartido del total (en moneda de la venta)
        _tot = {"venta": 0.0}

        def _cod_moneda():
            return _LABEL_TO_COD.get(cb_moneda.get(), "USD")

        def _convertir(total_usd, destino):
            t_usd = (_tasas.get("USD", {}) or {}).get("tasa", 0) or 0
            total_bs = total_usd * t_usd
            if destino == "VES":
                return total_bs
            t = (_tasas.get(destino, {}) or {}).get("tasa", 0) or 0
            return (total_bs / t) if t > 0 else 0.0

        def _a_usd(precio, moneda_item):
            if moneda_item == "USD" or precio <= 0:
                return precio
            t_usd = (_tasas.get("USD", {}) or {}).get("tasa", 0) or 0
            t     = (_tasas.get(moneda_item, {}) or {}).get("tasa", 0) or 0
            if t_usd <= 0 or t <= 0:
                return precio
            return (precio * t) / t_usd

        _items_v = []
        if row_data.get("items"):
            for it in row_data["items"]:
                _items_v.append({
                    "tipo":            it["tipo"],
                    "item_ref_id":     it["item_ref_id"],
                    "descripcion":     it["descripcion"],
                    "cantidad":        it["cantidad"],
                    "precio_unitario": it["precio_unitario"],
                    "moneda_item":     it.get("moneda_item",
                                              TIPO_MONEDA.get(it["tipo"], "USD")),
                })

        def _render_items():
            for w in it_body.winfo_children():
                w.destroy()
            total = 0.0
            for idx, it in enumerate(_items_v):
                bg2 = col["tarjetas"] if idx % 2 == 0 else col["fondo_oscuro"]
                mon_it  = it.get("moneda_item", "USD")
                simb_it = SIMB_ITEM.get(mon_it, "$")
                sub = it["cantidad"] * it["precio_unitario"]
                total += it["cantidad"] * _a_usd(it["precio_unitario"], mon_it)
                fila2 = ctk.CTkFrame(it_body, corner_radius=0, fg_color=bg2, height=28)
                fila2.pack(fill="x")
                fila2.pack_propagate(False)
                vals2 = [it["tipo"], it["descripcion"], f'{it["cantidad"]:.2f}',
                         f'{simb_it} {it["precio_unitario"]:.2f}',
                         f'{simb_it} {sub:.2f}']
                for v, w in zip(vals2, IT_WIDTHS[:-1]):
                    _cell(fila2, v, w, 28, col["texto_claro"], fnt["normal"])
                ctk.CTkButton(fila2, text="🗑", width=34, height=22,
                              fg_color="transparent",
                              hover_color=col.get("error", "#E63946"),
                              text_color=col.get("error", "#E63946"),
                              command=lambda i=idx: _quitar_item(i)
                              ).pack(side="left")
            base = _cod_moneda()
            tot_base = _convertir(total, base)
            _tot["venta"] = tot_base
            total_var.set(f"Total:  {MON_SIMB.get(base, '')} {tot_base:,.2f} {base}")
            otras = [c for c in ["USD", "EUR", "VES", "USDT", "TASA_EXT"] if c != base]
            partes = []
            for c in otras:
                val = _convertir(total, c)
                if val > 0 or c == "VES":
                    partes.append(f"≈ {MON_SIMB.get(c, '')} {val:,.2f} {c}")
            equiv_var.set("Equivalente:   " + "     ".join(partes) if partes else "")
            _refrescar_credito()

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
            _items_v.append({
                "tipo":            tipo,
                "item_ref_id":     _current_ref["id"],
                "descripcion":     desc,
                "cantidad":        cant,
                "precio_unitario": prec,
                "moneda_item":     TIPO_MONEDA.get(tipo, "USD"),
            })
            _render_items()

        def _quitar_item(idx):
            if 0 <= idx < len(_items_v):
                _items_v.pop(idx)
                _render_items()

        # ══════════════════════════════════════════════════════════════════════
        # CONDICIÓN DE PAGO  (Contado / Crédito)
        # ══════════════════════════════════════════════════════════════════════
        ctk.CTkFrame(body, height=2, fg_color=col["principal"]).pack(
            fill="x", padx=20, pady=(12, 4))
        ctk.CTkLabel(body, text="  Condición de pago", text_color=col["principal"],
                     font=fnt["subtitulo"]).pack(anchor="w", padx=20)

        cond_row = ctk.CTkFrame(body, fg_color="transparent")
        cond_row.pack(fill="x", padx=20, pady=(4, 0))
        cond_var = ctk.StringVar(value=row_data.get("condicion", "Contado"))
        ctk.CTkSegmentedButton(cond_row, values=["Contado", "Crédito"],
                               variable=cond_var,
                               command=lambda v: _on_cond_change()
                               ).pack(side="left")

        # ── PAGOS (métodos de pago) ──
        pagos_box = ctk.CTkFrame(body, fg_color=col["tarjetas"], corner_radius=8)
        pagos_box.pack(fill="x", padx=20, pady=(8, 0))

        metodos = [m for m in listar_metodos_pago() if m.get("activo", 1)]
        met_labels = [f'{m["nombre"]} ({m["moneda"]})' for m in metodos]
        _met_by_label = {f'{m["nombre"]} ({m["moneda"]})': m for m in metodos}

        pay_add = ctk.CTkFrame(pagos_box, fg_color="transparent")
        pay_add.pack(fill="x", padx=8, pady=(8, 2))
        ctk.CTkLabel(pay_add, text="Método", text_color=col["texto_claro"],
                     font=fnt["normal"]).grid(row=0, column=0, sticky="w", padx=4)
        cb_metodo = ctk.CTkComboBox(
            pay_add, values=(met_labels or ["(Sin métodos)"]),
            width=260, state="readonly")
        cb_metodo.grid(row=1, column=0, padx=4)
        cb_metodo.set(met_labels[0] if met_labels else "(Sin métodos)")
        ctk.CTkLabel(pay_add, text="Monto", text_color=col["texto_claro"],
                     font=fnt["normal"]).grid(row=0, column=1, sticky="w", padx=4)
        e_pago_monto = ctk.CTkEntry(pay_add, width=120, height=32)
        e_pago_monto.grid(row=1, column=1, padx=4)
        e_pago_monto.insert(0, "0.00")
        ctk.CTkButton(pay_add, text="➕ Agregar pago",
                      fg_color=col["principal"], text_color="#0A192F",
                      hover_color=col.get("principal_hover", "#00C8D4"),
                      width=140, height=32,
                      command=lambda: _agregar_pago()
                      ).grid(row=1, column=2, padx=(8, 4))

        pagos_list = ctk.CTkFrame(pagos_box, fg_color="transparent")
        pagos_list.pack(fill="x", padx=8, pady=(2, 8))

        _pagos = []
        if row_data.get("pagos"):
            for p in row_data["pagos"]:
                _pagos.append({
                    "metodo_pago_id": p.get("metodo_pago_id"),
                    "metodo_nombre":  p.get("metodo_nombre", ""),
                    "moneda":         p.get("moneda", "USD"),
                    "monto":          p.get("monto", 0),
                })

        def _render_pagos():
            for w in pagos_list.winfo_children():
                w.destroy()
            for idx, p in enumerate(_pagos):
                f = ctk.CTkFrame(pagos_list, fg_color="transparent")
                f.pack(fill="x", pady=1)
                ctk.CTkLabel(
                    f, text=f'💳 {p["metodo_nombre"]}  ·  '
                            f'{MON_SIMB.get(p["moneda"], "")} {p["monto"]:,.2f} '
                            f'{p["moneda"]}',
                    text_color=col["texto_claro"],
                    font=fnt["normal"]).pack(side="left")
                ctk.CTkButton(f, text="🗑", width=30, height=22,
                              fg_color="transparent",
                              hover_color=col.get("error", "#E63946"),
                              text_color=col.get("error", "#E63946"),
                              command=lambda i=idx: _quitar_pago(i)
                              ).pack(side="right")

        def _agregar_pago():
            sel = cb_metodo.get()
            m = _met_by_label.get(sel)
            if not m:
                return
            try:
                monto = float(e_pago_monto.get() or 0)
            except ValueError:
                return
            if monto <= 0:
                return
            try:
                from modulos.monedas.db import leer_todas
                _tasas_tmp = leer_todas()
            except Exception:
                _tasas_tmp = {}
            tasa_bs_tmp = (_tasas_tmp.get("VES", {}) or {}).get("tasa", 0) or 0
            monto_bs_tmp = round(monto * tasa_bs_tmp, 2) if tasa_bs_tmp > 0 and m["moneda"] == "USD" else 0
            _pagos.append({
                "metodo_pago_id": m["id"],
                "metodo_nombre":  m["nombre"],
                "moneda":         m["moneda"],
                "monto":          monto,
                "monto_bs":       monto_bs_tmp,
                "tasa_bs":        tasa_bs_tmp,
            })
            _render_pagos()

        def _quitar_pago(idx):
            if 0 <= idx < len(_pagos):
                _pagos.pop(idx)
                _render_pagos()

        # ══════════════════════════════════════════════════════════════════════
        # CRÉDITO — inicial + cuotas + frecuencia + primera cuota → plan de pago
        # ══════════════════════════════════════════════════════════════════════
        credito_box = ctk.CTkFrame(body, fg_color=col["tarjetas"], corner_radius=8)

        cred_top = ctk.CTkFrame(credito_box, fg_color="transparent")
        cred_top.pack(fill="x", padx=8, pady=(8, 2))
        labels_c = ["Inicial", "N° de cuotas", "Cada (días)", "1ª cuota (dd/mm/aaaa)"]
        for i, t in enumerate(labels_c):
            ctk.CTkLabel(cred_top, text=t, text_color=col["texto_claro"],
                         font=fnt["normal"]).grid(row=0, column=i, sticky="w", padx=4)
        e_inicial = ctk.CTkEntry(cred_top, width=110, height=32)
        e_inicial.grid(row=1, column=0, padx=4)
        e_inicial.insert(0, f'{row_data.get("inicial", 0):.2f}')
        e_ncuotas = ctk.CTkEntry(cred_top, width=110, height=32)
        e_ncuotas.grid(row=1, column=1, padx=4)
        e_ncuotas.insert(0, str(row_data.get("num_cuotas", 0) or 0))
        e_dias = ctk.CTkEntry(cred_top, width=110, height=32)
        e_dias.grid(row=1, column=2, padx=4)
        e_dias.insert(0, str(row_data.get("dias_frecuencia", 30) or 30))
        e_fecha1 = ctk.CTkEntry(cred_top, width=160, height=32)
        e_fecha1.grid(row=1, column=3, padx=4)
        e_fecha1.insert(0, row_data.get("fecha_primera_cuota", "") or
                        (datetime.date.today() +
                         datetime.timedelta(days=30)).strftime("%d/%m/%Y"))
        ctk.CTkLabel(cred_top, text="Moneda inicial/cuotas",
                     text_color=col["texto_claro"],
                     font=fnt["normal"]).grid(row=0, column=4, sticky="w", padx=4)
        cb_cred_moneda = ctk.CTkComboBox(
            cred_top, values=list(MON_LABELS.values()), width=170, height=32,
            command=lambda _=None: _refrescar_credito())
        cb_cred_moneda.grid(row=1, column=4, padx=4)
        cb_cred_moneda.set(MON_LABELS.get(
            row_data.get("moneda_credito") or _cod_moneda(),
            MON_LABELS.get("USD")))

        def _cred_moneda():
            return _LABEL_TO_COD.get(cb_cred_moneda.get(), _cod_moneda())

        def _total_en_credito():
            """Total de la venta convertido a la moneda del crédito."""
            total_usd = _a_usd(_tot["venta"], _cod_moneda())
            return round(_convertir(total_usd, _cred_moneda()), 2)

        ctk.CTkButton(cred_top, text="🔄 Recalcular plan",
                      fg_color=col["principal"], text_color="#0A192F",
                      hover_color=col.get("principal_hover", "#00C8D4"),
                      width=150, height=32,
                      command=lambda: _refrescar_credito()
                      ).grid(row=1, column=5, padx=(8, 4))

        plan_list = ctk.CTkFrame(credito_box, fg_color="transparent")
        plan_list.pack(fill="x", padx=8, pady=(2, 8))

        _cuotas = []

        def _calc_cuotas():
            """Genera _cuotas a partir de los campos de crédito. Devuelve texto de error o ''."""
            _cuotas.clear()
            try:
                inicial = float(e_inicial.get() or 0)
                ncuot   = int(float(e_ncuotas.get() or 0))
                dias    = int(float(e_dias.get() or 0))
            except ValueError:
                return "Datos de crédito inválidos."
            base = _cod_moneda()
            total = _tot["venta"]
            saldo = round(total - inicial, 2)
            if ncuot <= 0:
                return "Indique el número de cuotas."
            if saldo < 0:
                return "La inicial no puede superar el total."
            try:
                f1 = datetime.datetime.strptime(e_fecha1.get().strip(),
                                                "%d/%m/%Y").date()
            except ValueError:
                return "Fecha de 1ª cuota inválida (dd/mm/aaaa)."
            monto_cuota = round(saldo / ncuot, 2)
            acumulado = 0.0
            for i in range(ncuot):
                venc = f1 + datetime.timedelta(days=dias * i)
                # última cuota ajusta el residuo por redondeo
                if i == ncuot - 1:
                    monto = round(saldo - acumulado, 2)
                else:
                    monto = monto_cuota
                    acumulado += monto_cuota
                _cuotas.append({
                    "numero_cuota": i + 1,
                    "fecha_venc":   venc.strftime("%d/%m/%Y"),
                    "monto":        monto,
                })
            return ""

        def _render_plan(err=""):
            for w in plan_list.winfo_children():
                w.destroy()
            base = _cred_moneda()
            simb = MON_SIMB.get(base, "")
            if err:
                ctk.CTkLabel(plan_list, text=f"⚠ {err}", text_color="#F4A261",
                             font=fnt["normal"]).pack(anchor="w")
                return
            try:
                inicial = float(e_inicial.get() or 0)
            except ValueError:
                inicial = 0
            ctk.CTkLabel(
                plan_list,
                text=f'Inicial: {simb} {inicial:,.2f} {base}   ·   '
                     f'Saldo en {len(_cuotas)} cuota(s)',
                text_color=col["principal"], font=fnt["normal"]).pack(anchor="w")
            for c in _cuotas:
                ctk.CTkLabel(
                    plan_list,
                    text=f'   Cuota {c["numero_cuota"]:>2}  ·  vence '
                         f'{c["fecha_venc"]}  ·  {simb} {c["monto"]:,.2f} {base}',
                    text_color=col["texto_claro"],
                    font=fnt["normal"]).pack(anchor="w")

        def _refrescar_credito():
            if cond_var.get() != "Crédito":
                _cuotas.clear()
                return
            err = _calc_cuotas()
            _render_plan(err)

        def _on_cond_change():
            if cond_var.get() == "Crédito":
                credito_box.pack(fill="x", padx=20, pady=(8, 0))
                _refrescar_credito()
            else:
                credito_box.pack_forget()
                _cuotas.clear()

        # ── observaciones ──
        lbl(body, "Observaciones")
        e_obs = ctk.CTkEntry(body, width=900, height=32)
        e_obs.pack(padx=20, anchor="w", pady=(0, 12))
        if row_data.get("observaciones"):
            e_obs.insert(0, row_data["observaciones"])

        # render inicial
        _render_items()
        _render_pagos()
        _on_cond_change()

        # ── guardar (footer fijo) ──
        def _guardar():
            from core.session import get_usuario_actual
            num    = e_num.get().strip()
            fecha  = e_fecha.get().strip()
            estado = cb_estado.get()
            obs    = e_obs.get().strip()
            moneda = _cod_moneda()
            cond   = cond_var.get()

            if not num or not fecha:
                err_lbl.configure(text="Número y Fecha son obligatorios.")
                return
            if not _items_v:
                err_lbl.configure(text="Agregue al menos un ítem.")
                return

            inicial = num_cuotas = monto_cuota = dias_frec = 0
            fecha1 = ""
            cuotas_data = []
            if cond == "Crédito":
                err = _calc_cuotas()
                if err:
                    err_lbl.configure(text=err)
                    return
                try:
                    inicial   = float(e_inicial.get() or 0)
                    dias_frec = int(float(e_dias.get() or 0))
                except ValueError:
                    err_lbl.configure(text="Datos de crédito inválidos.")
                    return
                num_cuotas  = len(_cuotas)
                monto_cuota = _cuotas[0]["monto"] if _cuotas else 0
                fecha1      = e_fecha1.get().strip()
                cuotas_data = list(_cuotas)
                moneda_cred = _cred_moneda()

            cli_id = None
            sel = cb_cli.get()
            if sel != "(Sin cliente)":
                rif_sel = sel.split(" — ")[0]
                match = next((c for c in clientes_list if c["rif"] == rif_sel), None)
                if match:
                    cli_id = match["id"]

            data = {
                "numero": num, "fecha": fecha, "cliente_id": cli_id,
                "observaciones": obs, "estado": estado,
                "usuario": get_usuario_actual() or "",
                "total": round(_tot["venta"], 2), "moneda": moneda,
                "condicion": cond, "inicial": inicial,
                "num_cuotas": num_cuotas, "monto_cuota": monto_cuota,
                "dias_frecuencia": dias_frec, "fecha_primera_cuota": fecha1,
            }

            nuevo_id = venta_id
            try:
                if venta_id:
                    ok = update_venta(venta_id, data, _items_v, _pagos, cuotas_data)
                else:
                    nuevo_id = add_venta(data, _items_v, _pagos, cuotas_data)
                    ok = nuevo_id and nuevo_id > 0
            except Exception as e:
                err_lbl.configure(text=f"Error al guardar: {e}")
                return
            if not ok:
                err_lbl.configure(text="Error al guardar. ¿Número duplicado?")
                return

            modal.destroy()
            self.cargar_datos(self.busq_var.get())
            if nuevo_id and nuevo_id > 0:
                self._imprimir(nuevo_id)          # factura (+ plan si es crédito)
                if cond == "Crédito":
                    self._imprimir_contrato(nuevo_id)   # contrato de compromiso

        ctk.CTkButton(footer, text="💾 Guardar Venta",
                      fg_color=col["principal"], text_color="#0A192F",
                      hover_color=col.get("principal_hover", "#00C8D4"),
                      width=200, height=40,
                      command=_guardar).pack(side="right", padx=20, pady=12)

    # ─── Acciones ─────────────────────────────────────────────────────────────
    def _eliminar(self, rid):
        from core.database import eliminar_venta
        if messagebox.askyesno("Eliminar", "¿Eliminar esta venta?"):
            eliminar_venta(rid)
            self.cargar_datos(self.busq_var.get())

    def _imprimir(self, rid):
        try:
            from .impresion import imprimir_venta
            if not imprimir_venta(rid):
                messagebox.showerror("Imprimir", "No se pudo generar el documento.")
        except Exception as e:
            messagebox.showerror("Imprimir",
                                 f"No se pudo generar el documento:\n{e}")

    def _imprimir_contrato(self, rid):
        try:
            from .impresion import imprimir_contrato_pago
            imprimir_contrato_pago(rid)
        except Exception as e:
            messagebox.showerror("Contrato",
                                 f"No se pudo generar el contrato:\n{e}")
