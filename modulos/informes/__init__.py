"""
modulos/informes/__init__.py
================================
Módulo Informes — Inspecciones, Renovaciones, Historial Servicios,
Historial Fiscalización, Libro Máquinas, Historial Cliente, CxC.
"""
import customtkinter as ctk
from core.permisos import puede


# ─── Submódulos inline ────────────────────────────────────────────────────────

def _placeholder(parent, estilos, icono, titulo, desc):
    col = estilos["colores"]
    f = ctk.CTkFrame(parent, corner_radius=0, fg_color=col["fondo_oscuro"])
    ctk.CTkLabel(f, text=f"{icono}  {titulo}",
                 font=estilos["fuentes"]["titulo"],
                 text_color=col["texto_oscuro"]).pack(pady=(30, 10))
    t = ctk.CTkFrame(f, fg_color=col["tarjetas"], corner_radius=12)
    t.pack(pady=10, padx=30, fill="both", expand=True)
    ctk.CTkLabel(t, text=icono, font=("Roboto Mono", 48),
                 text_color=col["principal"]).pack(pady=(50, 10))
    ctk.CTkLabel(t, text=f"{desc}\nSubmódulo en desarrollo.",
                 font=estilos["fuentes"]["normal"],
                 text_color="#4A6FA5", justify="center").pack()
    return f


class SubmoduloInspecciones(ctk.CTkFrame):
    def __init__(self, parent, estilos, permisos=None):
        super().__init__(parent, corner_radius=0,
                         fg_color=estilos["colores"]["fondo_oscuro"])
        self.estilos = estilos
        _placeholder(self, estilos, "🔎", "Inspecciones",
                     "Informe de inspecciones realizadas.").pack(fill="both", expand=True)


class SubmoduloRenovaciones(ctk.CTkFrame):
    def __init__(self, parent, estilos, permisos=None):
        super().__init__(parent, corner_radius=0,
                         fg_color=estilos["colores"]["fondo_oscuro"])
        self.estilos = estilos
        _placeholder(self, estilos, "🔄", "Renovaciones",
                     "Renovaciones de contratos y licencias.").pack(fill="both", expand=True)


class SubmoduloHistorialServicios(ctk.CTkFrame):
    def __init__(self, parent, estilos, permisos=None):
        super().__init__(parent, corner_radius=0,
                         fg_color=estilos["colores"]["fondo_oscuro"])
        self.estilos = estilos
        _placeholder(self, estilos, "🔧", "Historial de Servicios",
                     "Registro histórico de servicios técnicos.").pack(fill="both", expand=True)


class SubmoduloHistorialFiscalizacion(ctk.CTkFrame):
    def __init__(self, parent, estilos, permisos=None):
        super().__init__(parent, corner_radius=0,
                         fg_color=estilos["colores"]["fondo_oscuro"])
        self.estilos = estilos
        _placeholder(self, estilos, "🔍", "Historial de Fiscalización",
                     "Historial de fiscalizaciones por equipo.").pack(fill="both", expand=True)


class SubmoduloLibroMaquinas(ctk.CTkFrame):
    def __init__(self, parent, estilos, permisos=None):
        super().__init__(parent, corner_radius=0,
                         fg_color=estilos["colores"]["fondo_oscuro"])
        self.estilos = estilos
        _placeholder(self, estilos, "📖", "Libro de Máquinas",
                     "Registro completo de todas las máquinas fiscales.").pack(fill="both", expand=True)


class SubmoduloHistorialCliente(ctk.CTkFrame):
    def __init__(self, parent, estilos, permisos=None):
        super().__init__(parent, corner_radius=0,
                         fg_color=estilos["colores"]["fondo_oscuro"])
        self.estilos = estilos
        _placeholder(self, estilos, "👤", "Historial de Cliente",
                     "Historial de operaciones por cliente.").pack(fill="both", expand=True)


class SubmoduloCxCInformes(ctk.CTkFrame):
    def __init__(self, parent, estilos, permisos=None):
        super().__init__(parent, corner_radius=0,
                         fg_color=estilos["colores"]["fondo_oscuro"])
        self.estilos = estilos
        _placeholder(self, estilos, "💰", "CxC",
                     "Reporte de cuentas por cobrar.").pack(fill="both", expand=True)


# ─── Módulo principal ─────────────────────────────────────────────────────────

class ModuloInformes(ctk.CTkFrame):
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
            ("Informes.Inspecciones",           "🔎 Inspecciones",       SubmoduloInspecciones),
            ("Informes.Renovaciones",           "🔄 Renovaciones",        SubmoduloRenovaciones),
            ("Informes.HistorialServicios",     "🔧 Hist. Servicios",     SubmoduloHistorialServicios),
            ("Informes.HistorialFiscalizacion", "🔍 Hist. Fiscalización", SubmoduloHistorialFiscalizacion),
            ("Informes.LibroMaquinas",          "📖 Libro Máquinas",      SubmoduloLibroMaquinas),
            ("Informes.HistorialCliente",       "👤 Hist. Cliente",       SubmoduloHistorialCliente),
            ("Informes.CxC",                    "💰 CxC",                 SubmoduloCxCInformes),
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
                anchor="center", height=40, width=145,
            )
            btn.pack(side="left", padx=2, pady=5)
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
