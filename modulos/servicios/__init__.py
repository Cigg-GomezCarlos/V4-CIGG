"""
modulos/servicios/__init__.py
=============================
Módulo Servicios — orquestador de submódulos.

Submódulos:
    • Fiscalizar        → SubmoduloFiscalizar
    • Entrada en Servicio → SubmoduloEntradaServicio (placeholder)
    • Lista de Equipos  → SubmoduloListaEquipos (placeholder)
"""
import customtkinter as ctk

from .sub_fiscalizar import SubmoduloFiscalizar


class ModuloServicios(ctk.CTkFrame):
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
            ("Servicios.Fiscalizar",       "🔍 Fiscalizar",        SubmoduloFiscalizar),
            ("Servicios.EntradaServicio",  "🔧 Entrada en Servicio", self._placeholder("Entrada en Servicio")),
            ("Servicios.ListaEquipos",     "📋 Lista de Equipos",   self._placeholder("Lista de Equipos")),
        ]

        self._nav_btns = []
        for perm_key, label, clase in self._submodulos:
            btn = ctk.CTkButton(
                barra, text=label,
                fg_color="transparent", text_color=col["texto_claro"],
                hover_color=col["tarjetas"],
                width=180, height=40, corner_radius=0,
            )
            # Si es un callable (placeholder builder), ejecutarlo;
            # si es una clase, instanciarla.
            if callable(clase) and not isinstance(clase, type):
                btn.configure(command=lambda b=btn, c=clase: self._activar_placeholder(b, c))
            else:
                btn.configure(command=lambda b=btn, c=clase: self._activar(b, c))
            btn.pack(side="left", padx=2)
            self._nav_btns.append((btn, clase))

    def _placeholder(self, nombre):
        """Devuelve una factory que crea un frame placeholder."""
        def _factory(parent, estilos, permisos):
            f = ctk.CTkFrame(parent, corner_radius=0,
                             fg_color=estilos["colores"]["fondo_oscuro"])
            ctk.CTkLabel(f, text=f"🔍 {nombre}",
                         font=estilos["fuentes"]["titulo"],
                         text_color=estilos["colores"]["principal"]
                         ).pack(pady=(40, 10))
            ctk.CTkLabel(f,
                         text=f"Registro de {nombre.lower()}.\nSubmódulo en desarrollo.",
                         font=estilos["fuentes"]["normal"],
                         text_color=estilos["colores"].get("texto_oscuro", "#94A3B8")
                         ).pack()
            return f
        return _factory

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

    def _activar_placeholder(self, btn, factory):
        col = self.estilos["colores"]
        if self._btn_activo:
            self._btn_activo.configure(
                fg_color="transparent", text_color=col["texto_claro"])
        btn.configure(fg_color=col["tarjetas"],
                      text_color=col["texto_oscuro"])
        self._btn_activo = btn
        for w in self.area.winfo_children():
            w.destroy()
        factory(self.area, self.estilos, self.permisos).pack(fill="both", expand=True)
