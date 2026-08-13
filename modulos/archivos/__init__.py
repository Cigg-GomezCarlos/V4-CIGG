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

import os
import shutil
from tkinter import filedialog, messagebox

import customtkinter as ctk
from core.permisos import puede

from .sub_usuarios    import SubmoduloUsuarios
from .sub_maquinas    import SubmoduloMaquinas
from .sub_proveedores import SubmoduloProveedores
from .sub_clientes    import SubmoduloClientes
from .sub_sistemas    import SubmoduloSistemas
from .sub_roles       import SubmoduloRoles


class SubmoduloEmpresa(ctk.CTkFrame):
    """
    Datos de la empresa (nombre, RIF, dirección, teléfono, correo, logo…)
    que se reflejan en las facturas y cotizaciones impresas.
    """

    CAMPOS = [
        ("nombre",    "Nombre / Razón Social"),
        ("eslogan",   "Eslogan (opcional)"),
        ("rif",       "RIF"),
        ("direccion", "Dirección Fiscal"),
        ("telefono",  "Teléfono"),
        ("correo",    "Correo"),
        ("ciudad",    "Ciudad"),
    ]

    def __init__(self, parent, estilos, permisos=None):
        super().__init__(parent, corner_radius=0, fg_color="transparent")
        self.estilos   = estilos
        self.permisos  = permisos or {}
        self._entries  = {}
        self._logo_sel = None   # ruta origen de un logo recién elegido

        col = estilos["colores"]

        # Raíz del proyecto y carpeta de imágenes
        self._base_dir = os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))))
        self._img_dir = os.path.join(self._base_dir, "imagenes")

        ctk.CTkLabel(
            self, text="🏢  Datos de la Empresa",
            font=("Segoe UI", 20, "bold"),
            text_color=col["texto_oscuro"],
        ).pack(anchor="w", padx=6, pady=(4, 2))

        ctk.CTkLabel(
            self,
            text="Esta información se muestra en el encabezado de facturas y cotizaciones.",
            font=("Segoe UI", 12),
            text_color=col.get("texto_secundario", "#8899AA"),
        ).pack(anchor="w", padx=6, pady=(0, 10))

        cont = ctk.CTkScrollableFrame(self, fg_color=col["tarjetas"],
                                      corner_radius=10)
        cont.pack(fill="both", expand=True, padx=4, pady=4)

        # Campos de texto
        for clave, etiqueta in self.CAMPOS:
            ctk.CTkLabel(cont, text=etiqueta, font=("Segoe UI", 12, "bold"),
                         text_color=col["texto_oscuro"]).pack(
                anchor="w", padx=16, pady=(10, 2))
            if clave == "direccion":
                e = ctk.CTkTextbox(cont, height=60,
                                   fg_color=col["fondo_oscuro"],
                                   text_color=col["texto_oscuro"])
                e.pack(fill="x", padx=16)
            else:
                e = ctk.CTkEntry(cont, height=34,
                                 fg_color=col["fondo_oscuro"],
                                 text_color=col["texto_oscuro"])
                e.pack(fill="x", padx=16)
            self._entries[clave] = e

        # Logo
        ctk.CTkLabel(cont, text="Logo (PNG / JPG)",
                     font=("Segoe UI", 12, "bold"),
                     text_color=col["texto_oscuro"]).pack(
            anchor="w", padx=16, pady=(14, 2))

        logo_row = ctk.CTkFrame(cont, fg_color="transparent")
        logo_row.pack(fill="x", padx=16, pady=(0, 4))

        ctk.CTkButton(
            logo_row, text="📁 Elegir logo…",
            fg_color=col["principal"], text_color="#0A192F",
            hover_color=col.get("principal_hover", "#00C4D4"),
            width=150, height=34, command=self._elegir_logo,
        ).pack(side="left")

        self.lbl_logo = ctk.CTkLabel(logo_row, text="(sin logo)",
                                     font=("Segoe UI", 12),
                                     text_color=col["texto_oscuro"])
        self.lbl_logo.pack(side="left", padx=12)

        self.prev_logo = ctk.CTkLabel(cont, text="")
        self.prev_logo.pack(anchor="w", padx=16, pady=(2, 10))

        # Botón guardar
        ctk.CTkButton(
            self, text="💾 Guardar datos",
            fg_color=col["principal"], text_color="#0A192F",
            hover_color=col.get("principal_hover", "#00C4D4"),
            height=40, font=("Segoe UI", 14, "bold"),
            command=self._guardar,
        ).pack(fill="x", padx=4, pady=(10, 2))

        self._cargar()

    # ─── Datos ────────────────────────────────────────────────────────────────

    def _set_entry(self, widget, valor):
        valor = valor or ""
        if isinstance(widget, ctk.CTkTextbox):
            widget.delete("1.0", "end")
            widget.insert("1.0", valor)
        else:
            widget.delete(0, "end")
            widget.insert(0, valor)

    def _get_entry(self, widget):
        if isinstance(widget, ctk.CTkTextbox):
            return widget.get("1.0", "end").strip()
        return widget.get().strip()

    def _cargar(self):
        try:
            from core.database import obtener_empresa
            datos = obtener_empresa() or {}
        except Exception as e:
            datos = {}
            print("obtener_empresa error:", e)

        for clave, _ in self.CAMPOS:
            self._set_entry(self._entries[clave], datos.get(clave, ""))

        self._logo_actual = datos.get("logo_path", "") or ""
        if self._logo_actual:
            self.lbl_logo.configure(text=self._logo_actual)
            self._mostrar_preview(os.path.join(self._img_dir, self._logo_actual))
        else:
            self.lbl_logo.configure(text="(sin logo)")

    def _mostrar_preview(self, ruta):
        try:
            from PIL import Image
            if os.path.exists(ruta):
                img = Image.open(ruta)
                w, h = img.size
                escala = min(160 / w, 90 / h, 1.0)
                cimg = ctk.CTkImage(light_image=img, dark_image=img,
                                    size=(int(w * escala), int(h * escala)))
                self.prev_logo.configure(image=cimg, text="")
                self.prev_logo._img_ref = cimg  # evitar GC
            else:
                self.prev_logo.configure(image=None, text="")
        except Exception as e:
            self.prev_logo.configure(image=None, text="")
            print("preview logo error:", e)

    def _elegir_logo(self):
        ruta = filedialog.askopenfilename(
            title="Seleccionar logo",
            filetypes=[("Imágenes", "*.png *.jpg *.jpeg"), ("Todos", "*.*")],
        )
        if not ruta:
            return
        self._logo_sel = ruta
        self.lbl_logo.configure(text="● " + os.path.basename(ruta))
        self._mostrar_preview(ruta)

    def _guardar(self):
        datos = {clave: self._get_entry(self._entries[clave])
                 for clave, _ in self.CAMPOS}

        # Copiar logo si se eligió uno nuevo
        logo_path = getattr(self, "_logo_actual", "") or ""
        if self._logo_sel:
            try:
                os.makedirs(self._img_dir, exist_ok=True)
                ext = os.path.splitext(self._logo_sel)[1].lower() or ".png"
                destino_nombre = "logo_empresa" + ext
                destino = os.path.join(self._img_dir, destino_nombre)
                shutil.copyfile(self._logo_sel, destino)
                logo_path = destino_nombre
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo copiar el logo:\n{e}")
                return
        datos["logo_path"] = logo_path

        try:
            from core.database import guardar_empresa
            guardar_empresa(datos)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar:\n{e}")
            return

        self._logo_sel = None
        self._logo_actual = logo_path
        messagebox.showinfo(
            "Guardado",
            "Datos de la empresa actualizados.\n"
            "Se reflejarán en las próximas facturas y cotizaciones.")


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
            ("Archivos.Empresa",     "🏢 Empresa",     SubmoduloEmpresa),
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
