"""
modulos/compras/sub_compra.py
=============================
Submódulo Compra — lista + modal de creación/edición.

Flujo simplificado:
  • El usuario agrega ítems (se calcula el total)
  • La moneda de la compra se hereda de la moneda de los ítems
  • El usuario agrega pagos
  • Si los pagos < total → la diferencia pasa automáticamente a CxP
    en la MISMA MONEDA de los productos (USD, USDT, EUR, etc.)
  • Si los pagos >= total → es contado, no hay CxP
"""
import customtkinter as ctk
import datetime
from tkinter import messagebox

from modulos.ventas.sub_cotizaciones import AutocompleteEntry


TIPO_MONEDA = {"Inventario": "USDT", "Máquina Fiscal": "USDT", "Sistema": "EUR"}
SIMB_ITEM   = {"USD": "$", "EUR": "€", "USDT": "₮", "VES": "Bs."}
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
    s = str(texto or "")
    max_chars = max(4, int(width_px / 7.5))
    if len(s) > max_chars:
        return s[:max_chars - 1].rstrip() + "…"
    return s


class _ToolTip:
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


class SubmoduloCompra(ctk.CTkFrame):
    COLS   = ["Número", "Fecha", "Proveedor", "Total", "Condición", ""]
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

    def _construir_ui(self):
        col, fnt = self.col, self.fnt

        bar = ctk.CTkFrame(self, height=52, corner_radius=0, fg_color="#020C1B")
        bar.pack(fill="x")
        bar.pack_propagate(False)

        ctk.CTkLabel(bar, text="🛒  Compra", font=fnt["titulo"],
                     text_color=col["principal"]).pack(side="left", padx=16, pady=8)

        ctk.CTkButton(bar, text="➕ Nueva Compra",
                      fg_color=col["principal"], text_color="#0A192F",
                      hover_color=col.get("principal_hover", "#00C8D4"),
                      width=160, height=34,
                      command=self._abrir_modal).pack(side="right", padx=12, pady=8)

        self.busq_var = ctk.StringVar()
        ctk.CTkEntry(bar, textvariable=self.busq_var, width=240, height=32,
                     placeholder_text="🔍 Buscar por número o proveedor…"
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

    def cargar_datos(self, filtro: str = ""):
        from core.database import listar_compras
        col, fnt = self.col, self.fnt

        for w in self.scroll.winfo_children():
            w.destroy()

        try:
            rows = listar_compras(filtro)
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
                (r["proveedor_nombre"],          col["texto_claro"]),
                (f"{simb} {r['total']:,.2f}",    col["principal"]),
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

    def _eliminar(self, rid):
        from core.database import eliminar_compra
        if messagebox.askyesno("Eliminar", "¿Eliminar esta compra?"):
            eliminar_compra(rid)
            self.cargar_datos(self.busq_var.get())

    def _abrir_modal(self, compra_id=None):
        try:
            self._abrir_modal_impl(compra_id)
        except Exception:
            import traceback
            tb = traceback.format_exc()
            print(tb)
            try:
                messagebox.showerror("Error al abrir Compra", tb)
            except Exception:
                pass

    def _abrir_modal_impl(self, compra_id=None):
        from core.database import (obtener_proveedores, get_items_inventario,
                                   listar_modelos_sistemas, listar_modelos_maquinas,
                                   listar_metodos_pago,
                                   add_compra, update_compra,
                                   get_compra_completa, get_next_compra_numero)
        col, fnt = self.col, self.fnt

        row_data = get_compra_completa(compra_id) if compra_id else {}

        modal = ctk.CTkToplevel(self)
        modal.title("Editar Compra" if compra_id else "Nueva Compra")
        modal.geometry("960x720")
        modal.configure(fg_color=col["fondo_oscuro"])
        modal.transient(self.winfo_toplevel())
        modal.lift()
        modal.after(60, lambda: (modal.lift(), modal.focus_force(),
                                 modal.grab_set()))

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

        # fila 1: número / fecha / estado
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
        e_num.insert(0, row_data.get("numero") or get_next_compra_numero())

        e_fecha = ctk.CTkEntry(r1, width=130, height=32)
        e_fecha.grid(row=1, column=1, padx=(16, 0))
        e_fecha.insert(0, row_data.get("fecha") or
                       datetime.date.today().strftime("%d/%m/%Y"))

        estados = ["Recibida", "Pagada", "Anulada"]
        cb_estado = ctk.CTkComboBox(r1, values=estados, width=140, state="readonly")
        cb_estado.grid(row=1, column=2, padx=(16, 0))
        cb_estado.set(row_data.get("estado", "Recibida"))

        try:
            from modulos.monedas.db import leer_todas
            _tasas = leer_todas()
        except Exception:
            _tasas = {}

        # proveedor
        lbl(body, "Proveedor *  (escribe para filtrar)")
        proveedores_list = obtener_proveedores()
        prov_nombres = ["(Sin proveedor)"] + [
            f'{p["rif"]} — {p["razon_social"]}' for p in proveedores_list]
        cb_prov = AutocompleteEntry(body, values=prov_nombres, width=900,
                                    placeholder="RIF o razón social…",
                                    colores=col, fuentes=fnt)
        cb_prov.pack(padx=20, anchor="w")
        if row_data.get("proveedor_id"):
            match = next((f'{p["rif"]} — {p["razon_social"]}'
                          for p in proveedores_list
                          if p["id"] == row_data["proveedor_id"]), None)
            cb_prov.set(match or prov_nombres[0])
        else:
            cb_prov.set(prov_nombres[0])

        # sección agregar ítem
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
                    e_precio_add.insert(0, f'{match.get("precio_costo", 0):.2f}')
            elif tipo == "Sistema":
                match = next((m for m in _mods_sis if m[1] == val), None)
                _current_ref["id"] = match[0] if match else None
            else:
                match = next((m for m in _mods_maq if m[1] == val), None)
                _current_ref["id"] = match[0] if match else None

        _on_tipo_change("Inventario")

        # tabla de ítems
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

        # moneda de la compra (heredada de los ítems, solo informativo)
        mon_row = ctk.CTkFrame(body, fg_color="transparent")
        mon_row.pack(fill="x", padx=20, pady=(6, 0))
        ctk.CTkLabel(mon_row, text="Moneda de la compra:",
                     text_color=col["texto_claro"],
                     font=fnt["normal"]).pack(side="left")
        moneda_var = ctk.StringVar(value=MON_LABELS.get(
            row_data.get("moneda", "USD"), MON_LABELS["USD"]))
        cb_moneda = ctk.CTkComboBox(mon_row, values=list(MON_LABELS.values()),
                                    width=200, state="readonly",
                                    command=lambda v: _render_items())
        cb_moneda.pack(side="left", padx=(8, 0))
        cb_moneda.set(moneda_var.get())

        total_var = ctk.StringVar(value="Total:  $ 0.00")
        ctk.CTkLabel(body, textvariable=total_var, text_color=col["principal"],
                     font=fnt["subtitulo"]).pack(anchor="e", padx=24, pady=(4, 0))
        equiv_var = ctk.StringVar(value="")
        ctk.CTkLabel(body, textvariable=equiv_var, text_color=col["texto_claro"],
                     font=fnt["normal"]).pack(anchor="e", padx=24, pady=(0, 2))

        # estado interno
        _tot = {"compra": 0.0}           # total en moneda de los ítems
        _moneda_nativa = "USD"           # moneda de los ítems (heredada)

        def _cod_moneda():
            return _LABEL_TO_COD.get(cb_moneda.get(), "USD")

        def _detectar_moneda_items():
            """Devuelve la moneda común de los ítems, o USD si están vacíos/mixtos."""
            if not _items_c:
                return _cod_moneda()
            monedas = {it.get("moneda_item", "USD") for it in _items_c}
            if len(monedas) == 1:
                return monedas.pop()
            return _cod_moneda()  # mixto: mantener la del combo

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

        _items_c = []
        if row_data.get("items"):
            for it in row_data["items"]:
                _items_c.append({
                    "tipo":            it["tipo"],
                    "item_ref_id":     it["item_ref_id"],
                    "descripcion":     it["descripcion"],
                    "cantidad":        it["cantidad"],
                    "precio_unitario": it["precio_unitario"],
                    "moneda_item":     it.get("moneda_item",
                                              TIPO_MONEDA.get(it["tipo"], "USD")),
                })

        def _render_items():
            nonlocal _moneda_nativa
            for w in it_body.winfo_children():
                w.destroy()
            total_usd = 0.0
            total_nativo = 0.0
            for idx, it in enumerate(_items_c):
                bg2 = col["tarjetas"] if idx % 2 == 0 else col["fondo_oscuro"]
                mon_it  = it.get("moneda_item", "USD")
                simb_it = SIMB_ITEM.get(mon_it, "$")
                sub = it["cantidad"] * it["precio_unitario"]
                total_usd += it["cantidad"] * _a_usd(it["precio_unitario"], mon_it)
                total_nativo += sub
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

            # Heredar moneda de los ítems
            _moneda_nativa = _detectar_moneda_items()
            simb_nat = MON_SIMB.get(_moneda_nativa, "$")
            _tot["compra"] = total_nativo  # guardamos en moneda nativa

            # Actualizar combo de moneda si todos los ítems son iguales
            if _items_c and len({it.get("moneda_item", "USD") for it in _items_c}) == 1:
                cb_moneda.set(MON_LABELS.get(_moneda_nativa, MON_LABELS["USD"]))

            total_var.set(
                f"Total:  {simb_nat} {total_nativo:,.2f} {_moneda_nativa}"
            )
            # Equivalentes en otras monedas (convertido desde USD)
            otras = [c for c in ["USD", "EUR", "VES", "USDT", "TASA_EXT"] if c != _moneda_nativa]
            partes = []
            for c in otras:
                val = _convertir(total_usd, c)
                if val > 0 or c == "VES":
                    partes.append(f"≈ {MON_SIMB.get(c, '')} {val:,.2f} {c}")
            equiv_var.set("Equivalente:   " + "     ".join(partes) if partes else "")
            _refrescar_saldo()

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
            _items_c.append({
                "tipo":            tipo,
                "item_ref_id":     _current_ref["id"],
                "descripcion":     desc,
                "cantidad":        cant,
                "precio_unitario": prec,
                "moneda_item":     TIPO_MONEDA.get(tipo, "USD"),
            })
            _render_items()

        def _quitar_item(idx):
            if 0 <= idx < len(_items_c):
                _items_c.pop(idx)
                _render_items()

        # ═══════════════════════════════════════════════════════════════════════
        # PAGOS  (el saldo automático va a CxP en moneda de los ítems)
        # ═══════════════════════════════════════════════════════════════════════
        ctk.CTkFrame(body, height=2, fg_color=col["principal"]).pack(
            fill="x", padx=20, pady=(12, 4))
        ctk.CTkLabel(body, text="  Pagos realizados", text_color=col["principal"],
                     font=fnt["subtitulo"]).pack(anchor="w", padx=20)

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

        # etiqueta de saldo automático en moneda de los ítems
        saldo_var = ctk.StringVar(value="")
        saldo_lbl = ctk.CTkLabel(body, textvariable=saldo_var,
                                 text_color=col["principal"], font=fnt["subtitulo"])
        saldo_lbl.pack(anchor="e", padx=24, pady=(4, 0))

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
            _refrescar_saldo()

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
            _pagos.append({
                "metodo_pago_id": m["id"],
                "metodo_nombre":  m["nombre"],
                "moneda":         m["moneda"],
                "monto":          monto,
            })
            _render_pagos()

        def _quitar_pago(idx):
            if 0 <= idx < len(_pagos):
                _pagos.pop(idx)
                _render_pagos()

        def _refrescar_saldo():
            """Calcula total pagado vs total compra y muestra saldo a CxP
            en la MONEDA NATIVA de los ítems."""
            simb = MON_SIMB.get(_moneda_nativa, "$")
            total = _tot["compra"]  # ya está en moneda nativa
            # Convertir cada pago a la moneda nativa
            pagado = 0.0
            for p in _pagos:
                pagado += _conv(p["monto"], p["moneda"], _moneda_nativa, _tasas)
            pagado = round(pagado, 2)
            saldo = round(total - pagado, 2)
            if saldo > 0.01:
                saldo_var.set(
                    f"Pagado: {simb} {pagado:,.2f}  │  "
                    f"Saldo a CxP: {simb} {saldo:,.2f} {_moneda_nativa}"
                )
            else:
                saldo_var.set(
                    f"Pagado: {simb} {pagado:,.2f}  │  "
                    f"Compra pagada al contado ✅"
                )

        def _conv(monto, origen, destino, tasas):
            if origen == destino or not monto:
                return monto
            t_usd = (tasas.get("USD", {}) or {}).get("tasa", 0) or 0
            # origen → USD
            if origen == "USD":
                usd = monto
            elif origen == "VES":
                usd = (monto / t_usd) if t_usd > 0 else monto
            else:
                t_o = (tasas.get(origen, {}) or {}).get("tasa", 0) or 0
                bs = monto * t_o if t_o > 0 else 0
                usd = (bs / t_usd) if t_usd > 0 else monto
            # USD → destino
            if destino == "USD":
                return usd
            if destino == "VES":
                return usd * t_usd
            t_d = (tasas.get(destino, {}) or {}).get("tasa", 0) or 0
            return (usd * t_usd) / t_d if t_d > 0 else usd

        # observaciones
        lbl(body, "Observaciones")
        e_obs = ctk.CTkEntry(body, width=900, height=32)
        e_obs.pack(padx=20, anchor="w", pady=(0, 12))
        if row_data.get("observaciones"):
            e_obs.insert(0, row_data["observaciones"])

        _render_items()
        _render_pagos()

        # guardar
        def _guardar():
            from core.session import get_usuario_actual
            num    = e_num.get().strip()
            fecha  = e_fecha.get().strip()
            estado = cb_estado.get()
            obs    = e_obs.get().strip()

            if not num or not fecha:
                err_lbl.configure(text="Número y Fecha son obligatorios.")
                return
            if not _items_c:
                err_lbl.configure(text="Agregue al menos un ítem.")
                return

            # La moneda de la compra = moneda de los ítems
            moneda = _moneda_nativa
            total = _tot["compra"]  # total en moneda nativa

            # Calcular pagado en moneda nativa
            pagado = 0.0
            for p in _pagos:
                pagado += _conv(p["monto"], p["moneda"], moneda, _tasas)
            pagado = round(pagado, 2)
            saldo = round(total - pagado, 2)

            if saldo > 0.01:
                cond = "Crédito"
                inicial = pagado
                num_cuotas = 1
                monto_cuota = saldo
                moneda_cred = moneda  # CxP en la moneda del producto
                if estado == "Recibida":
                    estado = "Recibida"
            else:
                cond = "Contado"
                inicial = total
                num_cuotas = 0
                monto_cuota = 0
                moneda_cred = moneda
                estado = "Pagada"

            prov_id = None
            sel = cb_prov.get()
            if sel != "(Sin proveedor)":
                rif_sel = sel.split(" — ")[0]
                match = next((p for p in proveedores_list if p["rif"] == rif_sel), None)
                if match:
                    prov_id = match["id"]

            data = {
                "numero": num, "fecha": fecha, "proveedor_id": prov_id,
                "observaciones": obs, "estado": estado,
                "usuario": get_usuario_actual() or "",
                "total": round(total, 2), "moneda": moneda,
                "condicion": cond, "inicial": inicial,
                "num_cuotas": num_cuotas, "monto_cuota": monto_cuota,
                "moneda_credito": moneda_cred,  # ← misma moneda del producto
            }

            nuevo_id = compra_id
            try:
                if compra_id:
                    ok = update_compra(compra_id, data, _items_c, _pagos)
                else:
                    nuevo_id = add_compra(data, _items_c, _pagos)
                    ok = nuevo_id and nuevo_id > 0
            except Exception as e:
                err_lbl.configure(text=f"Error al guardar: {e}")
                return
            if not ok:
                err_lbl.configure(text="Error al guardar. ¿Número duplicado?")
                return

            modal.destroy()
            self.cargar_datos(self.busq_var.get())

        ctk.CTkButton(footer, text="💾 Guardar Compra",
                      fg_color=col["principal"], text_color="#0A192F",
                      hover_color=col.get("principal_hover", "#00C8D4"),
                      width=200, height=40,
                      command=_guardar).pack(side="right", padx=20, pady=12)
