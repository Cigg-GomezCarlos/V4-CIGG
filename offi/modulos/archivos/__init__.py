"""
modulos/archivos/__init__.py
============================
Módulo de Archivos — punto de entrada y navegación entre submódulos.

Submódulos disponibles:
  · sub_usuarios.py    — Gestión de usuarios del sistema
  · sub_maquinas.py    — Control de modelos y unidades de máquinas fiscales
  · sub_proveedores.py — Registro y edición de proveedores
  · sub_clientes.py    — Cartera de clientes corporativos
  · sub_sistemas.py    — Configuración de sistemas (en desarrollo)
  · sub_roles.py       — Gestión de roles y permisos
"""

import customtkinter as ctk
from core.permisos import puede

from .sub_usuarios    import SubmoduloUsuarios
from .sub_maquinas    import SubmoduloMaquinas
from .sub_proveedores import SubmoduloProveedores
from .sub_clientes    import SubmoduloClientes
from .sub_sistemas    import SubmoduloSistemas
from .sub_roles       import SubmoduloRoles


class ModuloArchivos(ctk.CTkFrame):
    """
    Marco principal del módulo Archivos.
    Contiene una barra de navegación horizontal y un área de contenido
    donde se inyectan los submódulos de forma dinámica.
    Respeta los permisos del rol activo para filtrar tabs y controles.
    """

    def __init__(self, parent, estilos, permisos=None):
        super().__init__(parent, corner_radius=0,
                         fg_color=estilos["colores"]["fondo_oscuro"])
        self.estilos  = estilos
        self.permisos = permisos or {}
        self._btn_activo = None

        # Área de contenido intercambiable
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

        # (clave_permiso, texto_botón, clase_submodulo)
        todas = [
            ("Archivos.Usuarios",    "👤 Usuarios",    SubmoduloUsuarios),
            ("Archivos.Máquinas",    "🖥 Máquinas",    SubmoduloMaquinas),
            ("Archivos.Proveedores", "📦 Proveedores", SubmoduloProveedores),
            ("Archivos.Clientes",    "🤝 Clientes",    SubmoduloClientes),
            ("Archivos.Sistemas",    "⚙️ Sistemas",    SubmoduloSistemas),
            ("Archivos.Roles",       "🔐 Roles",       SubmoduloRoles),
        ]

        primer_btn   = None
        primer_clase = None

        for clave, texto, clase in todas:
            if not puede(self.permisos, clave, "ver"):
                continue

            btn = ctk.CTkButton(
                barra,
                text=texto,
                fg_color="transparent",
                text_color=col["texto_oscuro"],
                hover_color=col["tarjetas"],
                width=175, height=50, corner_radius=0,
            )
            btn.configure(command=lambda c=clase, b=btn: self.cargar(c, b))
            btn.pack(side="left", padx=1)

            if primer_btn is None:
                primer_btn   = btn
                primer_clase = clase

        # Cargar el primer submódulo visible
        if primer_btn and primer_clase:
            self.cargar(primer_clase, primer_btn)

    # ─── Navegación ──────────────────────────────────────────────────────────

    def cargar(self, clase_submodulo, btn_origen=None):
        """Limpia el área y monta el submódulo indicado, pasando permisos."""
        col = self.estilos["colores"]

        if self._btn_activo:
            self._btn_activo.configure(fg_color="transparent")

        if btn_origen:
            btn_origen.configure(fg_color=col["tarjetas"])
            self._btn_activo = btn_origen

        for w in self.area.winfo_children():
            w.destroy()

        try:
            sub = clase_submodulo(self.area, self.estilos,
                                  permisos=self.permisos)
        except TypeError:
            sub = clase_submodulo(self.area, self.estilos)

        sub.pack(fill="both", expand=True, padx=15, pady=15)
