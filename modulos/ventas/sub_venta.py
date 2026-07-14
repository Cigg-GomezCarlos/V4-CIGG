"""
modulos/ventas/sub_venta.py
===========================
Submódulo Venta — placeholder (en desarrollo).
"""
import customtkinter as ctk


class SubmoduloVenta(ctk.CTkFrame):
    def __init__(self, parent, estilos, permisos=None):
        super().__init__(parent, corner_radius=0,
                         fg_color=estilos["colores"]["fondo_oscuro"])
        self.estilos = estilos
        col = estilos["colores"]
        ctk.CTkLabel(self, text="🧾  Venta",
                     font=estilos["fuentes"]["titulo"],
                     text_color=col["texto_oscuro"]).pack(pady=(30, 10))
        t = ctk.CTkFrame(self, fg_color=col["tarjetas"], corner_radius=12)
        t.pack(pady=10, padx=30, fill="both", expand=True)
        ctk.CTkLabel(t, text="🧾", font=("Roboto Mono", 48),
                     text_color=col["principal"]).pack(pady=(50, 10))
        ctk.CTkLabel(t, text="Registro y gestión de ventas.\nSubmódulo en desarrollo.",
                     font=estilos["fuentes"]["normal"],
                     text_color="#4A6FA5", justify="center").pack()
