"""
modulos/ventas/sub_metodos_pago.py
==================================
Submódulo Métodos de Pago — lista + modal de creación/edición.

Aquí se dan de alta los métodos de pago que aceptará el sistema,
indicando en qué moneda opera cada uno.
Patrón: barra + lista scrollable + modal (igual que los demás submódulos).
"""
import customtkinter as ctk
from tkinter import messagebox


# Monedas soportadas por el sistema (código → etiqueta visible)
MONEDAS = [
    ("USD",      "USD  $  (Dólar)"),
    ("EUR",      "EUR  €  (Euro)"),
    ("VES",      "VES  Bs  (Bolívar)"),
    ("USDT",     "USDT ₮  (Tether)"),
    ("TASA_EXT", "Tasa Externa"),
]
_MON_LABEL = {c: l for c, l in MONEDAS}
_MON_FROM_LABEL = {l: c for c, l in MONEDAS}
_MON_SIMBOLO = {"USD": "$", "EUR": "€", "VES": "Bs", "USDT": "₮", "TASA_EXT": "≈"}


class SubmoduloMetodosPago(ctk.CTkFrame):
    """Submódulo de Métodos de Pago — lista + modal de creación/edición."""

    COLS   = ["Método", "Moneda", "Estado", "Observaciones", ""]
    WIDTHS = [240, 150, 110, 300, 76]

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

        ctk.CTkLabel(bar, text="💳  Métodos de Pago",
                     font=fnt["titulo"],
                     text_color=col["principal"]).pack(side="left", padx=16, pady=8)

        ctk.CTkButton(bar, text="➕ Nuevo Método",
                      fg_color=col["principal"], text_color="#0A192F",
                      hover_color=col.get("principal_hover", "#00C8D4"),
                      width=160, height=34,
                      command=self._abrir_modal).pack(side="right", padx=12, pady=8)

        self.filtro_moneda = ctk.StringVar(value="Todas")
        ctk.CTkOptionMenu(bar, variable=self.filtro_moneda,
                          values=["Todas"] + [c for c, _ in MONEDAS],
                          width=120, height=32,
                          fg_color=col["tarjetas"],
                          button_color=col["tarjetas"],
                          command=lambda *_: self.cargar_datos()
                          ).pack(side="right", padx=4, pady=10)

        self.busq_var = ctk.StringVar()
        ctk.CTkEntry(bar, textvariable=self.busq_var, width=220, height=32,
                     placeholder_text="🔍 Buscar por nombre…"
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

        self.busq_var.trace_add("write", lambda *_: self.cargar_datos())

    # ─── Datos ───────────────────────────────────────────────────────────────

    def cargar_datos(self, *_):
        from core.database import listar_metodos_pago
        col = self.col
        fnt = self.fnt

        for w in self.scroll.winfo_children():
            w.destroy()

        mon = self.filtro_moneda.get()
        mon = "" if mon == "Todas" else mon
        try:
            rows = listar_metodos_pago(self.busq_var.get(), mon)
        except Exception as e:
            ctk.CTkLabel(self.scroll, text=f"Error al cargar: {e}",
                         text_color="#E63946", font=fnt["normal"]).pack(pady=20)
            return

        if not rows:
            ctk.CTkLabel(self.scroll,
                         text="Sin métodos de pago registrados.\nUsa «➕ Nuevo Método» para agregar uno.",
                         text_color="#4A6FA5", font=fnt["normal"],
                         justify="center").pack(pady=30)
            return

        for i, r in enumerate(rows):
            bg = col["tarjetas"] if i % 2 == 0 else col["fondo_oscuro"]
            fila = ctk.CTkFrame(self.scroll, corner_radius=0, fg_color=bg, height=34)
            fila.pack(fill="x")
            fila.pack_propagate(False)

            simbolo = _MON_SIMBOLO.get(r["moneda"], "")
            mon_txt = f'{r["moneda"]}  {simbolo}'
            activo  = r["activo"]
            est_txt = "✅ Activo" if activo else "🚫 Inactivo"
            est_col = col["principal"] if activo else "#E63946"

            vals = [
                (r["nombre"],              col["texto_claro"]),
                (mon_txt,                  col["principal"]),
                (est_txt,                  est_col),
                (r.get("observaciones", "") or "—", "#8FA9C8"),
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
                          command=lambda rr=r: self._abrir_modal(rr)
                          ).pack(side="right", padx=2)

    # ─── Acciones ─────────────────────────────────────────────────────────────

    def _eliminar(self, rid):
        from core.database import eliminar_metodo_pago
        if messagebox.askyesno("Eliminar", "¿Eliminar este método de pago?"):
            eliminar_metodo_pago(rid)
            self.cargar_datos()

    # ─── MODAL ────────────────────────────────────────────────────────────────

    def _abrir_modal(self, row=None):
        from core.database import guardar_metodo_pago
        col = self.col
        fnt = self.fnt
        editar = row is not None

        win = ctk.CTkToplevel(self)
        win.title("Editar Método de Pago" if editar else "Nuevo Método de Pago")
        win.geometry("460x520")
        win.configure(fg_color=col["fondo_oscuro"])
        win.transient(self.winfo_toplevel())
        win.grab_set()

        ctk.CTkLabel(win,
                     text="✏️  Editar Método" if editar else "➕  Nuevo Método",
                     font=fnt["subtitulo"],
                     text_color=col["principal"]).pack(pady=(18, 10))

        body = ctk.CTkScrollableFrame(win, corner_radius=0,
                                      fg_color=col["fondo_oscuro"])
        body.pack(fill="both", expand=True, padx=20, pady=(0, 4))

        def _campo(lbl):
            ctk.CTkLabel(body, text=lbl, anchor="w", font=fnt["normal"],
                         text_color=col["texto_claro"]).pack(fill="x", pady=(10, 2))

        # Nombre del método
        _campo("Nombre del método *")
        e_nombre = ctk.CTkEntry(body, height=34,
                                placeholder_text="Ej: Transferencia Banesco, Zelle, Efectivo…")
        e_nombre.pack(fill="x")

        # Moneda
        _campo("Moneda del método *")
        moneda_var = ctk.StringVar(
            value=_MON_LABEL.get(row["moneda"], MONEDAS[0][1]) if editar else MONEDAS[0][1])
        ctk.CTkOptionMenu(body, variable=moneda_var,
                          values=[l for _, l in MONEDAS],
                          height=34,
                          fg_color=col["tarjetas"],
                          button_color=col["tarjetas"]).pack(fill="x")

        # Observaciones
        _campo("Observaciones")
        e_obs = ctk.CTkTextbox(body, height=90,
                               fg_color=col["tarjetas"], corner_radius=6)
        e_obs.pack(fill="x")

        # Activo
        activo_var = ctk.BooleanVar(value=bool(row["activo"]) if editar else True)
        ctk.CTkSwitch(body, text="Método activo (disponible para cobros)",
                      variable=activo_var, font=fnt["normal"],
                      progress_color=col["principal"]).pack(fill="x", pady=(14, 4))

        if editar:
            e_nombre.insert(0, row["nombre"])
            e_obs.insert("1.0", row.get("observaciones", "") or "")

        # Footer fijo con Guardar siempre visible
        footer = ctk.CTkFrame(win, height=58, corner_radius=0, fg_color="#020C1B")
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)

        def _guardar():
            nombre = e_nombre.get().strip()
            if not nombre:
                messagebox.showwarning("Falta información",
                                       "Indica el nombre del método.", parent=win)
                return
            moneda = _MON_FROM_LABEL.get(moneda_var.get(), "USD")
            obs    = e_obs.get("1.0", "end").strip()
            activo = 1 if activo_var.get() else 0
            datos = (nombre, moneda, activo, obs)
            try:
                if editar:
                    guardar_metodo_pago(datos, row["id"])
                else:
                    guardar_metodo_pago(datos)
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo guardar:\n{e}", parent=win)
                return
            win.destroy()
            self.cargar_datos()

        ctk.CTkButton(footer, text="Cancelar", width=120, height=36,
                      fg_color="#1A3550", hover_color="#24476B",
                      text_color=col["texto_claro"],
                      command=win.destroy).pack(side="right", padx=(6, 16), pady=11)
        ctk.CTkButton(footer, text="💾 Guardar", width=150, height=36,
                      fg_color=col["principal"], text_color="#0A192F",
                      hover_color=col.get("principal_hover", "#00C8D4"),
                      command=_guardar).pack(side="right", padx=6, pady=11)
