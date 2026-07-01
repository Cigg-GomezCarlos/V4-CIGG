"""
modulos/archivos/sub_proveedores.py
====================================
Submódulo de gestión de proveedores.

Características:
  - Lista con búsqueda reactiva (nombre / RIF)
  - Formulario modal para crear y editar
  - Todo el CRUD se delega a core.database (sin duplicar lógica)
  - Diseño 100 % pack (sin mezcla con grid)
"""

import customtkinter as ctk
from core.permisos import puede
from tkinter import messagebox

from core.database import (
    obtener_proveedores,
    obtener_tablas_auxiliares,
    guardar_proveedor,
    eliminar_proveedor,
)


class SubmoduloProveedores(ctk.CTkFrame):
    """Panel principal del submódulo Proveedores."""

    def __init__(self, parent, estilos, permisos=None):
        super().__init__(parent, fg_color="transparent")
        self.estilos         = estilos
        self.col             = estilos["colores"]
        self.fuente          = estilos["fuentes"]["normal"]
        self.permisos        = permisos or {}
        self._puede_editar   = puede(self.permisos, "Archivos.Proveedores", "editar")
        self._puede_eliminar = puede(self.permisos, "Archivos.Proveedores", "eliminar")
        self._construir_ui()
        self.cargar_datos()

    # ─── UI ──────────────────────────────────────────────────────────────────

    def _construir_ui(self):
        col = self.col

        # ── Barra superior ───────────────────────────────────────────────────
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=10, pady=(8, 4))

        ctk.CTkLabel(
            top, text="📦  GESTIÓN DE PROVEEDORES",
            font=self.estilos["fuentes"]["subtitulo"],
            text_color=col["texto_oscuro"],
        ).pack(side="left")

        if self._puede_editar:
            ctk.CTkButton(
                top, text="➕ Nuevo Proveedor",
                font=self.fuente,
                fg_color=col["principal"],
                hover_color=col["principal_hover"],
                text_color="#0A192F", height=34,
                command=lambda: self._abrir_modal(),
            ).pack(side="right")

        # ── Barra de búsqueda + filtro por tipo ──────────────────────────────
        barra = ctk.CTkFrame(self, fg_color="transparent")
        barra.pack(fill="x", padx=10, pady=(0, 6))

        self.entry_buscar = ctk.CTkEntry(
            barra, placeholder_text="🔍 Buscar por razón social o RIF…",
            font=self.fuente, height=32,
        )
        self.entry_buscar.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.entry_buscar.bind("<KeyRelease>", lambda e: self._aplicar_filtros())

        # Obtener tipos disponibles de la BD
        try:
            from core.database import obtener_tablas_auxiliares
            _, _, dic_t = obtener_tablas_auxiliares()
            tipos_disponibles = ["Todos"] + list(dic_t.keys())
        except Exception:
            tipos_disponibles = ["Todos"]

        self.cmb_tipo = ctk.CTkComboBox(
            barra, values=tipos_disponibles,
            font=self.fuente, height=32, width=180,
            dropdown_fg_color="#1A3550",
            command=lambda _: self._aplicar_filtros(),
        )
        self.cmb_tipo.set("Todos")
        self.cmb_tipo.pack(side="left")

        # ── Cabecera de columnas ─────────────────────────────────────────────
        cab = ctk.CTkFrame(self, fg_color="#0D2137", corner_radius=6, height=30)
        cab.pack(fill="x", padx=10, pady=(0, 2))
        cab.pack_propagate(False)

        for txt, w in [("Razón Social", 280), ("RIF", 150),
                       ("Contribuyente", 130), ("% Ret.", 80),
                       ("Tipo", 140), ("Acciones", 90)]:
            ctk.CTkLabel(
                cab, text=txt, width=w, anchor="w",
                font=(self.fuente[0], self.fuente[1], "bold"),
                text_color=col["principal"],
            ).pack(side="left", padx=6, pady=4)

        # ── Área scrollable con filas ─────────────────────────────────────────
        self.scroll = ctk.CTkScrollableFrame(
            self, fg_color="#0A192F", corner_radius=8)
        self.scroll.pack(fill="both", expand=True, padx=10, pady=(0, 8))

    # ─── Helpers de filtro ────────────────────────────────────────────────────

    def _aplicar_filtros(self):
        texto = self.entry_buscar.get()
        tipo  = self.cmb_tipo.get()
        self.cargar_datos(filtro=texto, tipo="" if tipo == "Todos" else tipo)

    # ─── Carga de datos ───────────────────────────────────────────────────────

    def cargar_datos(self, filtro: str = "", tipo: str = ""):
        for w in self.scroll.winfo_children():
            w.destroy()

        try:
            proveedores = obtener_proveedores(filtro, tipo)
        except Exception as exc:
            messagebox.showerror("Error", f"No se pudieron cargar proveedores:\n{exc}")
            return

        if not proveedores:
            ctk.CTkLabel(
                self.scroll,
                text="Sin proveedores registrados." if not filtro
                     else "Sin resultados para la búsqueda.",
                font=self.fuente,
                text_color="#4A6FA5",
            ).pack(pady=30)
            return

        col = self.col
        for i, p in enumerate(proveedores):
            bg = col["tarjetas"] if i % 2 == 0 else "#0D2137"
            fila = ctk.CTkFrame(self.scroll, fg_color=bg,
                                corner_radius=4, height=34)
            fila.pack(fill="x", pady=2, padx=4)
            fila.pack_propagate(False)

            datos_col = [
                (p["razon_social"],          280, col["texto_oscuro"]),
                (p["rif"],                   150, "#8892B0"),
                (p["tipo_contribuyente"],    130, "#6B8BAE"),
                (p["porcentaje_retencion"],   80, col["principal"]),
                (p["tipo_proveedor"],        140, "#6B8BAE"),
            ]
            for texto, ancho, color in datos_col:
                ctk.CTkLabel(
                    fila, text=texto, width=ancho, anchor="w",
                    font=self.fuente, text_color=color,
                ).pack(side="left", padx=6, pady=4)

            # Botones de acción
            acc = ctk.CTkFrame(fila, fg_color="transparent")
            acc.pack(side="left", padx=4)

            if self._puede_editar:
                ctk.CTkButton(
                    acc, text="✏️", width=32, height=26,
                    fg_color="#1A3550", hover_color="#2A4560",
                    text_color=col["texto_oscuro"],
                    command=lambda p=p: self._abrir_modal(p),
                ).pack(side="left", padx=2)
            if self._puede_eliminar:
                ctk.CTkButton(
                    acc, text="🗑️", width=32, height=26,
                    fg_color="#2A1A1A", hover_color="#3A1A1A",
                    text_color=col["error"],
                    command=lambda pid=p["id"]: self._eliminar(pid),
                ).pack(side="left", padx=2)

    # ─── Modal de creación / edición ──────────────────────────────────────────

    def _abrir_modal(self, proveedor=None):
        col   = self.col
        font  = self.fuente
        titulo = "Editar Proveedor" if proveedor else "Nuevo Proveedor"

        modal = ctk.CTkToplevel(self)
        modal.title(titulo)
        modal.geometry("480x620")
        modal.configure(fg_color="#0A192F")
        modal.resizable(False, False)
        modal.transient(self)
        modal.grab_set()
        modal.lift()

        ctk.CTkLabel(
            modal, text=f"{'✏️' if proveedor else '➕'}  {titulo.upper()}",
            font=self.estilos["fuentes"]["subtitulo"],
            text_color=col["principal"],
        ).pack(pady=(20, 8))

        # ── Formulario en ScrollableFrame ─────────────────────────────────────
        form = ctk.CTkScrollableFrame(modal, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=20, pady=(0, 8))

        def campo(label, valor=""):
            ctk.CTkLabel(form, text=label, font=font,
                         text_color="#8892B0").pack(anchor="w", pady=(6, 1))
            e = ctk.CTkEntry(form, font=font, fg_color="#1A3550",
                             border_color="#4A6FA5", height=30)
            e.insert(0, valor)
            e.pack(fill="x", pady=(0, 4))
            return e

        def combo(label, opciones, valor_actual=""):
            ctk.CTkLabel(form, text=label, font=font,
                         text_color="#8892B0").pack(anchor="w", pady=(6, 1))
            c = ctk.CTkComboBox(form, values=opciones, height=30,
                                dropdown_fg_color="#1A3550", font=font)
            c.set(valor_actual if valor_actual in opciones else opciones[0])
            c.pack(fill="x", pady=(0, 4))
            return c

        ent_social = campo("Razón Social *",
                           proveedor["razon_social"] if proveedor else "")
        ent_rif    = campo("RIF (Ej: J-12345678-0) *",
                           proveedor["rif"] if proveedor else "")
        ent_dir    = campo("Dirección Fiscal *",
                           proveedor["direccion"] if proveedor else "")
        ent_tel    = campo("Teléfono",
                           proveedor["telefono"] if proveedor else "")
        ent_mail   = campo("Correo",
                           proveedor["correo"] if proveedor else "")

        dic_c, dic_r, dic_t = obtener_tablas_auxiliares()

        cmb_contrib = combo("Tipo de Contribuyente *",
                            list(dic_c.keys()),
                            proveedor["tipo_contribuyente"] if proveedor else "Ordinario")
        cmb_ret     = combo("% Retención *",
                            list(dic_r.keys()),
                            proveedor["porcentaje_retencion"] if proveedor else "0%")
        cmb_tipo    = combo("Tipo de Proveedor *",
                            list(dic_t.keys()),
                            proveedor["tipo_proveedor"] if proveedor else "Otros")

        # ── Botón guardar (fuera del scroll) ──────────────────────────────────
        def _guardar():
            razon   = ent_social.get().strip()
            rif     = ent_rif.get().strip().upper()
            direccion = ent_dir.get().strip()

            if not razon or not rif or not direccion:
                messagebox.showerror("Error",
                                     "Razón Social, RIF y Dirección son obligatorios.",
                                     parent=modal)
                return

            datos = (
                razon, rif, direccion,
                dic_c[cmb_contrib.get()],
                dic_r[cmb_ret.get()],
                ent_tel.get().strip(),
                ent_mail.get().strip(),
                dic_t[cmb_tipo.get()],
            )
            try:
                guardar_proveedor(datos, proveedor["id"] if proveedor else None)
                modal.destroy()
                self._aplicar_filtros()
            except Exception as exc:
                messagebox.showerror("Error BD", str(exc), parent=modal)

        ctk.CTkButton(
            modal, text="💾 Guardar",
            font=font, height=38,
            fg_color=col["principal"],
            hover_color=col["principal_hover"],
            text_color="#0A192F",
            command=_guardar,
        ).pack(fill="x", padx=20, pady=12)

    # ─── Eliminar ─────────────────────────────────────────────────────────────

    def _eliminar(self, prov_id: int):
        if messagebox.askyesno("Confirmar",
                               "¿Eliminar este proveedor definitivamente?"):
            try:
                eliminar_proveedor(prov_id)
                self._aplicar_filtros()
            except Exception as exc:
                messagebox.showerror("Error", str(exc))
