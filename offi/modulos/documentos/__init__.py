"""
modulos/documentos/__init__.py
================================
Módulo de Documentos — gestión documental centralizada.

Submódulos:
  · sub_sistemas_docs  — Homologaciones de sistemas + contratos de licencias
  · sub_maquinas_docs  — Cartas de enajenación + carta de entrega (template)
  · sub_providencias   — Providencias SENIAT / leyes del país
  · sub_varios         — Carpetas personalizadas con documentos libres
"""

import customtkinter as ctk

from .sub_sistemas_docs import SubmoduloSistemasDocs
from .sub_maquinas_docs import SubmoduloMaquinasDocs
from .sub_providencias  import SubmoduloProvidencias
from .sub_varios        import SubmoduloVarios


class ModuloDocumentos(ctk.CTkFrame):
    """Panel principal del módulo Documentos con barra de navegación horizontal."""

    def __init__(self, parent, estilos, permisos=None):
        super().__init__(parent, corner_radius=0,
                         fg_color=estilos["colores"]["fondo_oscuro"])
        self.estilos     = estilos
        self.permisos    = permisos or {}
        self._btn_activo = None

        self.area = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")

        self._construir_barra_nav()
        self.area.pack(side="bottom", fill="both", expand=True)

    # ─── Barra de navegación ──────────────────────────────────────────────────
    def _construir_barra_nav(self):
        col = self.estilos["colores"]

        barra = ctk.CTkFrame(self, height=50, corner_radius=0,
                             fg_color="#020C1B")
        barra.pack(side="top", fill="x")
        barra.pack_propagate(False)

        tabs = [
            ("📋 Sistemas",     SubmoduloSistemasDocs),
            ("🖨 Máquinas",     SubmoduloMaquinasDocs),
            ("📜 Providencias", SubmoduloProvidencias),
            ("📁 Varios",       SubmoduloVarios),
        ]

        primer_btn   = None
        primer_clase = None

        for texto, clase in tabs:
            btn = ctk.CTkButton(
                barra,
                text=texto,
                fg_color="transparent",
                text_color=col["texto_oscuro"],
                hover_color=col["tarjetas"],
                corner_radius=0,
                height=50,
                command=lambda c=clase, b=None: None,  # placeholder; se asigna abajo
            )
            btn.pack(side="left", padx=2, pady=0)

            if primer_btn is None:
                primer_btn   = btn
                primer_clase = clase

            # Cierre correcto de variable de loop
            btn.configure(command=lambda c=clase, b=btn: self._activar_tab(b, c))

        # Activar primera tab
        if primer_btn and primer_clase:
            self._activar_tab(primer_btn, primer_clase)

    def _activar_tab(self, btn, clase):
        col = self.estilos["colores"]

        # Resetear botón anterior
        if self._btn_activo and self._btn_activo != btn:
            self._btn_activo.configure(
                fg_color="transparent",
                text_color=col["texto_oscuro"],
            )

        btn.configure(
            fg_color=col["tarjetas"],
            text_color=col["texto_oscuro"],
        )
        self._btn_activo = btn

        # Limpiar área y cargar submódulo
        for w in self.area.winfo_children():
            w.destroy()

        clase(self.area, self.estilos).pack(
            fill="both", expand=True, padx=12, pady=10)
