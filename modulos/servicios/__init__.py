"""
modulos/servicios/__init__.py
================================
Módulo Servicios — Fiscalizar, Entrada en Servicio, Lista de Equipos.
"""
import customtkinter as ctk
from core.permisos import puede


# ─── Submódulos inline ────────────────────────────────────────────────────────

class SubmoduloFiscalizar(ctk.CTkFrame):
    def __init__(self, parent, estilos, permisos=None):
        super().__init__(parent, corner_radius=0,
                         fg_color=estilos["colores"]["fondo_oscuro"])
        self.estilos = estilos
        self._ui()

    def _ui(self):
        col = self.estilos["colores"]
        ctk.CTkLabel(self, text="🔍  Fiscalizar",
                     font=self.estilos["fuentes"]["titulo"],
                     text_color=col["texto_oscuro"]).pack(pady=(30, 10))
        t = ctk.CTkFrame(self, fg_color=col["tarjetas"], corner_radius=12)
        t.pack(pady=10, padx=30, fill="both", expand=True)
        ctk.CTkLabel(t, text="🔍", font=("Roboto Mono", 48),
                     text_color=col["principal"]).pack(pady=(50, 10))
        ctk.CTkLabel(t, text="Registro de fiscalizaciones de equipos.\nSubmódulo en desarrollo.",
                     font=self.estilos["fuentes"]["normal"],
                     text_color="#4A6FA5", justify="center").pack()


class SubmoduloEntradaServicio(ctk.CTkFrame):
    def __init__(self, parent, estilos, permisos=None):
        super().__init__(parent, corner_radius=0,
                         fg_color=estilos["colores"]["fondo_oscuro"])
        self.estilos = estilos
        self._ui()

    def _ui(self):
        col = self.estilos["colores"]
        ctk.CTkLabel(self, text="🔧  Entrada en Servicio",
                     font=self.estilos["fuentes"]["titulo"],
                     text_color=col["texto_oscuro"]).pack(pady=(30, 10))
        t = ctk.CTkFrame(self, fg_color=col["tarjetas"], corner_radius=12)
        t.pack(pady=10, padx=30, fill="both", expand=True)
        ctk.CTkLabel(t, text="🔧", font=("Roboto Mono", 48),
                     text_color=col["principal"]).pack(pady=(50, 10))
        ctk.CTkLabel(t, text="Ingreso de equipos al taller de servicio técnico.\nSubmódulo en desarrollo.",
                     font=self.estilos["fuentes"]["normal"],
                     text_color="#4A6FA5", justify="center").pack()


class SubmoduloListaEquipos(ctk.CTkFrame):
    def __init__(self, parent, estilos, permisos=None):
        super().__init__(parent, corner_radius=0,
                         fg_color=estilos["colores"]["fondo_oscuro"])
        self.estilos = estilos
        self._ui()

    def _ui(self):
        col = self.estilos["colores"]
        ctk.CTkLabel(self, text="📋  Lista de Equipos en Servicio",
                     font=self.estilos["fuentes"]["titulo"],
                     text_color=col["texto_oscuro"]).pack(pady=(30, 10))
        t = ctk.CTkFrame(self, fg_color=col["tarjetas"], corner_radius=12)
        t.pack(pady=10, padx=30, fill="both", expand=True)
        ctk.CTkLabel(t, text="📋", font=("Roboto Mono", 48),
                     text_color=col["principal"]).pack(pady=(50, 10))
        ctk.CTkLabel(t, text="Equipos actualmente en servicio técnico.\nSubmódulo en desarrollo.",
                     font=self.estilos["fuentes"]["normal"],
                     text_color="#4A6FA5", justify="center").pack()


# ─── Módulo principal ─────────────────────────────────────────────────────────

class ModuloServicios(ctk.CTkFrame):
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
            ("Servicios.Fiscalizar",      "🔍 Fiscalizar",          SubmoduloFiscalizar),
            ("Servicios.EntradaServicio", "🔧 Entrada en Servicio",  SubmoduloEntradaServicio),
            ("Servicios.ListaEquipos",    "📋 Lista de Equipos",     SubmoduloListaEquipos),
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
                anchor="center", height=40, width=170,
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
