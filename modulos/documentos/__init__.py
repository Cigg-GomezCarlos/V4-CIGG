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
from tkinter import messagebox

from .sub_sistemas_docs import SubmoduloSistemasDocs
from .sub_maquinas_docs import SubmoduloMaquinasDocs
from .sub_providencias  import SubmoduloProvidencias
from .sub_varios        import SubmoduloVarios

from core.database import (
    obtener_contrato_pago,
    guardar_contrato_pago,
    _CONTRATO_PAGO_DEFAULT,
)


class SubmoduloContratoPago(ctk.CTkFrame):
    """Editor de la plantilla del Contrato de Compromiso de Pago (crédito).

    Es la misma plantilla que usa la impresión de ventas a crédito. Los
    cambios guardados aquí se reflejan automáticamente en cada contrato
    que se genere desde el módulo de Ventas.
    """

    _PLACEHOLDERS = (
        "[EMPRESA_NOMBRE] [EMPRESA_RIF] [CLIENTE_NOMBRE] [CLIENTE_RIF] "
        "[CLIENTE_DIR] [VENTA_NUMERO] [VENTA_FECHA] [VENTA_TOTAL] [INICIAL] "
        "[NUM_CUOTAS] [MONTO_CUOTA] [DIAS_FRECUENCIA] [FECHA_PRIMERA_CUOTA] "
        "[PLAN_PAGOS] [CIUDAD]"
    )

    def __init__(self, parent, estilos):
        super().__init__(parent, corner_radius=0, fg_color="transparent")
        self.estilos = estilos
        self._construir_ui()

    def _construir_ui(self):
        col = self.estilos["colores"]

        sec = ctk.CTkFrame(self, corner_radius=8, fg_color=col["fondo_oscuro"])
        sec.pack(fill="both", expand=True)

        hdr = ctk.CTkFrame(sec, fg_color="transparent", height=36)
        hdr.pack(fill="x", padx=10, pady=(10, 2))
        hdr.pack_propagate(False)

        ctk.CTkLabel(hdr, text="💳 Contrato de Compromiso de Pago (Plantilla)",
                     font=self.estilos["fuentes"]["subtitulo"],
                     text_color=col["texto_claro"]).pack(side="left")

        ctk.CTkLabel(sec,
                     text="Placeholders disponibles:\n" + self._PLACEHOLDERS,
                     font=("Roboto Mono", 10), justify="left",
                     text_color="#5A7BAF").pack(anchor="w", padx=10, pady=(0, 4))

        self._txt = ctk.CTkTextbox(sec, font=("Roboto Mono", 11),
                                   fg_color=col["tarjetas"],
                                   text_color=col["texto_oscuro"])
        self._txt.pack(fill="both", expand=True, padx=10, pady=4)

        self._txt.delete("1.0", "end")
        self._txt.insert("1.0", obtener_contrato_pago() or _CONTRATO_PAGO_DEFAULT)

        btn_row = ctk.CTkFrame(sec, fg_color="transparent")
        btn_row.pack(fill="x", padx=10, pady=(0, 10))

        ctk.CTkButton(btn_row, text="💾 Guardar Plantilla",
                      width=170, height=32,
                      fg_color=col["principal"],
                      hover_color=col.get("principal_hover", col["principal"]),
                      text_color="#0A192F",
                      command=self._guardar).pack(side="left", padx=(0, 8))

        ctk.CTkButton(btn_row, text="↺ Restaurar por defecto",
                      width=190, height=32,
                      fg_color=col["tarjetas"],
                      text_color=col["texto_oscuro"],
                      command=self._restaurar).pack(side="left")

    def _guardar(self):
        contenido = self._txt.get("1.0", "end").rstrip()
        guardar_contrato_pago(contenido)
        messagebox.showinfo("Guardado",
                            "Plantilla del contrato de pago guardada.\n"
                            "Se usará en las próximas ventas a crédito.")

    def _restaurar(self):
        if not messagebox.askyesno("Restaurar",
                                   "¿Restaurar la plantilla original? "
                                   "Se perderán los cambios guardados."):
            return
        self._txt.delete("1.0", "end")
        self._txt.insert("1.0", _CONTRATO_PAGO_DEFAULT)


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
            ("💳 Contrato Pago", SubmoduloContratoPago),
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
