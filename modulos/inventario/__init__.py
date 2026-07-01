"""
modulos/inventario/__init__.py
================================
Módulo Inventario — Ítems, Marca, Departamento, Grupo.
"""
import customtkinter as ctk
from core.permisos import puede


# ─── Submódulos inline ────────────────────────────────────────────────────────

class SubmoduloItems(ctk.CTkFrame):
    """Ítems de inventario con sub-nav: Ítems · Carga · Descarga."""

    def __init__(self, parent, estilos, permisos=None):
        super().__init__(parent, corner_radius=0,
                         fg_color=estilos["colores"]["fondo_oscuro"])
        self.estilos      = estilos
        self.permisos     = permisos or {}
        self._btn_activo  = None
        self._usuario     = "sistema"

        nav = ctk.CTkFrame(self, height=42, corner_radius=0, fg_color="#010A17")
        nav.pack(side="top", fill="x")
        nav.pack_propagate(False)

        self._area = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self._area.pack(fill="both", expand=True)

        col = self.estilos["colores"]
        subs = [("📋 Ítems", self._panel_items),
                ("📥 Carga",  self._panel_carga),
                ("📤 Descarga", self._panel_descarga)]
        primer = None
        for txt, fn in subs:
            btn = ctk.CTkButton(
                nav, text=txt, fg_color="transparent",
                text_color=col["texto_claro"],
                hover_color=col["tarjetas"],
                anchor="center", height=36, width=130)
            btn.pack(side="left", padx=3, pady=3)
            if primer is None:
                primer = (btn, fn)
            def _cmd(b=btn, f=fn):
                self._activar_nav(b)
                self._cargar_panel(f)
            btn.configure(command=_cmd)
        if primer:
            self._activar_nav(primer[0])
            self._cargar_panel(primer[1])

    # ── helpers nav ──────────────────────────────────────────────────────────
    def _activar_nav(self, btn):
        col = self.estilos["colores"]
        if self._btn_activo:
            self._btn_activo.configure(fg_color="transparent",
                                       text_color=col["texto_claro"])
        btn.configure(fg_color=col["tarjetas"], text_color=col["texto_claro"])
        self._btn_activo = btn

    def _cargar_panel(self, fn):
        for w in self._area.winfo_children():
            w.destroy()
        fn(self._area)

    # ════════════════════════════════════════════════════════════════════════
    # SUB-PANEL 1 — Ítems
    # ════════════════════════════════════════════════════════════════════════
    def _panel_items(self, parent):
        from core.database import (get_items_inventario, add_item_inventario,
                                   update_item_inventario, eliminar_item_inventario,
                                   get_marcas, listar_departamentos, listar_grupos)
        col = self.estilos["colores"]
        fnt = self.estilos["fuentes"]

        # ── barra superior ────────────────────────────────────────────────
        bar = ctk.CTkFrame(parent, height=48, corner_radius=0,
                           fg_color=col["tarjetas"])
        bar.pack(fill="x")
        bar.pack_propagate(False)
        ctk.CTkButton(bar, text="➕ Nuevo Ítem",
                      fg_color=col["principal"], text_color="#0A192F",
                      hover_color=col["principal_hover"],
                      width=140, height=32,
                      command=lambda: _abrir_modal()).pack(side="left", padx=10, pady=8)
        busq_var = ctk.StringVar()
        ctk.CTkEntry(bar, textvariable=busq_var, placeholder_text="🔍 Buscar…",
                     width=240, height=32).pack(side="right", padx=10, pady=8)
        busq_var.trace_add("write", lambda *_: _refrescar())

        # ── tabla scroll ──────────────────────────────────────────────────
        cont = ctk.CTkFrame(parent, corner_radius=0, fg_color="transparent")
        cont.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        COLS = ["Código", "Nombre", "Marca", "Departamento",
                "Grupo", "Unidad", "Stock", "Stk.Mín",
                "P.Costo", "P.Venta", ""]
        WIDTHS = [90, 180, 110, 120, 110, 70, 65, 65, 90, 90, 76]

        hdr = ctk.CTkFrame(cont, corner_radius=0, fg_color="#0A192F", height=34)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        for c, w in zip(COLS, WIDTHS):
            ctk.CTkLabel(hdr, text=c, width=w, anchor="center",
                         text_color=col["texto_claro"],
                         font=fnt["normal"]).pack(side="left")

        scroll = ctk.CTkScrollableFrame(cont, corner_radius=0,
                                        fg_color=col["fondo_oscuro"])
        scroll.pack(fill="both", expand=True)

        _filas_items = []

        def _refrescar():
            for w in scroll.winfo_children():
                w.destroy()
            _filas_items.clear()
            rows = get_items_inventario(busq_var.get())
            for i, r in enumerate(rows):
                bg = col["tarjetas"] if i % 2 == 0 else col["fondo_oscuro"]
                fila = ctk.CTkFrame(scroll, corner_radius=0,
                                    fg_color=bg, height=34)
                fila.pack(fill="x")
                fila.pack_propagate(False)
                _filas_items.append(fila)
                vals = [r["codigo"], r["nombre"],
                        r.get("marca_nombre") or "-",
                        r.get("departamento_nombre") or "-",
                        r.get("grupo_nombre") or "-",
                        r["unidad_medida"],
                        f'{r["stock"]:.1f}',
                        f'{r["stock_minimo"]:.1f}',
                        f'{r["precio_costo"]:.2f}',
                        f'{r["precio_venta"]:.2f}']
                for v, w in zip(vals, WIDTHS[:-1]):
                    ctk.CTkLabel(fila, text=v, width=w, anchor="center",
                                 text_color=col["texto_claro"],
                                 font=fnt["normal"]).pack(side="left")
                btn_f = ctk.CTkFrame(fila, width=76, corner_radius=0,
                                     fg_color="transparent")
                btn_f.pack(side="left")
                btn_f.pack_propagate(False)
                ctk.CTkButton(btn_f, text="🗑", width=30, height=28,
                              fg_color="#1A3550",
                              hover_color=col.get("error","#E63946"),
                              text_color=col.get("error","#E63946"),
                              command=lambda rid=r["id"]: _eliminar(rid)
                              ).pack(side="right", padx=(2,2))
                ctk.CTkButton(btn_f, text="✏", width=30, height=28,
                              fg_color="#1A3550",
                              hover_color=col["principal_hover"],
                              text_color=col["principal"],
                              command=lambda row=r: _abrir_modal(row)
                              ).pack(side="right", padx=(0,2))

        def _eliminar(rid):
            import tkinter.messagebox as mb
            if mb.askyesno("Eliminar", "¿Eliminar este ítem?"):
                eliminar_item_inventario(rid)
                _refrescar()

        def _abrir_modal(row=None):
            modal = ctk.CTkToplevel(parent)
            modal.title("Editar Ítem" if row else "Nuevo Ítem")
            modal.geometry("560x650")
            modal.grab_set()
            modal.configure(fg_color=col["fondo_oscuro"])

            def lbl(p, t):
                ctk.CTkLabel(p, text=t, text_color=col["texto_claro"],
                             font=fnt["normal"]).pack(anchor="w", padx=20, pady=(8,0))
            def ent(p):
                e = ctk.CTkEntry(p, width=460, height=32)
                e.pack(padx=20)
                return e

            lbl(modal, "Código *")
            e_cod = ent(modal)
            lbl(modal, "Nombre *")
            e_nom = ent(modal)

            # Combos row
            row2 = ctk.CTkFrame(modal, fg_color="transparent")
            row2.pack(fill="x", padx=20, pady=(6,0))
            ctk.CTkLabel(row2, text="Marca", text_color=col["texto_claro"],
                         font=fnt["normal"]).grid(row=0,column=0,sticky="w")
            ctk.CTkLabel(row2, text="Departamento", text_color=col["texto_claro"],
                         font=fnt["normal"]).grid(row=0,column=1,sticky="w",padx=(16,0))
            ctk.CTkLabel(row2, text="Grupo", text_color=col["texto_claro"],
                         font=fnt["normal"]).grid(row=0,column=2,sticky="w",padx=(16,0))

            marcas_list = ["(Ninguna)"] + [m["nombre"] for m in get_marcas()]
            deptos_list = ["(Ninguno)"] + [d[1] for d in listar_departamentos()]
            grupos_all  = listar_grupos()

            cb_marca = ctk.CTkComboBox(row2, values=marcas_list, width=140, state="readonly")
            cb_marca.grid(row=1,column=0)
            cb_marca.set(marcas_list[0])
            cb_depto = ctk.CTkComboBox(row2, values=deptos_list, width=150, state="readonly")
            cb_depto.grid(row=1,column=1,padx=(16,0))
            cb_depto.set(deptos_list[0])
            cb_grupo = ctk.CTkComboBox(row2, values=["(Ninguno)"], width=140, state="readonly")
            cb_grupo.grid(row=1,column=2,padx=(16,0))
            cb_grupo.set("(Ninguno)")

            def _filtrar_grupos(*_):
                dep_n = cb_depto.get()
                dep_id = None
                for d in listar_departamentos():
                    if d[1] == dep_n:
                        dep_id = d[0]; break
                gs = ["(Ninguno)"] + [g[1] for g in grupos_all if g[2] == dep_id] if dep_id else ["(Ninguno)"]
                cb_grupo.configure(values=gs)
                cb_grupo.set(gs[0])
            cb_depto.configure(command=_filtrar_grupos)

            row3 = ctk.CTkFrame(modal, fg_color="transparent")
            row3.pack(fill="x", padx=20, pady=(6,0))
            UNIDADES = ["Unidad","Kg","g","L","mL","m","cm","Caja","Par","Docena","Rollo","Juego"]
            ctk.CTkLabel(row3, text="Unidad de Medida", text_color=col["texto_claro"],
                         font=fnt["normal"]).grid(row=0,column=0,sticky="w")
            ctk.CTkLabel(row3, text="Stock Mínimo", text_color=col["texto_claro"],
                         font=fnt["normal"]).grid(row=0,column=1,sticky="w",padx=(16,0))
            cb_unidad = ctk.CTkComboBox(row3, values=UNIDADES, width=140, state="readonly")
            cb_unidad.grid(row=1,column=0)
            cb_unidad.set("Unidad")
            e_smin = ctk.CTkEntry(row3, width=140, height=32)
            e_smin.grid(row=1,column=1,padx=(16,0))
            e_smin.insert(0,"0")

            # Tasa USDT para referencia de precios
            try:
                from modulos.monedas.db import leer_todas as _leer_monedas
                _tasas = _leer_monedas()
                _usdt = _tasas.get("USDT", {}).get("tasa", 0)
                _tasa_lbl = f"Precios en USD  —  USDT Binance: {_usdt:,.2f} Bs" if _usdt else "Precios en USD"
            except Exception:
                _tasa_lbl = "Precios en USD"
            ctk.CTkLabel(modal, text=_tasa_lbl,
                         text_color=col["principal"], font=fnt["normal"]
                         ).pack(anchor="w", padx=20, pady=(8,0))

            row4 = ctk.CTkFrame(modal, fg_color="transparent")
            row4.pack(fill="x", padx=20, pady=(2,0))
            ctk.CTkLabel(row4, text="Precio Costo (USD)", text_color=col["texto_claro"],
                         font=fnt["normal"]).grid(row=0,column=0,sticky="w")
            ctk.CTkLabel(row4, text="Precio Venta (USD)", text_color=col["texto_claro"],
                         font=fnt["normal"]).grid(row=0,column=1,sticky="w",padx=(16,0))
            e_pcosto = ctk.CTkEntry(row4, width=210, height=32)
            e_pcosto.grid(row=1,column=0)
            e_pcosto.insert(0,"0.00")
            e_pventa = ctk.CTkEntry(row4, width=210, height=32)
            e_pventa.grid(row=1,column=1,padx=(16,0))
            e_pventa.insert(0,"0.00")

            # stock inicial solo en nuevo
            e_stock = None
            if not row:
                lbl(modal, "Stock Inicial")
                e_stock = ent(modal)
                e_stock.insert(0, "0")

            # pre-fill
            if row:
                e_cod.insert(0, row["codigo"])
                e_nom.insert(0, row["nombre"])
                if row.get("marca_nombre"):
                    cb_marca.set(row["marca_nombre"])
                if row.get("departamento_nombre"):
                    cb_depto.set(row["departamento_nombre"])
                    _filtrar_grupos()
                    if row.get("grupo_nombre"):
                        cb_grupo.set(row["grupo_nombre"])
                if row.get("unidad_medida"):
                    cb_unidad.set(row["unidad_medida"])
                e_smin.delete(0,"end"); e_smin.insert(0, str(row["stock_minimo"]))
                e_pcosto.delete(0,"end"); e_pcosto.insert(0, str(row["precio_costo"]))
                e_pventa.delete(0,"end"); e_pventa.insert(0, str(row["precio_venta"]))

            err_lbl = ctk.CTkLabel(modal, text="", text_color="#E63946", font=fnt["normal"])
            err_lbl.pack(pady=(4,0))

            def _guardar():
                cod  = e_cod.get().strip()
                nom  = e_nom.get().strip()
                if not cod or not nom:
                    err_lbl.configure(text="Código y Nombre son obligatorios.")
                    return
                # resolve FKs
                m_id = None
                for m in get_marcas():
                    if m["nombre"] == cb_marca.get(): m_id = m["id"]; break
                d_id = None
                for d in listar_departamentos():
                    if d[1] == cb_depto.get(): d_id = d[0]; break
                g_id = None
                for g in grupos_all:
                    if g[1] == cb_grupo.get(): g_id = g[0]; break
                try:
                    smin  = float(e_smin.get() or 0)
                    pcost = float(e_pcosto.get() or 0)
                    pvta  = float(e_pventa.get() or 0)
                    stk   = float(e_stock.get() or 0) if e_stock else None
                except ValueError:
                    err_lbl.configure(text="Valores numéricos inválidos.")
                    return
                if row:
                    ok = update_item_inventario(
                        row["id"], cod, nom, "",
                        m_id, d_id, g_id, cb_unidad.get(), smin, pcost, pvta)
                else:
                    ok = add_item_inventario(
                        cod, nom, "",
                        m_id, d_id, g_id, cb_unidad.get(),
                        stk, smin, pcost, pvta)
                if not ok:
                    err_lbl.configure(text="El código ya existe.")
                    return
                modal.destroy()
                _refrescar()

            ctk.CTkButton(modal, text="💾 Guardar",
                          fg_color=col["principal"], text_color="#0A192F",
                          hover_color=col["principal_hover"],
                          width=200, height=36,
                          command=_guardar).pack(pady=12)

        _refrescar()

    # ════════════════════════════════════════════════════════════════════════
    # SUB-PANEL 2 — Carga de Inventario
    # ════════════════════════════════════════════════════════════════════════
    def _panel_carga(self, parent):
        from core.database import (get_cargas_inventario, add_carga_inventario,
                                   eliminar_carga_inventario, get_items_inventario,
                                   obtener_proveedores)
        import datetime
        col = self.estilos["colores"]
        fnt = self.estilos["fuentes"]

        bar = ctk.CTkFrame(parent, height=48, corner_radius=0,
                           fg_color=col["tarjetas"])
        bar.pack(fill="x")
        bar.pack_propagate(False)
        ctk.CTkButton(bar, text="➕ Nueva Carga",
                      fg_color=col["principal"], text_color="#0A192F",
                      hover_color=col["principal_hover"],
                      width=140, height=32,
                      command=lambda: _abrir_modal()).pack(side="left", padx=10, pady=8)
        busq_var = ctk.StringVar()
        ctk.CTkEntry(bar, textvariable=busq_var, placeholder_text="🔍 Buscar…",
                     width=240, height=32).pack(side="right", padx=10, pady=8)
        busq_var.trace_add("write", lambda *_: _refrescar())

        cont = ctk.CTkFrame(parent, corner_radius=0, fg_color="transparent")
        cont.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        COLS   = ["Fecha", "Ítem", "Cantidad", "Precio Unit.", "Proveedor", "Referencia", "Usuario", ""]
        WIDTHS = [100, 200, 80, 100, 150, 120, 100, 76]

        hdr = ctk.CTkFrame(cont, corner_radius=0, fg_color="#0A192F", height=34)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        for c, w in zip(COLS, WIDTHS):
            ctk.CTkLabel(hdr, text=c, width=w, anchor="center",
                         text_color=col["texto_claro"],
                         font=fnt["normal"]).pack(side="left")

        scroll = ctk.CTkScrollableFrame(cont, corner_radius=0,
                                        fg_color=col["fondo_oscuro"])
        scroll.pack(fill="both", expand=True)

        def _refrescar():
            for w in scroll.winfo_children():
                w.destroy()
            rows = get_cargas_inventario(busq_var.get())
            for i, r in enumerate(rows):
                bg = col["tarjetas"] if i % 2 == 0 else col["fondo_oscuro"]
                fila = ctk.CTkFrame(scroll, corner_radius=0, fg_color=bg, height=34)
                fila.pack(fill="x")
                fila.pack_propagate(False)
                vals = [r["fecha"], r["item_nombre"], f'{r["cantidad"]:.2f}',
                        f'{r["precio_unitario"]:.2f}', r["proveedor"] or "-",
                        r["referencia"] or "-", r["usuario"] or "-"]
                for v, w in zip(vals, WIDTHS[:-1]):
                    ctk.CTkLabel(fila, text=v, width=w, anchor="center",
                                 text_color=col["texto_claro"],
                                 font=fnt["normal"]).pack(side="left")
                btn_f = ctk.CTkFrame(fila, width=76, corner_radius=0,
                                     fg_color="transparent")
                btn_f.pack(side="left")
                btn_f.pack_propagate(False)
                ctk.CTkButton(btn_f, text="🗑", width=36, height=28,
                              fg_color="#1A3550",
                              hover_color=col.get("error","#E63946"),
                              text_color=col.get("error","#E63946"),
                              command=lambda rid=r["id"]: _eliminar(rid)
                              ).pack(side="right", padx=2)

        def _eliminar(rid):
            import tkinter.messagebox as mb
            if mb.askyesno("Eliminar", "¿Eliminar esta carga? El stock será revertido."):
                eliminar_carga_inventario(rid)
                _refrescar()

        def _abrir_modal():
            modal = ctk.CTkToplevel(parent)
            modal.title("Nueva Carga de Inventario")
            modal.geometry("460x500")
            modal.grab_set()
            modal.configure(fg_color=col["fondo_oscuro"])

            items_list = get_items_inventario()
            items_nombres = [f'{it["codigo"]} — {it["nombre"]}' for it in items_list]

            def lbl(t):
                ctk.CTkLabel(modal, text=t, text_color=col["texto_claro"],
                             font=fnt["normal"]).pack(anchor="w", padx=20, pady=(8,0))
            def ent(def_val=""):
                e = ctk.CTkEntry(modal, width=420, height=32)
                e.pack(padx=20)
                if def_val:
                    e.insert(0, def_val)
                return e

            lbl("Ítem *")
            cb_item = ctk.CTkComboBox(modal, values=items_nombres if items_nombres else ["(Sin ítems)"],
                                      width=420, state="readonly")
            cb_item.pack(padx=20)
            if items_nombres:
                cb_item.set(items_nombres[0])

            row2 = ctk.CTkFrame(modal, fg_color="transparent")
            row2.pack(fill="x", padx=20, pady=(6,0))
            ctk.CTkLabel(row2, text="Cantidad *", text_color=col["texto_claro"],
                         font=fnt["normal"]).grid(row=0,column=0,sticky="w")
            ctk.CTkLabel(row2, text="Precio Unitario", text_color=col["texto_claro"],
                         font=fnt["normal"]).grid(row=0,column=1,sticky="w",padx=(16,0))
            e_cant = ctk.CTkEntry(row2, width=200, height=32)
            e_cant.grid(row=1,column=0)
            e_cant.insert(0,"1")
            e_prec = ctk.CTkEntry(row2, width=200, height=32)
            e_prec.grid(row=1,column=1,padx=(16,0))
            e_prec.insert(0,"0.00")

            lbl("Proveedor")
            provs_list = obtener_proveedores()
            provs_nombres = ["(Ninguno)"] + [p["razon_social"] for p in provs_list]
            cb_prov = ctk.CTkComboBox(modal, values=provs_nombres,
                                      width=420, state="readonly")
            cb_prov.pack(padx=20)
            cb_prov.set(provs_nombres[0])
            lbl("Referencia")
            e_ref = ent()
            lbl("Fecha *")
            e_fecha = ent(datetime.date.today().strftime("%d/%m/%Y"))
            lbl("Observaciones")
            e_obs = ent()

            err_lbl = ctk.CTkLabel(modal, text="", text_color="#E63946", font=fnt["normal"])
            err_lbl.pack(pady=(4,0))

            def _guardar():
                idx = items_nombres.index(cb_item.get()) if cb_item.get() in items_nombres else -1
                if idx < 0:
                    err_lbl.configure(text="Seleccione un ítem válido.")
                    return
                try:
                    cant = float(e_cant.get() or 0)
                    prec = float(e_prec.get() or 0)
                    if cant <= 0:
                        raise ValueError
                except ValueError:
                    err_lbl.configure(text="Cantidad debe ser un número mayor a 0.")
                    return
                item_id = items_list[idx]["id"]
                ok = add_carga_inventario(
                    item_id, cant, prec,
                    cb_prov.get() if cb_prov.get() != "(Ninguno)" else "", e_ref.get().strip(),
                    e_obs.get().strip(), e_fecha.get().strip(),
                    self._usuario)
                if not ok:
                    err_lbl.configure(text="Error al guardar la carga.")
                    return
                modal.destroy()
                _refrescar()

            ctk.CTkButton(modal, text="💾 Guardar Carga",
                          fg_color=col["principal"], text_color="#0A192F",
                          hover_color=col["principal_hover"],
                          width=200, height=36,
                          command=_guardar).pack(pady=12)

        _refrescar()

    # ════════════════════════════════════════════════════════════════════════
    # SUB-PANEL 3 — Descarga de Inventario
    # ════════════════════════════════════════════════════════════════════════
    def _panel_descarga(self, parent):
        from core.database import (get_descargas_inventario, add_descarga_inventario,
                                   eliminar_descarga_inventario, get_items_inventario)
        import datetime
        col = self.estilos["colores"]
        fnt = self.estilos["fuentes"]

        bar = ctk.CTkFrame(parent, height=48, corner_radius=0,
                           fg_color=col["tarjetas"])
        bar.pack(fill="x")
        bar.pack_propagate(False)
        ctk.CTkButton(bar, text="➕ Nueva Descarga",
                      fg_color=col["principal"], text_color="#0A192F",
                      hover_color=col["principal_hover"],
                      width=150, height=32,
                      command=lambda: _abrir_modal()).pack(side="left", padx=10, pady=8)
        busq_var = ctk.StringVar()
        ctk.CTkEntry(bar, textvariable=busq_var, placeholder_text="🔍 Buscar…",
                     width=240, height=32).pack(side="right", padx=10, pady=8)
        busq_var.trace_add("write", lambda *_: _refrescar())

        cont = ctk.CTkFrame(parent, corner_radius=0, fg_color="transparent")
        cont.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        COLS   = ["Fecha", "Ítem", "Cantidad", "Motivo", "Destino", "Referencia", "Usuario", ""]
        WIDTHS = [100, 200, 80, 120, 140, 110, 100, 76]

        hdr = ctk.CTkFrame(cont, corner_radius=0, fg_color="#0A192F", height=34)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        for c, w in zip(COLS, WIDTHS):
            ctk.CTkLabel(hdr, text=c, width=w, anchor="center",
                         text_color=col["texto_claro"],
                         font=fnt["normal"]).pack(side="left")

        scroll = ctk.CTkScrollableFrame(cont, corner_radius=0,
                                        fg_color=col["fondo_oscuro"])
        scroll.pack(fill="both", expand=True)

        def _refrescar():
            for w in scroll.winfo_children():
                w.destroy()
            rows = get_descargas_inventario(busq_var.get())
            for i, r in enumerate(rows):
                bg = col["tarjetas"] if i % 2 == 0 else col["fondo_oscuro"]
                fila = ctk.CTkFrame(scroll, corner_radius=0, fg_color=bg, height=34)
                fila.pack(fill="x")
                fila.pack_propagate(False)
                vals = [r["fecha"], r["item_nombre"], f'{r["cantidad"]:.2f}',
                        r["motivo"] or "-", r["destino"] or "-",
                        r["referencia"] or "-", r["usuario"] or "-"]
                for v, w in zip(vals, WIDTHS[:-1]):
                    ctk.CTkLabel(fila, text=v, width=w, anchor="center",
                                 text_color=col["texto_claro"],
                                 font=fnt["normal"]).pack(side="left")
                btn_f = ctk.CTkFrame(fila, width=76, corner_radius=0,
                                     fg_color="transparent")
                btn_f.pack(side="left")
                btn_f.pack_propagate(False)
                ctk.CTkButton(btn_f, text="🗑", width=36, height=28,
                              fg_color="#1A3550",
                              hover_color=col.get("error","#E63946"),
                              text_color=col.get("error","#E63946"),
                              command=lambda rid=r["id"]: _eliminar(rid)
                              ).pack(side="right", padx=2)

        def _eliminar(rid):
            import tkinter.messagebox as mb
            if mb.askyesno("Eliminar", "¿Eliminar esta descarga? El stock será repuesto."):
                eliminar_descarga_inventario(rid)
                _refrescar()

        def _abrir_modal():
            modal = ctk.CTkToplevel(parent)
            modal.title("Nueva Descarga de Inventario")
            modal.geometry("460x520")
            modal.grab_set()
            modal.configure(fg_color=col["fondo_oscuro"])

            items_list   = get_items_inventario()
            items_nombres = [f'{it["codigo"]} — {it["nombre"]} (stock: {it["stock"]:.1f})' for it in items_list]
            MOTIVOS = ["Venta", "Uso Interno", "Daño / Merma", "Devolución", "Ajuste", "Otro"]

            def lbl(t):
                ctk.CTkLabel(modal, text=t, text_color=col["texto_claro"],
                             font=fnt["normal"]).pack(anchor="w", padx=20, pady=(8,0))
            def ent(def_val=""):
                e = ctk.CTkEntry(modal, width=420, height=32)
                e.pack(padx=20)
                if def_val:
                    e.insert(0, def_val)
                return e

            lbl("Ítem *")
            cb_item = ctk.CTkComboBox(modal, values=items_nombres if items_nombres else ["(Sin ítems)"],
                                      width=420, state="readonly")
            cb_item.pack(padx=20)
            if items_nombres:
                cb_item.set(items_nombres[0])

            row2 = ctk.CTkFrame(modal, fg_color="transparent")
            row2.pack(fill="x", padx=20, pady=(6,0))
            ctk.CTkLabel(row2, text="Cantidad *", text_color=col["texto_claro"],
                         font=fnt["normal"]).grid(row=0,column=0,sticky="w")
            ctk.CTkLabel(row2, text="Motivo *", text_color=col["texto_claro"],
                         font=fnt["normal"]).grid(row=0,column=1,sticky="w",padx=(16,0))
            e_cant = ctk.CTkEntry(row2, width=190, height=32)
            e_cant.grid(row=1,column=0)
            e_cant.insert(0,"1")
            cb_motivo = ctk.CTkComboBox(row2, values=MOTIVOS, width=200, state="readonly")
            cb_motivo.grid(row=1,column=1,padx=(16,0))
            cb_motivo.set(MOTIVOS[0])

            lbl("Destino")
            e_dest = ent()
            lbl("Referencia")
            e_ref = ent()
            lbl("Fecha *")
            e_fecha = ent(datetime.date.today().strftime("%d/%m/%Y"))
            lbl("Observaciones")
            e_obs = ent()

            err_lbl = ctk.CTkLabel(modal, text="", text_color="#E63946", font=fnt["normal"])
            err_lbl.pack(pady=(4,0))

            def _guardar():
                idx = items_nombres.index(cb_item.get()) if cb_item.get() in items_nombres else -1
                if idx < 0:
                    err_lbl.configure(text="Seleccione un ítem válido.")
                    return
                try:
                    cant = float(e_cant.get() or 0)
                    if cant <= 0:
                        raise ValueError
                except ValueError:
                    err_lbl.configure(text="Cantidad debe ser un número mayor a 0.")
                    return
                item_id = items_list[idx]["id"]
                ok = add_descarga_inventario(
                    item_id, cant, 0,
                    cb_motivo.get(), e_dest.get().strip(),
                    e_ref.get().strip(), e_obs.get().strip(),
                    e_fecha.get().strip(), self._usuario)
                if not ok:
                    err_lbl.configure(text="Error al guardar la descarga.")
                    return
                modal.destroy()
                _refrescar()

            ctk.CTkButton(modal, text="💾 Guardar Descarga",
                          fg_color=col["principal"], text_color="#0A192F",
                          hover_color=col["principal_hover"],
                          width=220, height=36,
                          command=_guardar).pack(pady=12)

        _refrescar()


class SubmoduloMarca(ctk.CTkFrame):
    def __init__(self, parent, estilos, permisos=None):
        super().__init__(parent, corner_radius=0,
                         fg_color=estilos["colores"]["fondo_oscuro"])
        self.estilos = estilos
        self._ui()

    def _ui(self):
        from core.database import get_marcas, add_marca, update_marca, eliminar_marca
        self._db_get    = get_marcas
        self._db_add    = add_marca
        self._db_update = update_marca
        self._db_del    = eliminar_marca

        col  = self.estilos["colores"]
        fnt  = self.estilos["fuentes"]

        # ── Barra superior ────────────────────────────────────────────────
        barra = ctk.CTkFrame(self, fg_color=col["tarjetas"], corner_radius=10)
        barra.pack(fill="x", padx=20, pady=(18, 6))

        ctk.CTkButton(
            barra, text="➕  Nueva Marca",
            fg_color=col["principal"], hover_color=col["principal_hover"],
            text_color="#0A192F",
            font=fnt["normal"], width=160, height=32,
            command=self._modal
        ).pack(side="left", padx=12, pady=8)

        self._var_buscar = ctk.StringVar()
        self._var_buscar.trace_add("write", lambda *_: self._refrescar())
        ctk.CTkEntry(
            barra, textvariable=self._var_buscar,
            placeholder_text="🔍  Buscar marca…",
            width=260, height=32
        ).pack(side="left", padx=6, pady=8)

        # ── Encabezado tabla ──────────────────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color="#0A192F", corner_radius=8)
        hdr.pack(fill="x", padx=20, pady=(4, 0))
        hdr.columnconfigure(0, weight=1)
        hdr.columnconfigure(1, minsize=90)
        for c, t, anchor in [(0, "Marca", "w"), (1, "Acciones", "center")]:
            ctk.CTkLabel(hdr, text=t, font=fnt["normal"],
                         text_color=col["texto_claro"],
                         anchor=anchor).grid(row=0, column=c,
                                             padx=12, pady=6, sticky="ew")

        # ── Lista scrollable ──────────────────────────────────────────────
        self._lista_frame = ctk.CTkScrollableFrame(
            self, fg_color=col["fondo_oscuro"], corner_radius=0)
        self._lista_frame.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        self._refrescar()

    def _refrescar(self):
        col  = self.estilos["colores"]
        fnt  = self.estilos["fuentes"]
        filtro = self._var_buscar.get() if hasattr(self, "_var_buscar") else ""

        for w in self._lista_frame.winfo_children():
            w.destroy()

        marcas = self._db_get(filtro)

        if not marcas:
            ctk.CTkLabel(self._lista_frame,
                         text="No hay marcas registradas.",
                         font=fnt["normal"], text_color="#4A6FA5").pack(pady=30)
            return

        for i, m in enumerate(marcas):
            bg = col["tarjetas"] if i % 2 == 0 else col["fondo_oscuro"]
            fila = ctk.CTkFrame(self._lista_frame, fg_color=bg, corner_radius=6)
            fila.pack(fill="x", pady=1)
            fila.columnconfigure(0, weight=1)
            fila.columnconfigure(1, minsize=90)

            ctk.CTkLabel(fila, text=m["nombre"], font=fnt["normal"],
                         text_color=col["texto_claro"],
                         anchor="w").grid(row=0, column=0,
                                          padx=12, pady=6, sticky="ew")

            btn_f = ctk.CTkFrame(fila, fg_color="transparent",
                                 width=90, height=34)
            btn_f.pack_propagate(False)
            btn_f.grid(row=0, column=1, padx=4, pady=2)

            ctk.CTkButton(
                btn_f, text="🗑", width=36, height=28,
                fg_color="#1A3550", hover_color=col["error"],
                text_color=col["error"], font=fnt["normal"],
                command=lambda mid=m["id"], mn=m["nombre"]: self._eliminar(mid, mn)
            ).pack(side="right", padx=2)

            ctk.CTkButton(
                btn_f, text="✏️", width=36, height=28,
                fg_color="#1A3550", hover_color=col["principal_hover"],
                text_color=col["principal"], font=fnt["normal"],
                command=lambda mid=m["id"], mn=m["nombre"]: self._modal(mid, mn)
            ).pack(side="right", padx=2)

    def _modal(self, marca_id=None, nombre_actual=""):
        col = self.estilos["colores"]
        fnt = self.estilos["fuentes"]
        es_nuevo = marca_id is None

        win = ctk.CTkToplevel(self)
        win.title("Nueva Marca" if es_nuevo else "Editar Marca")
        win.geometry("360x200")
        win.resizable(False, False)
        win.grab_set()

        ctk.CTkLabel(win, text="🏷  " + ("Nueva Marca" if es_nuevo else "Editar Marca"),
                     font=fnt["subtitulo"],
                     text_color=col["texto_oscuro"]).pack(pady=(20, 10))

        var_nombre = ctk.StringVar(value=nombre_actual)
        ctk.CTkEntry(win, textvariable=var_nombre,
                     placeholder_text="Nombre de la marca",
                     width=280, height=36).pack(pady=6)

        lbl_err = ctk.CTkLabel(win, text="", font=fnt["normal"],
                                text_color="#E74C3C")
        lbl_err.pack()

        def _guardar():
            nombre = var_nombre.get().strip()
            if not nombre:
                lbl_err.configure(text="El nombre es obligatorio.")
                return
            if es_nuevo:
                ok = self._db_add(nombre)
            else:
                ok = self._db_update(marca_id, nombre)
            if not ok:
                lbl_err.configure(text="Ya existe una marca con ese nombre.")
                return
            win.destroy()
            self._refrescar()

        ctk.CTkButton(
            win, text="💾  Guardar",
            fg_color=col["principal"], hover_color=col["principal_hover"],
            text_color="#0A192F",
            font=fnt["normal"], width=140, height=34,
            command=_guardar
        ).pack(pady=10)

    def _eliminar(self, marca_id, nombre):
        from tkinter import messagebox
        if messagebox.askyesno("Eliminar Marca",
                               f"¿Eliminar la marca «{nombre}»?\nEsta acción no se puede deshacer."):
            self._db_del(marca_id)
            self._refrescar()


class SubmoduloDepartamento(ctk.CTkFrame):
    def __init__(self, parent, estilos, permisos=None):
        super().__init__(parent, corner_radius=0,
                         fg_color=estilos["colores"]["fondo_oscuro"])
        self.estilos = estilos
        self._datos = []
        self._ui()

    # ── UI principal ──────────────────────────────────────────────────────────
    def _ui(self):
        from core.database import listar_departamentos
        col = self.estilos["colores"]
        fnt = self.estilos["fuentes"]

        # Barra superior
        top = ctk.CTkFrame(self, fg_color="#020C1B", corner_radius=8)
        top.pack(fill="x", padx=12, pady=(10, 4))
        ctk.CTkButton(
            top, text="➕  Nuevo Departamento",
            font=fnt["normal"], fg_color=col["principal"],
            hover_color=col["principal_hover"], text_color="#0A192F",
            height=34, corner_radius=6,
            command=self._modal
        ).pack(side="left", padx=8, pady=6)
        self._search_var = ctk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._refrescar())
        ctk.CTkEntry(
            top, textvariable=self._search_var,
            placeholder_text="🔍  Buscar departamento…",
            font=fnt["normal"], height=32, width=260,
            fg_color="#0A192F", border_color="#1E3A5F",
            text_color=col["texto_claro"]
        ).pack(side="left", padx=8, pady=6)

        # Encabezado tabla
        hdr = ctk.CTkFrame(self, fg_color="#0A192F", corner_radius=6, height=30)
        hdr.pack(fill="x", padx=12, pady=(0, 2))
        hdr.pack_propagate(False)
        ctk.CTkLabel(hdr, text="Nombre del Departamento", font=fnt["normal"],
                     text_color=col["texto_claro"], anchor="w").pack(
            side="left", padx=12, fill="x", expand=True)
        ctk.CTkLabel(hdr, text="Acciones", font=fnt["normal"],
                     text_color=col["texto_claro"], width=76, anchor="center").pack(
            side="right", padx=8)

        # Lista scrollable
        self._scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent", corner_radius=0)
        self._scroll.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        self._refrescar()

    def _refrescar(self):
        from core.database import listar_departamentos
        q = self._search_var.get().lower().strip()
        self._datos = listar_departamentos()
        for w in self._scroll.winfo_children():
            w.destroy()
        col = self.estilos["colores"]
        fnt = self.estilos["fuentes"]
        for idx, (dep_id, nombre) in enumerate(self._datos):
            if q and q not in nombre.lower():
                continue
            bg = "#0D1F35" if idx % 2 == 0 else "#0A192F"
            fila = ctk.CTkFrame(self._scroll, fg_color=bg, corner_radius=4, height=34)
            fila.pack(fill="x", pady=1)
            fila.pack_propagate(False)
            ctk.CTkLabel(fila, text=nombre, font=fnt["normal"],
                         text_color=col["texto_claro"], anchor="w").pack(
                side="left", padx=12, fill="x", expand=True)
            # Botones acciones (derecha primero)
            btn_frame = ctk.CTkFrame(fila, fg_color="transparent", width=76)
            btn_frame.pack(side="right", padx=4)
            btn_frame.pack_propagate(False)
            ctk.CTkButton(
                btn_frame, text="🗑", width=30, height=26, corner_radius=4,
                fg_color="#1A3550", hover_color=col["error"],
                text_color=col["error"], font=fnt["normal"],
                command=lambda i=dep_id, n=nombre: self._eliminar(i, n)
            ).pack(side="right", padx=2)
            ctk.CTkButton(
                btn_frame, text="✏️", width=30, height=26, corner_radius=4,
                fg_color="#1A3550", hover_color=col["principal_hover"],
                text_color=col["principal"], font=fnt["normal"],
                command=lambda i=dep_id, n=nombre: self._modal(i, n)
            ).pack(side="right", padx=2)

        if not self._scroll.winfo_children():
            ctk.CTkLabel(self._scroll, text="Sin departamentos registrados.",
                         font=fnt["normal"], text_color="#4A6FA5").pack(pady=30)

    def _modal(self, dep_id=None, nombre_actual=""):
        from core.database import crear_departamento, actualizar_departamento
        col = self.estilos["colores"]
        fnt = self.estilos["fuentes"]
        win = ctk.CTkToplevel(self)
        win.title("Editar Departamento" if dep_id else "Nuevo Departamento")
        win.geometry("400x180")
        win.resizable(False, False)
        win.configure(fg_color="#020C1B")
        win.grab_set()
        ctk.CTkLabel(win, text="Editar Departamento" if dep_id else "Nuevo Departamento",
                     font=fnt["subtitulo"], text_color=col["principal"]).pack(pady=(16, 8))
        ctk.CTkLabel(win, text="Nombre *", font=fnt["normal"],
                     text_color="#94A3B8").pack(anchor="w", padx=20)
        var = ctk.StringVar(value=nombre_actual)
        entry = ctk.CTkEntry(win, textvariable=var, height=34,
                             fg_color="#0A192F", border_color="#1E3A5F",
                             text_color=col["texto_claro"], font=fnt["normal"])
        entry.pack(fill="x", padx=20, pady=(2, 12))
        lbl_err = ctk.CTkLabel(win, text="", font=fnt["normal"],
                               text_color=col.get("error", "#EF4444"))
        lbl_err.pack()

        def _guardar():
            nombre = var.get().strip()
            if not nombre:
                lbl_err.configure(text="El nombre es obligatorio.")
                return
            if dep_id:
                ok = actualizar_departamento(dep_id, nombre)
                if not ok:
                    lbl_err.configure(text="Ese nombre ya existe.")
                    return
            else:
                r = crear_departamento(nombre)
                if r == -1:
                    lbl_err.configure(text="Ese nombre ya existe.")
                    return
            win.destroy()
            self._refrescar()

        ctk.CTkButton(win, text="Guardar", fg_color=col["principal"],
                      hover_color=col["principal_hover"], text_color="#0A192F",
                      font=fnt["normal"], height=34, command=_guardar).pack(pady=4)

    def _eliminar(self, dep_id, nombre):
        from core.database import eliminar_departamento
        from tkinter import messagebox
        if messagebox.askyesno("Eliminar", f"¿Eliminar el departamento «{nombre}»?\n"
                               "Se eliminarán también los grupos asociados."):
            eliminar_departamento(dep_id)
            self._refrescar()


class SubmoduloGrupo(ctk.CTkFrame):
    def __init__(self, parent, estilos, permisos=None):
        super().__init__(parent, corner_radius=0,
                         fg_color=estilos["colores"]["fondo_oscuro"])
        self.estilos = estilos
        self._ui()

    # ── UI principal ──────────────────────────────────────────────────────────
    def _ui(self):
        col = self.estilos["colores"]
        fnt = self.estilos["fuentes"]

        # Barra superior
        top = ctk.CTkFrame(self, fg_color="#020C1B", corner_radius=8)
        top.pack(fill="x", padx=12, pady=(10, 4))
        ctk.CTkButton(
            top, text="➕  Nuevo Grupo",
            font=fnt["normal"], fg_color=col["principal"],
            hover_color=col["principal_hover"], text_color="#0A192F",
            height=34, corner_radius=6,
            command=self._modal
        ).pack(side="left", padx=8, pady=6)
        self._search_var = ctk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._refrescar())
        ctk.CTkEntry(
            top, textvariable=self._search_var,
            placeholder_text="🔍  Buscar grupo o departamento…",
            font=fnt["normal"], height=32, width=280,
            fg_color="#0A192F", border_color="#1E3A5F",
            text_color=col["texto_claro"]
        ).pack(side="left", padx=8, pady=6)

        # Encabezado tabla
        hdr = ctk.CTkFrame(self, fg_color="#0A192F", corner_radius=6, height=30)
        hdr.pack(fill="x", padx=12, pady=(0, 2))
        hdr.pack_propagate(False)
        ctk.CTkLabel(hdr, text="Grupo", font=fnt["normal"],
                     text_color=col["texto_claro"], anchor="w", width=200).pack(
            side="left", padx=12)
        ctk.CTkLabel(hdr, text="Departamento", font=fnt["normal"],
                     text_color=col["texto_claro"], anchor="w").pack(
            side="left", padx=8, fill="x", expand=True)
        ctk.CTkLabel(hdr, text="Acciones", font=fnt["normal"],
                     text_color=col["texto_claro"], width=76, anchor="center").pack(
            side="right", padx=8)

        # Lista scrollable
        self._scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent", corner_radius=0)
        self._scroll.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        self._refrescar()

    def _refrescar(self):
        from core.database import listar_grupos
        q = self._search_var.get().lower().strip()
        datos = listar_grupos()  # (id, nombre, dep_id, dep_nombre)
        for w in self._scroll.winfo_children():
            w.destroy()
        col = self.estilos["colores"]
        fnt = self.estilos["fuentes"]
        for idx, (g_id, g_nombre, dep_id, dep_nombre) in enumerate(datos):
            if q and q not in g_nombre.lower() and q not in dep_nombre.lower():
                continue
            bg = "#0D1F35" if idx % 2 == 0 else "#0A192F"
            fila = ctk.CTkFrame(self._scroll, fg_color=bg, corner_radius=4, height=34)
            fila.pack(fill="x", pady=1)
            fila.pack_propagate(False)
            ctk.CTkLabel(fila, text=g_nombre, font=fnt["normal"],
                         text_color=col["texto_claro"], anchor="w", width=200).pack(
                side="left", padx=12)
            ctk.CTkLabel(fila, text=dep_nombre, font=fnt["normal"],
                         text_color="#94A3B8", anchor="w").pack(
                side="left", padx=8, fill="x", expand=True)
            btn_frame = ctk.CTkFrame(fila, fg_color="transparent", width=76)
            btn_frame.pack(side="right", padx=4)
            btn_frame.pack_propagate(False)
            ctk.CTkButton(
                btn_frame, text="🗑", width=30, height=26, corner_radius=4,
                fg_color="#1A3550", hover_color=col["error"],
                text_color=col["error"], font=fnt["normal"],
                command=lambda i=g_id, n=g_nombre: self._eliminar(i, n)
            ).pack(side="right", padx=2)
            ctk.CTkButton(
                btn_frame, text="✏️", width=30, height=26, corner_radius=4,
                fg_color="#1A3550", hover_color=col["principal_hover"],
                text_color=col["principal"], font=fnt["normal"],
                command=lambda i=g_id, n=g_nombre, d=dep_id: self._modal(i, n, d)
            ).pack(side="right", padx=2)

        if not self._scroll.winfo_children():
            ctk.CTkLabel(self._scroll,
                         text="Sin grupos registrados.\nCrea primero al menos un departamento.",
                         font=fnt["normal"], text_color="#4A6FA5",
                         justify="center").pack(pady=30)

    def _modal(self, grupo_id=None, nombre_actual="", dep_actual=None):
        from core.database import (listar_departamentos, crear_grupo,
                                   actualizar_grupo)
        col = self.estilos["colores"]
        fnt = self.estilos["fuentes"]
        deps = listar_departamentos()   # [(id, nombre), ...]
        if not deps:
            from tkinter import messagebox
            messagebox.showwarning("Sin departamentos",
                                   "Debes crear al menos un departamento antes de agregar grupos.")
            return

        win = ctk.CTkToplevel(self)
        win.title("Editar Grupo" if grupo_id else "Nuevo Grupo")
        win.geometry("420x250")
        win.resizable(False, False)
        win.configure(fg_color="#020C1B")
        win.grab_set()

        ctk.CTkLabel(win, text="Editar Grupo" if grupo_id else "Nuevo Grupo",
                     font=fnt["subtitulo"], text_color=col["principal"]).pack(pady=(16, 8))

        form = ctk.CTkFrame(win, fg_color="transparent")
        form.pack(fill="x", padx=20)

        ctk.CTkLabel(form, text="Nombre *", font=fnt["normal"],
                     text_color="#94A3B8", anchor="w").grid(
            row=0, column=0, sticky="w", pady=2)
        var_nombre = ctk.StringVar(value=nombre_actual)
        ctk.CTkEntry(form, textvariable=var_nombre, height=34,
                     fg_color="#0A192F", border_color="#1E3A5F",
                     text_color=col["texto_claro"], font=fnt["normal"]).grid(
            row=0, column=1, sticky="ew", padx=(8, 0), pady=2)

        ctk.CTkLabel(form, text="Departamento *", font=fnt["normal"],
                     text_color="#94A3B8", anchor="w").grid(
            row=1, column=0, sticky="w", pady=2)
        dep_nombres = [d[1] for d in deps]
        dep_ids = [d[0] for d in deps]
        # Selección actual
        sel_idx = 0
        if dep_actual is not None:
            try:
                sel_idx = dep_ids.index(dep_actual)
            except ValueError:
                pass
        var_dep = ctk.StringVar(value=dep_nombres[sel_idx])
        ctk.CTkComboBox(form, values=dep_nombres, variable=var_dep,
                        height=34, fg_color="#0A192F",
                        border_color="#1E3A5F", button_color="#1E3A5F",
                        text_color=col["texto_claro"],
                        dropdown_fg_color="#0D1F35",
                        dropdown_text_color=col["texto_claro"],
                        font=fnt["normal"], state="readonly").grid(
            row=1, column=1, sticky="ew", padx=(8, 0), pady=2)
        form.columnconfigure(1, weight=1)

        lbl_err = ctk.CTkLabel(win, text="", font=fnt["normal"],
                               text_color=col.get("error", "#EF4444"))
        lbl_err.pack(pady=(8, 0))

        def _guardar():
            nombre = var_nombre.get().strip()
            dep_nombre_sel = var_dep.get()
            if not nombre:
                lbl_err.configure(text="El nombre es obligatorio.")
                return
            if not dep_nombre_sel or dep_nombre_sel not in dep_nombres:
                lbl_err.configure(text="Selecciona un departamento.")
                return
            dep_id_sel = dep_ids[dep_nombres.index(dep_nombre_sel)]
            if grupo_id:
                ok = actualizar_grupo(grupo_id, nombre, dep_id_sel)
                if not ok:
                    lbl_err.configure(text="Ese nombre de grupo ya existe.")
                    return
            else:
                r = crear_grupo(nombre, dep_id_sel)
                if r == -1:
                    lbl_err.configure(text="Ese nombre de grupo ya existe.")
                    return
            win.destroy()
            self._refrescar()

        ctk.CTkButton(win, text="Guardar", fg_color=col["principal"],
                      hover_color=col["principal_hover"], text_color="#0A192F",
                      font=fnt["normal"], height=34, command=_guardar).pack(pady=10)

    def _eliminar(self, grupo_id, nombre):
        from core.database import eliminar_grupo
        from tkinter import messagebox
        if messagebox.askyesno("Eliminar", f"¿Eliminar el grupo «{nombre}»?"):
            eliminar_grupo(grupo_id)
            self._refrescar()


# ─── Módulo principal ─────────────────────────────────────────────────────────

class ModuloInventario(ctk.CTkFrame):
    def __init__(self, parent, estilos, permisos=None):
        super().__init__(parent, corner_radius=0,
                         fg_color=estilos["colores"]["fondo_oscuro"])
        self.estilos     = estilos
        self.permisos    = permisos or {}
        self._btn_activo = None
        self.area = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self._construir_barra_nav()
        self.area.pack(side="bottom", fill="both", expand=True)

    def _construir_barra_nav(self):
        col = self.estilos["colores"]
        barra = ctk.CTkFrame(self, height=50, corner_radius=0, fg_color="#020C1B")
        barra.pack(side="top", fill="x")
        barra.pack_propagate(False)

        todas = [
            ("Inventario.Items",        "📦 Ítems",        SubmoduloItems),
            ("Inventario.Marca",        "🏷 Marca",         SubmoduloMarca),
            ("Inventario.Departamento", "🏢 Departamento",  SubmoduloDepartamento),
            ("Inventario.Grupo",        "🗂 Grupo",          SubmoduloGrupo),
        ]

        primer_btn = primer_clase = None
        for clave, texto, clase in todas:
            if not puede(self.permisos, clave, "ver"):
                continue
            btn = ctk.CTkButton(
                barra, text=texto,
                fg_color="transparent",
                text_color=col["texto_oscuro"],
                hover_color=col["tarjetas"],
                anchor="center", height=40, width=150,
            )
            btn.pack(side="left", padx=4, pady=5)
            if primer_btn is None:
                primer_btn, primer_clase = btn, clase

            def _cmd(c=clase, b=btn):
                self._activar(b)
                self._cargar(c)
            btn.configure(command=_cmd)

        if primer_btn:
            self._activar(primer_btn)
            self._cargar(primer_clase)

    def _activar(self, btn):
        col = self.estilos["colores"]
        if self._btn_activo:
            self._btn_activo.configure(fg_color="transparent",
                                       text_color=col["texto_oscuro"])
        btn.configure(fg_color=col["tarjetas"], text_color=col["texto_oscuro"])
        self._btn_activo = btn

    def _cargar(self, clase):
        for w in self.area.winfo_children():
            w.destroy()
        clase(self.area, self.estilos, self.permisos).pack(fill="both", expand=True)
