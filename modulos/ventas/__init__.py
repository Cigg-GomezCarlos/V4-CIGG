"""
modulos/ventas/__init__.py
==========================
Módulo Ventas — orquestador de submódulos (Venta, Cotizaciones, CxC).

Cada submódulo vive en su propio archivo, igual que los demás módulos:
    • sub_venta.py         → SubmoduloVenta
    • sub_cotizaciones.py  → SubmoduloCotizaciones
    • sub_cxc.py           → SubmoduloCxC
"""
import customtkinter as ctk

from .sub_venta import SubmoduloVenta
from .sub_cotizaciones import SubmoduloCotizaciones
from .sub_cxc import SubmoduloCxC


class ModuloVentas(ctk.CTkFrame):
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
            ("Ventas.Venta",        "🧾 Venta",         SubmoduloVenta),
            ("Ventas.Cotizaciones", "📋 Cotizaciones",  SubmoduloCotizaciones),
            ("Ventas.CxC",          "💰 CxC",           SubmoduloCxC),
        ]

        self._nav_btns = []
        for perm_key, label, clase in self._submodulos:
            btn = ctk.CTkButton(
                barra, text=label,
                fg_color="transparent", text_color=col["texto_claro"],
                hover_color=col["tarjetas"],
                width=150, height=40, corner_radius=0,
            )
            btn.configure(command=lambda b=btn, c=clase: self._activar(b, c))
            btn.pack(side="left", padx=2)
            self._nav_btns.append((btn, clase))

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
