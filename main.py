"""
main.py
========
Punto de entrada de CIGG Systems — Central Administrative Panel.

Flujo de arranque:
  1. Inicializar toda la base de datos (una sola llamada)
  2. Pre-cargar tablas del módulo Monedas
  3. Lanzar actualización de tasas en segundo plano
  4. Mostrar pantalla de login
  5. Tras autenticación → panel principal con navegación lateral

Módulos disponibles:
  📁 Archivos   — usuarios, máquinas, proveedores, clientes, sistemas
  📊 Ventas     — facturación y ventas (en desarrollo)
  📦 Inventario — control de stock (en desarrollo)
  💱 Monedas    — tasas USD/EUR/USDT/VES/Tasa Externa
  🔧 Servicios  — órdenes de servicio (en desarrollo)
  📄 Documentos — gestión documental (en desarrollo)
  📈 Informes   — reportes y dashboards (en desarrollo)
"""

import os
import sys
import json

import customtkinter as ctk
from PIL import Image

# ── Core ──────────────────────────────────────────────────────────────────────
from core.database import inicializar_todo
from core.auth     import validar_credenciales_seguras
from core.permisos import cargar_permisos_usuario, puede
from core.session  import set_usuario_actual, clear_session

# ── Módulos ───────────────────────────────────────────────────────────────────
from modulos.archivos    import ModuloArchivos
from modulos.ventas      import ModuloVentas
from modulos.inventario  import ModuloInventario
from modulos.monedas     import ModuloMonedas, inicializar_tablas, actualizar_en_background
from modulos.servicios   import ModuloServicios
from modulos.documentos  import ModuloDocumentos
from modulos.informes    import ModuloInformes

# ── Inicialización de la BD (única llamada al arranque) ───────────────────────
inicializar_todo()
inicializar_tablas()
actualizar_en_background()          # actualiza tasas sin bloquear la UI

# ── Modo oscuro global ────────────────────────────────────────────────────────
ctk.set_appearance_mode("Dark")


# ─────────────────────────────────────────────────────────────────────────────
# APLICACIÓN PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

class AppAdministrativa(ctk.CTk):
    """
    Ventana raíz del sistema CIGG.

    Responsabilidades:
      - Cargar estilos desde config/estilos.json
      - Gestionar pantalla completa (modo kiosco)
      - Controlar login / logout
      - Enrutar módulos en el área de trabajo
    """

    def __init__(self):
        super().__init__()
        self.title("CIGG - Tech & Cyber Security")
        self.attributes("-fullscreen", True)

        self.estilos        = self._cargar_estilos()
        self.usuario_actual = ""
        self.permisos       = {}          # se carga tras login

        # Rutas de imágenes
        self._ruta_isotipo = os.path.join("imagenes", "isotipo_barra.png")
        self._ruta_logo    = os.path.join("imagenes", "logo_completo.png")

        # Imágenes precargadas
        self.img_barra = ctk.CTkImage(
            light_image=Image.open(self._ruta_isotipo),
            dark_image=Image.open(self._ruta_isotipo),
            size=(28, 28),
        )
        self.img_login = ctk.CTkImage(
            light_image=Image.open(self._ruta_logo),
            dark_image=Image.open(self._ruta_logo),
            size=(260, 156),
        )
        self.img_sidebar = ctk.CTkImage(
            light_image=Image.open(self._ruta_logo),
            dark_image=Image.open(self._ruta_logo),
            size=(190, 114),
        )

        self.configure(fg_color=self.estilos["colores"]["fondo_oscuro"])
        self._barra_superior()

        # Pie de página (debe empaquetarse ANTES del contenedor)
        self._crear_footer()

        # Contenedor dinámico (pantallas intercambiables)
        self.contenedor = ctk.CTkFrame(
            self, fg_color=self.estilos["colores"]["fondo_oscuro"],
            corner_radius=0)
        self.contenedor.pack(fill="both", expand=True)

        self.mostrar_login()

    # ─── Configuración ────────────────────────────────────────────────────────

    def _cargar_estilos(self) -> dict:
        """Lee config/estilos.json y convierte listas de fuentes a tuplas."""
        if getattr(sys, "frozen", False):
            base = sys._MEIPASS
        else:
            base = os.path.dirname(os.path.abspath(__file__))

        with open(os.path.join(base, "config", "estilos.json"),
                  encoding="utf-8") as f:
            datos = json.load(f)

        if "fuentes" in datos:
            datos["fuentes"] = {k: tuple(v)
                                 for k, v in datos["fuentes"].items()}
        return datos

    # ─── Barra superior ───────────────────────────────────────────────────────

    def _barra_superior(self):
        cfg = self.estilos["barra_superior"]
        col = self.estilos["colores"]

        barra = ctk.CTkFrame(self, height=40, corner_radius=0,
                             fg_color=cfg["fondo"])
        barra.pack(side="top", fill="x")
        barra.pack_propagate(False)

        ctk.CTkLabel(barra, image=self.img_barra, text="").pack(
            side="left", padx=(15, 8))

        ctk.CTkLabel(
            barra,
            text="CIGG SYSTEMS // Central Administrative Panel",
            text_color=cfg["texto"],
            font=("Roboto Mono", 11, "bold"),
        ).pack(side="left", padx=5)

        # Botones de control
        ctk.CTkButton(
            barra, text="✕", width=45, height=40, corner_radius=0,
            fg_color="transparent", hover_color=col["error"],
            text_color="#ffffff", font=("Arial", 14, "bold"),
            command=self.quit,
        ).pack(side="right")

        ctk.CTkButton(
            barra, text="—", width=45, height=40, corner_radius=0,
            fg_color="transparent", hover_color=cfg["hover_minimizar"],
            text_color="#ffffff", font=("Arial", 14, "bold"),
            command=self._minimizar,
        ).pack(side="right")

    # ─── Pie de página ────────────────────────────────────────────────────────

    def _crear_footer(self):
        col = self.estilos["colores"]

        wrap = ctk.CTkFrame(self, corner_radius=0, fg_color="#020C1B")
        wrap.pack(side="bottom", fill="x")

        # Línea separadora
        ctk.CTkFrame(wrap, height=1, fg_color=col["tarjetas"]).pack(fill="x")

        inner = ctk.CTkFrame(wrap, height=28, corner_radius=0,
                             fg_color="transparent")
        inner.pack(fill="x")
        inner.pack_propagate(False)

        self._lbl_footer_user = ctk.CTkLabel(
            inner, text="",
            text_color=col.get("texto_oscuro", "#94A3B8"),
            font=("Roboto Mono", 10),
        )
        self._lbl_footer_user.pack(side="left", padx=14)

        self._lbl_footer_tasas = ctk.CTkLabel(
            inner, text="",
            text_color=col.get("principal", "#00FF9D"),
            font=("Roboto Mono", 10),
        )
        self._lbl_footer_tasas.pack(side="right", padx=14)

    def _actualizar_footer(self):
        """Rellena usuario y tasas; se auto-refresca cada 60 s mientras se use."""
        import sqlite3
        from modulos.monedas.db import leer_todas
        from core.database import DB_NAME

        # ── Usuario ─────────────────────────────────────────────────────────
        try:
            con = sqlite3.connect(DB_NAME)
            row = con.execute(
                "SELECT nombre_completo FROM usuarios WHERE username=?",
                (self.usuario_actual,),
            ).fetchone()
            con.close()
            nombre = (row[0] or self.usuario_actual) if row else self.usuario_actual
        except Exception:
            nombre = self.usuario_actual

        self._lbl_footer_user.configure(text=f"👤  {nombre}")

        # ── Tasas ────────────────────────────────────────────────────────────
        tasas = leer_todas()

        def _fmt(codigo: str, etiqueta: str) -> str:
            t = tasas.get(codigo, {}).get("tasa", 0.0)
            return f"{etiqueta}: {t:,.4f} Bs"

        segmentos = [
            _fmt("USD",      "💵 USD"),
            _fmt("EUR",      "💶 EUR"),
            _fmt("USDT",     "🟡 USDT"),
            _fmt("TASA_EXT", "⚙️ T.Ext"),
        ]
        self._lbl_footer_tasas.configure(text="   │   ".join(segmentos) + "   ")

        # Refrescar cada 60 s automáticamente
        self._footer_job = self.after(60_000, self._actualizar_footer)

    def _detener_footer(self):
        if hasattr(self, "_footer_job"):
            self.after_cancel(self._footer_job)

    def _minimizar(self):
        self.attributes("-fullscreen", False)
        self.iconify()
        self.bind("<FocusIn>", self._restaurar)

    def _restaurar(self, _event=None):
        self.attributes("-fullscreen", True)
        self.unbind("<FocusIn>")

    # ─── Utilidades ───────────────────────────────────────────────────────────

    def _limpiar(self):
        for w in self.contenedor.winfo_children():
            w.destroy()

    # ─── Login ────────────────────────────────────────────────────────────────

    def mostrar_login(self):
        self._limpiar()
        col   = self.estilos["colores"]
        fuente = self.estilos["fuentes"]["normal"]

        panel = ctk.CTkFrame(self.contenedor,
                             width=440, height=540,
                             fg_color=col["tarjetas"])
        panel.place(relx=0.5, rely=0.5, anchor="center")
        panel.pack_propagate(False)

        ctk.CTkLabel(panel, image=self.img_login, text="").pack(pady=(35, 15))

        txt_user = ctk.CTkEntry(
            panel, placeholder_text="ID DE USUARIO CIGG",
            width=320, font=fuente, text_color=col["texto_oscuro"],
            fg_color="#0A192F", border_color=col["principal"],
        )
        txt_user.pack(pady=12)
        txt_user.focus()

        txt_pass = ctk.CTkEntry(
            panel, placeholder_text="TOKEN DE ACCESO",
            show="*", width=320, font=fuente,
            text_color=col["texto_oscuro"],
            fg_color="#0A192F", border_color=col["principal"],
        )
        txt_pass.pack(pady=12)

        lbl_error = ctk.CTkLabel(panel, text="",
                                  text_color=col["error"], font=fuente)
        lbl_error.pack(pady=5)

        def _login(event=None):
            ok, msg = validar_credenciales_seguras(
                txt_user.get(), txt_pass.get())
            if ok:
                self.usuario_actual = txt_user.get().strip()
                set_usuario_actual(self.usuario_actual)
                self.permisos       = cargar_permisos_usuario(self.usuario_actual)
                self.unbind("<Return>")
                self._actualizar_footer()
                self.mostrar_panel_principal()
            else:
                lbl_error.configure(text=msg)

        ctk.CTkButton(
            panel, text="INICIAR SISTEMA",
            fg_color=col["principal"], hover_color=col["principal_hover"],
            text_color="#0A192F", font=fuente,
            height=38, width=320, command=_login,
        ).pack(pady=20)

        self.bind("<Return>", _login)

    # ─── Panel principal ──────────────────────────────────────────────────────

    def mostrar_panel_principal(self):
        self._limpiar()
        col = self.estilos["colores"]

        # Barra lateral
        self.sidebar = ctk.CTkFrame(
            self.contenedor, width=240, corner_radius=0,
            fg_color="#020C1B")
        self.sidebar.pack(side="left", fill="y")

        # Área de trabajo
        self.area = ctk.CTkFrame(
            self.contenedor, corner_radius=0,
            fg_color=col["fondo_oscuro"])
        self.area.pack(side="right", fill="both", expand=True)

        # Logo en sidebar
        ctk.CTkLabel(self.sidebar, image=self.img_sidebar, text="").pack(
            pady=(25, 10), padx=15)

        # Separador decorativo
        ctk.CTkFrame(self.sidebar, height=1,
                     fg_color=col["tarjetas"]).pack(fill="x", padx=15, pady=4)

        # Definición de botones del menú lateral (filtrados por permisos)
        nav_todos = [
            ("📁  Archivos",   "Archivos",   lambda: self._cargar(ModuloArchivos)),
            ("📊  Ventas",     "Ventas",      lambda: self._cargar(ModuloVentas)),
            ("📦  Inventario", "Inventario",  lambda: self._cargar(ModuloInventario)),
            ("💱  Monedas",    "Monedas",     lambda: self._cargar_monedas()),
            ("🔧  Servicios",  "Servicios",   lambda: self._cargar(ModuloServicios)),
            ("📄  Documentos", "Documentos",  lambda: self._cargar(ModuloDocumentos)),
            ("📈  Informes",   "Informes",    lambda: self._cargar(ModuloInformes)),
        ]

        self._btns_nav  = []
        primer_modulo   = None
        primer_callback = None

        for texto, clave, cmd in nav_todos:
            if not puede(self.permisos, clave, "ver"):
                continue
            btn = ctk.CTkButton(
                self.sidebar,
                text=texto,
                fg_color="transparent",
                text_color=col["texto_oscuro"],
                hover_color=col["tarjetas"],
                anchor="w", height=42,
                command=cmd,
            )
            btn.pack(pady=3, padx=15, fill="x")
            self._btns_nav.append(btn)
            if primer_modulo is None:
                primer_modulo   = btn
                primer_callback = cmd

        # Botón de cerrar sesión (abajo)
        def _logout():
            clear_session()
            self.usuario_actual = ""
            self._detener_footer()
            self._lbl_footer_user.configure(text="")
            self._lbl_footer_tasas.configure(text="")
            self.mostrar_login()

        ctk.CTkButton(
            self.sidebar,
            text="🔌  Cerrar Sesión",
            fg_color=col["error"], text_color="#ffffff",
            hover_color="#8B0000", height=38,
            command=_logout,
        ).pack(side="bottom", pady=25, padx=15, fill="x")

        # Módulo inicial: Monedas (fallback al primero visible)
        if puede(self.permisos, "Monedas", "ver"):
            self._cargar_monedas()
        elif primer_callback:
            primer_callback()

    # ─── Enrutamiento de módulos ──────────────────────────────────────────────

    def _limpiar_area(self):
        for w in self.area.winfo_children():
            w.destroy()

    def _cargar(self, clase_modulo):
        """Instancia e inyecta cualquier módulo estándar, pasando permisos."""
        self._limpiar_area()
        try:
            modulo = clase_modulo(self.area, self.estilos,
                                  permisos=self.permisos)
        except TypeError:
            # módulos placeholder que aún no aceptan permisos
            modulo = clase_modulo(self.area, self.estilos)
        modulo.pack(fill="both", expand=True)
        self.update_idletasks()

    def _cargar_monedas(self):
        """Instancia ModuloMonedas pasando el usuario en sesión."""
        self._limpiar_area()
        modulo = ModuloMonedas(
            self.area, self.estilos,
            usuario=self.usuario_actual or "Sistema")
        modulo.pack(fill="both", expand=True)
        self.update_idletasks()


# ─────────────────────────────────────────────────────────────────────────────
# PUNTO DE ENTRADA
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = AppAdministrativa()
    app.mainloop()
