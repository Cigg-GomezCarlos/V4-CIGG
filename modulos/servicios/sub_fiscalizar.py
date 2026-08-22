"""
modulos/servicios/sub_fiscalizar.py
====================================
Submódulo Fiscalizar — lista de máquinas sin cliente asignado
con filtros por columna (debajo de cada encabezado).
Tabla ajustada al 100% del ancho disponible.
"""
import customtkinter as ctk
from tkinter import messagebox

from modulos.ventas.sub_cotizaciones import AutocompleteEntry


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
    frame.pack(side="left", fill="x", expand=True)
    frame.pack_propagate(False)
    lbl = ctk.CTkLabel(frame, text=disp, anchor="center",
                       text_color=text_color, font=font)
    lbl.pack(fill="both", expand=True)
    if disp != str(full_text or ""):
        _ToolTip(lbl, str(full_text))
    return frame


class SubmoduloFiscalizar(ctk.CTkFrame):
    """
    Lista máquinas sin cliente asignado.
    Filtros individuales debajo de cada encabezado.
    Tabla ajustada al ancho completo de la pantalla.
    """
    COLS   = ["Registro", "Serial", "Modelo", "Fabricante", "Firmware", ""]
    # Anchos ajustados para cubrir el 100% del ancho disponible (~940px)
    WIDTHS = [160, 170, 210, 190, 120, 130]
    COL_DB = ["numero_registro", "numero_serial", "modelo_nombre",
              "fabricante", "firmware", None]

    def __init__(self, parent, estilos, permisos=None):
        super().__init__(parent, corner_radius=0,
                         fg_color=estilos["colores"]["fondo_oscuro"])
        self.estilos  = estilos
        self.permisos = permisos or {}
        self.col      = estilos["colores"]
        self.fnt      = estilos["fuentes"]
        self._filtros = {}
        self._construir_ui()
        self.after(0, self.cargar_datos)

    def _construir_ui(self):
        col, fnt = self.col, self.fnt

        # ── Barra superior (solo título) ──
        bar = ctk.CTkFrame(self, height=52, corner_radius=0, fg_color="#020C1B")
        bar.pack(fill="x")
        bar.pack_propagate(False)

        ctk.CTkLabel(bar, text="🔍  Fiscalizar", font=fnt["titulo"],
                     text_color=col["principal"]).pack(side="left", padx=16, pady=8)

        # ── Contenedor scrollable ──
        cont = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        cont.pack(fill="both", expand=True, padx=12, pady=8)

        # ── Header + filtros ──
        self.hdr_frame = ctk.CTkFrame(cont, corner_radius=0,
                                        fg_color="transparent")
        self.hdr_frame.pack(fill="x")

        # Fila de títulos (ocupa todo el ancho)
        tit_row = ctk.CTkFrame(self.hdr_frame, corner_radius=0, fg_color="#0A192F", height=30)
        tit_row.pack(fill="x")
        tit_row.pack_propagate(False)
        for ctext, w in zip(self.COLS, self.WIDTHS):
            f = ctk.CTkFrame(tit_row, width=w, height=30, corner_radius=0,
                             fg_color="transparent")
            f.pack(side="left", fill="x", expand=True)
            f.pack_propagate(False)
            ctk.CTkLabel(f, text=ctext, anchor="center",
                         text_color=col["texto_claro"],
                         font=fnt["normal"]).pack(fill="both", expand=True)

        # Fila de filtros
        fil_row = ctk.CTkFrame(self.hdr_frame, corner_radius=0,
                                 fg_color=col["tarjetas"], height=32)
        fil_row.pack(fill="x")
        fil_row.pack_propagate(False)

        for idx, w in enumerate(self.WIDTHS):
            if self.COL_DB[idx] is None:
                pad = ctk.CTkFrame(fil_row, width=w, height=32, corner_radius=0,
                                   fg_color="transparent")
                pad.pack(side="left", fill="x", expand=True)
                pad.pack_propagate(False)
                continue

            var = ctk.StringVar()
            self._filtros[idx] = var
            f = ctk.CTkFrame(fil_row, width=w, height=32, corner_radius=0,
                             fg_color="transparent")
            f.pack(side="left", fill="x", expand=True)
            f.pack_propagate(False)
            ent = ctk.CTkEntry(f, textvariable=var, height=26,
                               placeholder_text="Filtrar…",
                               font=("Segoe UI", 9))
            ent.pack(fill="x", padx=4, pady=3)
            var.trace_add("write", lambda *_: self.cargar_datos())

        # ── Scroll de datos ──
        self.scroll = ctk.CTkScrollableFrame(cont, corner_radius=0,
                                             fg_color=col["fondo_oscuro"])
        self.scroll.pack(fill="both", expand=True)

        # ── Pie de página ──
        self.footer = ctk.CTkFrame(cont, height=28, corner_radius=0,
                                     fg_color="transparent")
        self.footer.pack(fill="x", pady=(4, 0))
        self.footer.pack_propagate(False)

        self.lbl_footer = ctk.CTkLabel(
            self.footer, text="",
            text_color=col.get("texto_oscuro", "#94A3B8"),
            font=("Roboto Mono", 10),
        )
        self.lbl_footer.pack(side="right", padx=14)

    def cargar_datos(self):
        from core.database import listar_maquinas_sin_cliente
        col, fnt = self.col, self.fnt

        for w in self.scroll.winfo_children():
            w.destroy()

        try:
            rows = listar_maquinas_sin_cliente()
        except Exception as e:
            ctk.CTkLabel(self.scroll, text=f"Error al cargar: {e}",
                         text_color="#E63946", font=fnt["normal"]).pack(pady=20)
            self.lbl_footer.configure(text="")
            return

        # Aplicar filtros por columna
        for idx, db_field in enumerate(self.COL_DB):
            if db_field is None:
                continue
            filtro = self._filtros[idx].get().strip().lower()
            if filtro:
                rows = [r for r in rows if filtro in str(r.get(db_field, "")).lower()]

        if not rows:
            ctk.CTkLabel(self.scroll,
                         text="🎉  No hay máquinas pendientes por fiscalizar",
                         text_color=col["principal"],
                         font=fnt["subtitulo"]).pack(pady=40)
            self.lbl_footer.configure(text="")
            return

        for i, r in enumerate(rows):
            bg = col["tarjetas"] if i % 2 == 0 else col["fondo_oscuro"]
            fila = ctk.CTkFrame(self.scroll, corner_radius=0, fg_color=bg, height=34)
            fila.pack(fill="x")
            fila.pack_propagate(False)

            vals = [
                (r["numero_registro"],  col["texto_claro"]),
                (r["numero_serial"],    col["texto_claro"]),
                (r["modelo_nombre"],    col["texto_claro"]),
                (r["fabricante"],       col["texto_claro"]),
                (r["firmware"],         col["texto_claro"]),
            ]
            for (v, tc), w in zip(vals, self.WIDTHS[:-1]):
                _cell(fila, v, w, 34, tc, fnt["normal"])

            # Celda de acciones (ancho fijo, alineada a la derecha)
            btn_f = ctk.CTkFrame(fila, width=self.WIDTHS[-1], corner_radius=0,
                                 fg_color="transparent")
            btn_f.pack(side="left", fill="x", expand=True)
            btn_f.pack_propagate(False)

            ctk.CTkButton(btn_f, text="👤 Asignar Cliente", width=120, height=28,
                          fg_color=col["principal"],
                          hover_color=col.get("principal_hover", "#00C8D4"),
                          text_color="#0A192F",
                          font=("Segoe UI", 10),
                          command=lambda rid=r["id"], reg=r["numero_registro"],
                                         mod=r["modelo_nombre"]:
                                         self._abrir_asignar(rid, reg, mod)
                          ).pack(side="right", padx=4)

        self.lbl_footer.configure(text=f"Máquinas sin fiscalizar: {len(rows)}")

    def _abrir_asignar(self, maquina_id, registro, modelo):
        from core.database import obtener_clientes, asignar_cliente_maquina
        col, fnt = self.col, self.fnt

        modal = ctk.CTkToplevel(self)
        modal.title(f"Fiscalizar — {registro}")
        modal.geometry("520x380")
        modal.configure(fg_color=col["fondo_oscuro"])
        modal.transient(self.winfo_toplevel())
        modal.lift()
        modal.after(60, lambda: (modal.lift(), modal.focus_force(),
                                 modal.grab_set()))

        body = ctk.CTkFrame(modal, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=20, pady=16)

        info = ctk.CTkFrame(body, fg_color=col["tarjetas"], corner_radius=8)
        info.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(info, text=f"Máquina: {registro}",
                     text_color=col["principal"], font=fnt["subtitulo"]
                     ).pack(anchor="w", padx=12, pady=(8, 2))
        ctk.CTkLabel(info, text=f"Modelo: {modelo}",
                     text_color=col["texto_claro"], font=fnt["normal"]
                     ).pack(anchor="w", padx=12, pady=(2, 8))

        ctk.CTkLabel(body, text="Cliente *  (escribe para filtrar)",
                     text_color=col["texto_claro"],
                     font=fnt["normal"]).pack(anchor="w", pady=(8, 2))

        clientes_list = obtener_clientes()
        cli_nombres = [f'{c["rif"]} — {c["razon_social"]}' for c in clientes_list]
        cb_cli = AutocompleteEntry(body, values=cli_nombres, width=460,
                                   placeholder="RIF o razón social…",
                                   colores=col, fuentes=fnt)
        cb_cli.pack(anchor="w", pady=(0, 8))

        ctk.CTkLabel(body, text="Número de Precinto:",
                     text_color=col["texto_claro"],
                     font=fnt["normal"]).pack(anchor="w", pady=(4, 2))
        e_precinto = ctk.CTkEntry(body, width=460, height=32)
        e_precinto.pack(anchor="w", pady=(0, 12))

        err_lbl = ctk.CTkLabel(body, text="", text_color="#E63946",
                               font=fnt["normal"])
        err_lbl.pack(anchor="w")

        footer = ctk.CTkFrame(modal, height=64, corner_radius=0, fg_color="#020C1B")
        footer.pack(side="bottom", fill="x")
        footer.pack_propagate(False)

        def _guardar():
            sel = cb_cli.get().strip()
            if not sel:
                err_lbl.configure(text="Debe seleccionar un cliente.")
                return

            rif_sel = sel.split(" — ")[0]
            match = next((c for c in clientes_list if c["rif"] == rif_sel), None)
            if not match:
                err_lbl.configure(text="Cliente no válido.")
                return

            cliente_nombre = match["razon_social"]
            precinto = e_precinto.get().strip()

            ok = asignar_cliente_maquina(maquina_id, cliente_nombre, precinto)
            if ok:
                modal.destroy()
                self.cargar_datos()
            else:
                err_lbl.configure(text="Error al asignar cliente.")

        ctk.CTkButton(footer, text="💾 Fiscalizar / Asignar Cliente",
                      fg_color=col["principal"], text_color="#0A192F",
                      hover_color=col.get("principal_hover", "#00C8D4"),
                      width=260, height=40,
                      command=_guardar).pack(side="right", padx=20, pady=12)
