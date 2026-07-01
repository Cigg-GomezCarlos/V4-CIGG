"""
modulos/archivos/sub_clientes.py
=================================
Submódulo de Cartera de Clientes.
Permite crear, editar y eliminar clientes corporativos.
Campos: RIF, Razón Social, Dirección Fiscal, Correo,
        Teléfono, Tipo de Contribuyente.

Patrón: idéntico a sub_proveedores.py
  - Lista scrollable con cabecera fija
  - Modal (CTkToplevel) para crear / editar
  - Layout 100 % pack (sin mezcla con grid)
"""

import customtkinter as ctk
from core.permisos import puede
from tkinter import messagebox

from core.database import obtener_clientes, guardar_cliente, eliminar_cliente


class SubmoduloClientes(ctk.CTkFrame):
    """Panel principal del submódulo Clientes."""

    def __init__(self, parent, estilos, permisos=None):
        super().__init__(parent, fg_color="transparent")
        self.estilos  = estilos
        self.permisos = permisos or {}
        self._puede_editar   = puede(self.permisos, "Archivos.Clientes", "editar")
        self._puede_eliminar = puede(self.permisos, "Archivos.Clientes", "eliminar")
        self.col     = estilos["colores"]
        self.fuente  = estilos["fuentes"]["normal"]
        self._construir_ui()
        self.cargar_datos()

    # ─── UI ──────────────────────────────────────────────────────────────────

    def _construir_ui(self):
        col = self.col

        # ── Barra superior ───────────────────────────────────────────────────
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=10, pady=(8, 4))

        ctk.CTkLabel(
            top, text="🤝  CARTERA DE CLIENTES",
            font=self.estilos["fuentes"]["subtitulo"],
            text_color=col["texto_oscuro"],
        ).pack(side="left")

        if self._puede_editar:
            ctk.CTkButton(
                top, text="➕ Nuevo Cliente",
                font=self.fuente,
                fg_color=col["principal"],
                hover_color=col["principal_hover"],
                text_color="#0A192F", height=34,
                command=lambda: self._abrir_modal(),
            ).pack(side="right")

        # ── Buscador ─────────────────────────────────────────────────────────
        self.entry_buscar = ctk.CTkEntry(
            self, placeholder_text="🔍 Buscar por razón social o RIF…",
            font=self.fuente, height=32,
        )
        self.entry_buscar.pack(fill="x", padx=10, pady=(0, 6))
        self.entry_buscar.bind(
            "<KeyRelease>",
            lambda e: self.cargar_datos(self.entry_buscar.get())
        )

        # ── Cabecera de columnas ─────────────────────────────────────────────
        cab = ctk.CTkFrame(self, fg_color="#0D2137", corner_radius=6, height=30)
        cab.pack(fill="x", padx=10, pady=(0, 2))
        cab.pack_propagate(False)

        for txt, w in [
            ("Razón Social",      280),
            ("RIF",               150),
            ("Contribuyente",     130),
            ("Teléfono",          120),
            ("Correo",            180),
            ("Acciones",           90),
        ]:
            ctk.CTkLabel(
                cab, text=txt, width=w, anchor="w",
                font=(self.fuente[0], self.fuente[1], "bold"),
                text_color=col["principal"],
            ).pack(side="left", padx=6, pady=4)

        # ── Área scrollable con filas ─────────────────────────────────────────
        self.scroll = ctk.CTkScrollableFrame(
            self, fg_color="#0A192F", corner_radius=8)
        self.scroll.pack(fill="both", expand=True, padx=10, pady=(0, 8))

    # ─── Carga de datos ───────────────────────────────────────────────────────

    def cargar_datos(self, filtro: str = ""):
        for w in self.scroll.winfo_children():
            w.destroy()

        try:
            clientes = obtener_clientes(filtro)
        except Exception as exc:
            messagebox.showerror("Error", f"No se pudieron cargar clientes:\n{exc}")
            return

        if not clientes:
            ctk.CTkLabel(
                self.scroll,
                text="Sin clientes registrados." if not filtro
                     else "Sin resultados para la búsqueda.",
                font=self.fuente,
                text_color="#4A6FA5",
            ).pack(pady=30)
            return

        col = self.col
        for i, c in enumerate(clientes):
            bg = col["tarjetas"] if i % 2 == 0 else "#0D2137"
            fila = ctk.CTkFrame(self.scroll, fg_color=bg,
                                corner_radius=4, height=34)
            fila.pack(fill="x", pady=2, padx=4)
            fila.pack_propagate(False)

            icono = "⭐" if c["tipo_contribuyente"] == "Especial" else "👤"

            datos_col = [
                (c["razon_social"],                      280, col["texto_oscuro"]),
                (c["rif"],                               150, "#8892B0"),
                (f"{icono} {c['tipo_contribuyente']}",   130, "#6B8BAE"),
                (c["telefono"],                          120, "#8892B0"),
                (c["correo"],                            180, "#6B8BAE"),
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
                    command=lambda c=c: self._abrir_modal(c),
                ).pack(side="left", padx=2)
            if self._puede_eliminar:
                ctk.CTkButton(
                    acc, text="🗑️", width=32, height=26,
                    fg_color="#2A1A1A", hover_color="#3A1A1A",
                    text_color=col["error"],
                    command=lambda cid=c["id"], nom=c["razon_social"]: self._eliminar(cid, nom),
                ).pack(side="left", padx=2)

    # ─── Modal de creación / edición ──────────────────────────────────────────

    def _abrir_modal(self, cliente=None):
        col   = self.col
        font  = self.fuente
        titulo = "Editar Cliente" if cliente else "Nuevo Cliente"

        modal = ctk.CTkToplevel(self)
        modal.title(titulo)
        modal.geometry("480x560")
        modal.configure(fg_color="#0A192F")
        modal.resizable(False, False)
        modal.transient(self)
        modal.grab_set()
        modal.lift()

        ctk.CTkLabel(
            modal,
            text=f"{'✏️' if cliente else '➕'}  {titulo.upper()}",
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

        ent_razon  = campo("Razón Social *",
                           cliente["razon_social"] if cliente else "")
        ent_rif    = campo("RIF (Ej: J-12345678-0) *",
                           cliente["rif"] if cliente else "")
        ent_dir    = campo("Dirección Fiscal",
                           cliente["direccion"] if cliente else "")
        ent_tel    = campo("Teléfono",
                           cliente["telefono"] if cliente else "")
        ent_mail   = campo("Correo",
                           cliente["correo"] if cliente else "")

        # Tipo de Contribuyente
        ctk.CTkLabel(form, text="Tipo de Contribuyente *", font=font,
                     text_color="#8892B0").pack(anchor="w", pady=(6, 1))
        opciones_tipo = ["Ordinario", "Especial"]
        cmb_tipo = ctk.CTkComboBox(
            form, values=opciones_tipo, height=30,
            dropdown_fg_color="#1A3550", font=font,
        )
        valor_tipo = cliente["tipo_contribuyente"] if cliente else "Ordinario"
        cmb_tipo.set(valor_tipo if valor_tipo in opciones_tipo else "Ordinario")
        cmb_tipo.pack(fill="x", pady=(0, 4))

        # ── Botón Guardar ─────────────────────────────────────────────────────
        def _guardar():
            razon = ent_razon.get().strip()
            rif   = ent_rif.get().strip().upper()

            if not razon or not rif:
                messagebox.showerror(
                    "Error", "Razón Social y RIF son obligatorios.",
                    parent=modal,
                )
                return

            datos = (
                rif,
                razon,
                ent_dir.get().strip(),
                ent_mail.get().strip(),
                cmb_tipo.get(),
                ent_tel.get().strip(),
            )
            try:
                guardar_cliente(datos, cliente["id"] if cliente else None)
                modal.destroy()
                self.cargar_datos(self.entry_buscar.get())
            except Exception as exc:
                if "UNIQUE" in str(exc):
                    messagebox.showerror(
                        "RIF duplicado",
                        f"Ya existe un cliente con el RIF «{rif}».",
                        parent=modal,
                    )
                else:
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

    def _eliminar(self, cliente_id: int, nombre: str):
        if messagebox.askyesno(
            "Confirmar",
            f"¿Eliminar al cliente «{nombre}» definitivamente?",
        ):
            try:
                eliminar_cliente(cliente_id)
                self.cargar_datos(self.entry_buscar.get())
            except Exception as exc:
                messagebox.showerror("Error", str(exc))
