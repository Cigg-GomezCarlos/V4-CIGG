"""
modulos/ventas/sub_cxc.py
=========================
Submódulo Cuentas por Cobrar — placeholder (en desarrollo).
"""
import customtkinter as ctk


class SubmoduloCxC(ctk.CTkFrame):
    def __init__(self, parent, estilos, permisos=None):
        super().__init__(parent, corner_radius=0,
                         fg_color=estilos["colores"]["fondo_oscuro"])
        self.estilos = estilos
        col = estilos["colores"]
        ctk.CTkLabel(self, text="💰  Cuentas por Cobrar",
                     font=estilos["fuentes"]["titulo"],
                     text_color=col["texto_oscuro"]).pack(pady=(30, 10))
        t = ctk.CTkFrame(self, fg_color=col["tarjetas"], corner_radius=12)
        t.pack(pady=10, padx=30, fill="both", expand=True)
        ctk.CTkLabel(t, text="💰", font=("Roboto Mono", 48),
                     text_color=col["principal"]).pack(pady=(50, 10))
        ctk.CTkLabel(t, text="Control de cuentas por cobrar.\nSubmódulo en desarrollo.",
                     font=estilos["fuentes"]["normal"],
                     text_color="#4A6FA5", justify="center").pack()
