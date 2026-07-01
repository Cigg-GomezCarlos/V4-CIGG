"""
modulos/archivos/sub_roles.py
==============================
Submódulo de gestión de roles y permisos del sistema CIGG.

Patrón idéntico a sub_proveedores / sub_clientes / sub_usuarios:
  – Lista con cabecera fija + área scrollable
  – Botón ➕ Nuevo Rol abre modal
  – Cada rol muestra sus permisos configurables
  – Botones ✏️ editar y 🗑️ eliminar (bloqueados en rol admin)
"""

import customtkinter as ctk
from core.permisos import puede
from tkinter import messagebox

from core.database import (
    obtener_roles, obtener_permisos_rol,
    guardar_rol, eliminar_rol,
)

# ── Estructura de módulos y submódulos del sistema ────────────────────────────
# hoja=True  → módulo sin submódulos (ver + editar + eliminar)
# hoja=False → módulo padre (sólo ver; permisos reales en sus hijos)
ESTRUCTURA = [
    {
        "key": "Archivos", "label": "📁  Archivos", "hoja": False,
        "subs": [
            {"key": "Archivos.Usuarios",    "label": "👤 Usuarios"},
            {"key": "Archivos.Máquinas",    "label": "🖥 Máquinas"},
            {"key": "Archivos.Proveedores", "label": "📦 Proveedores"},
            {"key": "Archivos.Clientes",    "label": "🤝 Clientes"},
            {"key": "Archivos.Sistemas",    "label": "⚙️ Sistemas"},
            {"key": "Archivos.Roles",       "label": "🔐 Roles"},
        ],
    },
    {"key": "Ventas",     "label": "📊  Ventas",     "hoja": True, "subs": []},
    {"key": "Inventario", "label": "📦  Inventario", "hoja": True, "subs": []},
    {"key": "Monedas",    "label": "💱  Monedas",    "hoja": True, "subs": []},
    {"key": "Servicios",  "label": "🔧  Servicios",  "hoja": True, "subs": []},
    {"key": "Documentos", "label": "📄  Documentos", "hoja": True, "subs": []},
    {"key": "Informes",   "label": "📈  Informes",   "hoja": True, "subs": []},
]


class SubmoduloRoles(ctk.CTkFrame):
    """Panel de administración de roles del sistema CIGG."""

    def __init__(self, parent, estilos, permisos=None):
        super().__init__(parent, fg_color="transparent")
        self.estilos  = estilos
        self.permisos = permisos or {}
        self._puede_editar   = puede(self.permisos, "Archivos.Roles", "editar")
        self._puede_eliminar = puede(self.permisos, "Archivos.Roles", "eliminar")
        self.col = estilos["colores"]
        self.fnt = estilos["fuentes"]

        self.pack_propagate(False)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=0)
        self.rowconfigure(1, weight=0)
        self.rowconfigure(2, weight=1)

        self._construir_barra_superior()
        self._construir_cabecera()
        self._construir_lista()

    # ── Barra superior ────────────────────────────────────────────────────────

    def _construir_barra_superior(self):
        col, fnt = self.col, self.fnt
        barra = ctk.CTkFrame(self, fg_color="#020C1B", corner_radius=8)
        barra.grid(row=0, column=0, padx=10, pady=(10, 4), sticky="ew")
        barra.columnconfigure(1, weight=1)

        if self._puede_editar:
            ctk.CTkButton(
                barra, text="➕  Nuevo Rol",
                font=fnt["normal"], fg_color=col["principal"],
                hover_color=col["principal_hover"], text_color="#0A192F",
                height=34, corner_radius=6,
                command=self._abrir_modal_crear,
            ).grid(row=0, column=0, padx=(10, 6), pady=8)

        self.entry_buscar = ctk.CTkEntry(
            barra, placeholder_text="🔍  Buscar rol...",
            font=fnt["normal"], border_color=col["principal"], height=34,
        )
        self.entry_buscar.grid(row=0, column=1, padx=(0, 10), pady=8, sticky="ew")
        self.entry_buscar.bind("<KeyRelease>", lambda e: self._cargar_lista())

    # ── Cabecera fija ─────────────────────────────────────────────────────────

    def _construir_cabecera(self):
        col, fnt = self.col, self.fnt
        cab = ctk.CTkFrame(self, fg_color="#020C1B", corner_radius=6)
        cab.grid(row=1, column=0, padx=10, pady=(0, 2), sticky="ew")
        cab.columnconfigure(0, weight=3)
        cab.columnconfigure(1, weight=2)
        cab.columnconfigure(2, weight=1)

        def th(txt, c, anchor="w"):
            ctk.CTkLabel(
                cab, text=txt,
                font=(fnt["normal"][0], fnt["normal"][1], "bold"),
                text_color=col["principal"], anchor=anchor,
            ).grid(row=0, column=c, padx=10, pady=6, sticky="ew")

        th("Nombre del Rol", 0)
        th("Descripción",    1)
        th("Acciones",       2, "center")

    # ── Lista scrollable ──────────────────────────────────────────────────────

    def _construir_lista(self):
        self.scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent", corner_radius=0,
        )
        self.scroll.grid(row=2, column=0, padx=10, pady=(0, 10), sticky="nsew")
        self.scroll.columnconfigure(0, weight=3)
        self.scroll.columnconfigure(1, weight=2)
        self.scroll.columnconfigure(2, weight=1)
        self._cargar_lista()

    def _cargar_lista(self):
        col, fnt = self.col, self.fnt
        filtro = self.entry_buscar.get() if hasattr(self, "entry_buscar") else ""

        for w in self.scroll.winfo_children():
            w.destroy()

        roles = obtener_roles(filtro)
        if not roles:
            ctk.CTkLabel(
                self.scroll, text="No hay roles registrados.",
                font=fnt["normal"], text_color="#64748B",
            ).grid(row=0, column=0, columnspan=3, pady=30)
            return

        for i, rol in enumerate(roles):
            bg = "#0D1F35" if i % 2 == 0 else "#091525"
            fila = ctk.CTkFrame(self.scroll, fg_color=bg, corner_radius=4)
            fila.grid(row=i, column=0, columnspan=3, sticky="ew", pady=1)
            fila.columnconfigure(0, weight=3)
            fila.columnconfigure(1, weight=2)
            fila.columnconfigure(2, weight=1)

            nombre_txt = ("🔒 " if rol["es_admin"] else "") + rol["nombre"]
            ctk.CTkLabel(
                fila, text=nombre_txt,
                font=fnt["normal"], text_color=col["texto_claro"], anchor="w",
            ).grid(row=0, column=0, padx=10, pady=8, sticky="ew")

            desc = rol["descripcion"] or "—"
            if len(desc) > 45:
                desc = desc[:42] + "..."
            ctk.CTkLabel(
                fila, text=desc,
                font=fnt["normal"], text_color="#94A3B8", anchor="w",
            ).grid(row=0, column=1, padx=10, pady=8, sticky="ew")

            acc = ctk.CTkFrame(fila, fg_color="transparent")
            acc.grid(row=0, column=2, padx=8, pady=4, sticky="e")

            if rol["es_admin"]:
                ctk.CTkLabel(acc, text="🔒",
                             font=(fnt["normal"][0], 16),
                             text_color="#64748B").pack(side="left", padx=4)
            else:
                if self._puede_editar:
                    ctk.CTkButton(
                        acc, text="✏️", width=34, height=28,
                        fg_color="#1E3A5F", hover_color="#2A5080",
                        font=fnt["normal"],
                        command=lambda r=rol: self._abrir_modal_editar(r),
                    ).pack(side="left", padx=(0, 4))
                if self._puede_eliminar:
                    ctk.CTkButton(
                        acc, text="🗑️", width=34, height=28,
                        fg_color="#3B1A1A", hover_color="#DC2626",
                        font=fnt["normal"],
                        command=lambda r=rol: self._confirmar_eliminar(r),
                    ).pack(side="left")

    # ── Modal ─────────────────────────────────────────────────────────────────

    def _abrir_modal_crear(self):
        self._modal(None)

    def _abrir_modal_editar(self, rol):
        self._modal(rol)

    def _modal(self, rol):
        col, fnt = self.col, self.fnt
        editando = rol is not None
        permisos_actuales = obtener_permisos_rol(rol["id"]) if editando else {}

        win = ctk.CTkToplevel(self)
        win.title("Editar Rol" if editando else "Nuevo Rol")
        win.geometry("640x630")
        win.resizable(False, False)
        win.grab_set()
        win.configure(fg_color="#020C1B")

        ctk.CTkLabel(
            win, text="Editar Rol" if editando else "Nuevo Rol",
            font=fnt["subtitulo"], text_color=col["principal"],
        ).pack(pady=(16, 6), padx=24)

        # Campos básicos
        campos = ctk.CTkFrame(win, fg_color="transparent")
        campos.pack(fill="x", padx=24, pady=4)
        campos.columnconfigure(1, weight=1)

        def campo(lbl, row):
            ctk.CTkLabel(
                campos, text=lbl, font=fnt["normal"],
                text_color="#94A3B8", anchor="e",
            ).grid(row=row, column=0, padx=(0, 8), pady=5, sticky="e")
            e = ctk.CTkEntry(campos, font=fnt["normal"],
                             border_color=col["principal"])
            e.grid(row=row, column=1, pady=5, sticky="ew")
            return e

        e_nombre = campo("Nombre:", 0)
        e_desc   = campo("Descripción:", 1)

        if editando:
            e_nombre.insert(0, rol["nombre"])
            e_desc.insert(0, rol["descripcion"] or "")

        # Separador
        ctk.CTkFrame(win, height=1, fg_color="#1E3A5F").pack(
            fill="x", padx=24, pady=(8, 0))
        ctk.CTkLabel(
            win, text="Permisos por Módulo / Submódulo",
            font=(fnt["normal"][0], fnt["normal"][1], "bold"),
            text_color=col["principal"],
        ).pack(anchor="w", padx=24, pady=(6, 2))

        # Cabecera tabla
        hdr = ctk.CTkFrame(win, fg_color="#0D1F35", corner_radius=4)
        hdr.pack(fill="x", padx=24, pady=(0, 2))
        hdr.columnconfigure(0, weight=1)
        ctk.CTkLabel(
            hdr, text="Módulo / Submódulo",
            font=(fnt["normal"][0], fnt["normal"][1], "bold"),
            text_color=col["principal"], anchor="w",
        ).grid(row=0, column=0, padx=10, pady=4, sticky="w")
        for ci, txt in enumerate(["Ver", "Editar", "Eliminar"], start=1):
            hdr.columnconfigure(ci, minsize=80)
            ctk.CTkLabel(
                hdr, text=txt,
                font=(fnt["normal"][0], fnt["normal"][1], "bold"),
                text_color=col["principal"], width=80, anchor="center",
            ).grid(row=0, column=ci, pady=4)

        # Tabla scrollable
        tabla = ctk.CTkScrollableFrame(win, fg_color="transparent", height=290)
        tabla.pack(fill="x", padx=24, pady=(0, 4))
        tabla.columnconfigure(0, weight=1)
        for ci in range(1, 4):
            tabla.columnconfigure(ci, minsize=80)

        vars_p = {}  # {clave: {"ver": BoolVar, "editar": BoolVar, "eliminar": BoolVar}}

        def check(parent, var, col_n, row_n):
            ctk.CTkCheckBox(
                parent, text="", variable=var, width=80,
                checkbox_width=18, checkbox_height=18,
                fg_color=col["principal"], hover_color=col["principal_hover"],
            ).grid(row=row_n, column=col_n, pady=4)

        fi = 0
        for mod in ESTRUCTURA:
            bg = "#091525" if fi % 2 == 0 else "#0D1F35"
            fm = ctk.CTkFrame(tabla, fg_color=bg, corner_radius=3)
            fm.grid(row=fi, column=0, columnspan=4, sticky="ew", pady=1)
            fm.columnconfigure(0, weight=1)
            for ci in range(1, 4):
                fm.columnconfigure(ci, minsize=80)

            ctk.CTkLabel(
                fm, text=mod["label"],
                font=(fnt["normal"][0], fnt["normal"][1], "bold"),
                text_color=col["texto_claro"], anchor="w",
            ).grid(row=0, column=0, padx=10, pady=5, sticky="w")

            p = permisos_actuales.get(mod["key"], {})
            vv = ctk.BooleanVar(value=bool(p.get("ver", 0)))
            ve = ctk.BooleanVar(value=bool(p.get("editar", 0)))
            vl = ctk.BooleanVar(value=bool(p.get("eliminar", 0)))
            vars_p[mod["key"]] = {"ver": vv, "editar": ve, "eliminar": vl}

            check(fm, vv, 1, 0)
            if mod["hoja"]:
                check(fm, ve, 2, 0)
                check(fm, vl, 3, 0)
            else:
                for ci in (2, 3):
                    ctk.CTkLabel(fm, text="—", width=80,
                                 text_color="#334155",
                                 anchor="center").grid(row=0, column=ci, pady=5)
            fi += 1

            for sub in mod["subs"]:
                bg2 = "#091525" if fi % 2 == 0 else "#0D1F35"
                fs = ctk.CTkFrame(tabla, fg_color=bg2, corner_radius=3)
                fs.grid(row=fi, column=0, columnspan=4, sticky="ew", pady=1)
                fs.columnconfigure(0, weight=1)
                for ci in range(1, 4):
                    fs.columnconfigure(ci, minsize=80)

                ctk.CTkLabel(
                    fs, text="    " + sub["label"],
                    font=fnt["normal"], text_color="#94A3B8", anchor="w",
                ).grid(row=0, column=0, padx=10, pady=4, sticky="w")

                ps = permisos_actuales.get(sub["key"], {})
                sv  = ctk.BooleanVar(value=bool(ps.get("ver", 0)))
                se  = ctk.BooleanVar(value=bool(ps.get("editar", 0)))
                sel = ctk.BooleanVar(value=bool(ps.get("eliminar", 0)))
                vars_p[sub["key"]] = {"ver": sv, "editar": se, "eliminar": sel}

                for ci, var in enumerate([sv, se, sel], start=1):
                    check(fs, var, ci, 0)
                fi += 1

        # Error + botones
        lbl_err = ctk.CTkLabel(win, text="", font=fnt["normal"],
                               text_color=col["error"])
        lbl_err.pack(pady=(4, 0))

        btns = ctk.CTkFrame(win, fg_color="transparent")
        btns.pack(pady=(4, 16))

        def guardar():
            nombre = e_nombre.get().strip()
            desc   = e_desc.get().strip()
            if not nombre:
                lbl_err.configure(text="El nombre del rol es obligatorio.")
                return
            permisos = {
                clave: {
                    "ver":      int(vs["ver"].get()),
                    "editar":   int(vs["editar"].get()),
                    "eliminar": int(vs["eliminar"].get()),
                }
                for clave, vs in vars_p.items()
            }
            err = guardar_rol(nombre, desc, permisos,
                              rol_id=rol["id"] if editando else None)
            if err:
                lbl_err.configure(text=err)
                return
            win.destroy()
            self._cargar_lista()

        ctk.CTkButton(
            btns, text="Cancelar", font=fnt["normal"],
            fg_color="#1E293B", hover_color="#334155",
            width=110, height=34, command=win.destroy,
        ).pack(side="left", padx=6)

        ctk.CTkButton(
            btns, text="💾  Guardar", font=fnt["normal"],
            fg_color=col["principal"], hover_color=col["principal_hover"],
            text_color="#0A192F",
            width=110, height=34, command=guardar,
        ).pack(side="left", padx=6)

    # ── Eliminar ──────────────────────────────────────────────────────────────

    def _confirmar_eliminar(self, rol):
        ok = messagebox.askyesno(
            "Eliminar Rol",
            f"¿Eliminar el rol «{rol['nombre']}»?\n"
            "Se quitará de todos los usuarios que lo tengan asignado.",
            parent=self,
        )
        if ok:
            eliminar_rol(rol["id"])
            self._cargar_lista()
