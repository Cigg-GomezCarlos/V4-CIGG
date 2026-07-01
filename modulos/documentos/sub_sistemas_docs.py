"""
modulos/documentos/sub_sistemas_docs.py
========================================
Submódulo Documentos › Sistemas
  - Panel izquierdo: lista de modelos de software
  - Panel derecho:
      · Homologaciones — adjuntar / ver / eliminar
      · Contratos       — lista de licencias que ya tienen contrato cargado
"""

import os
import shutil
import uuid
import subprocess
import sys
import customtkinter as ctk
from tkinter import filedialog, messagebox

from core.database import (
    listar_modelos_sistemas,
    listar_homologaciones,
    agregar_homologacion,
    eliminar_homologacion,
    listar_licencias_con_contrato,
)

DOCS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "documentos", "homologaciones")


def _abrir_archivo(ruta: str):
    """Abre un archivo con el programa predeterminado del SO."""
    if not os.path.isfile(ruta):
        messagebox.showerror("Error", f"Archivo no encontrado:\n{ruta}")
        return
    try:
        if sys.platform.startswith("win"):
            os.startfile(ruta)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", ruta])
        else:
            subprocess.Popen(["xdg-open", ruta])
    except Exception as e:
        messagebox.showerror("Error", str(e))


class SubmoduloSistemasDocs(ctk.CTkFrame):

    def __init__(self, parent, estilos):
        super().__init__(parent, corner_radius=0, fg_color="transparent")
        self.estilos   = estilos
        self.col       = estilos["colores"]
        self._modelo_id   = None
        self._modelo_nom  = ""
        self._btn_activo  = None

        os.makedirs(DOCS_DIR, exist_ok=True)
        self._construir_ui()

    # ─── Layout principal ──────────────────────────────────────────────────────
    def _construir_ui(self):
        col = self.col

        # Panel izquierdo — modelos
        self._panel_izq = ctk.CTkFrame(self, width=200, corner_radius=8,
                                        fg_color=col["tarjetas"])
        self._panel_izq.pack(side="left", fill="y", padx=(0, 8), pady=0)
        self._panel_izq.pack_propagate(False)

        ctk.CTkLabel(self._panel_izq, text="📦 Sistemas",
                     font=self.estilos["fuentes"]["subtitulo"],
                     text_color=col["principal"]).pack(pady=(12, 6), padx=8)

        self._lista_modelos = ctk.CTkScrollableFrame(
            self._panel_izq, fg_color="transparent", corner_radius=0)
        self._lista_modelos.pack(fill="both", expand=True, padx=4, pady=4)

        btn_ref = ctk.CTkButton(self._panel_izq, text="🔄 Actualizar",
                                height=30, fg_color=col["principal"],
                                hover_color=col["principal_hover"],
                                text_color="#0A192F",
                                command=self._cargar_modelos)
        btn_ref.pack(pady=6, padx=8, fill="x")

        # Panel derecho — contenido
        self._panel_der = ctk.CTkFrame(self, corner_radius=8,
                                        fg_color=col["tarjetas"])
        self._panel_der.pack(side="left", fill="both", expand=True)

        self._placeholder()
        self._cargar_modelos()

    def _placeholder(self):
        for w in self._panel_der.winfo_children():
            w.destroy()
        ctk.CTkLabel(self._panel_der,
                     text="← Selecciona un sistema",
                     font=self.estilos["fuentes"]["normal"],
                     text_color="#5A7BAF").pack(expand=True)

    # ─── Modelos ───────────────────────────────────────────────────────────────
    def _cargar_modelos(self):
        for w in self._lista_modelos.winfo_children():
            w.destroy()
        self._btn_activo = None

        modelos = listar_modelos_sistemas()
        if not modelos:
            ctk.CTkLabel(self._lista_modelos, text="Sin registros",
                         text_color="#5A7BAF",
                         font=self.estilos["fuentes"]["normal"]).pack(pady=10)
            return

        for mid, nombre in modelos:
            btn = ctk.CTkButton(
                self._lista_modelos,
                text=nombre,
                fg_color="transparent",
                text_color=self.col["texto_oscuro"],
                hover_color=self.col["principal"],
                anchor="w",
                height=34,
                command=lambda i=mid, n=nombre: self._seleccionar_modelo(i, n),
            )
            btn.pack(fill="x", pady=2)

    def _seleccionar_modelo(self, modelo_id: int, nombre: str):
        self._modelo_id  = modelo_id
        self._modelo_nom = nombre
        self._mostrar_contenido()

    # ─── Panel derecho ─────────────────────────────────────────────────────────
    def _mostrar_contenido(self):
        for w in self._panel_der.winfo_children():
            w.destroy()
        col = self.col

        # Título
        ctk.CTkLabel(self._panel_der,
                     text=f"📦 {self._modelo_nom}",
                     font=self.estilos["fuentes"]["subtitulo"],
                     text_color=col["principal"]).pack(pady=(14, 6), padx=16, anchor="w")

        # ── Sección Homologaciones ─────────────────────────────────────────────
        sec_homo = ctk.CTkFrame(self._panel_der, corner_radius=8,
                                fg_color=col["fondo_oscuro"])
        sec_homo.pack(fill="both", expand=True, padx=12, pady=(0, 6))

        hdr_homo = ctk.CTkFrame(sec_homo, fg_color="transparent", height=36)
        hdr_homo.pack(fill="x", padx=10, pady=(8, 2))
        hdr_homo.pack_propagate(False)

        ctk.CTkLabel(hdr_homo, text="📋 Cartas de Homologación",
                     font=self.estilos["fuentes"]["subtitulo"],
                     text_color=col["texto_claro"]).pack(side="left")

        ctk.CTkButton(hdr_homo, text="➕ Adjuntar",
                      width=110, height=28,
                      fg_color=col["principal"],
                      hover_color=col["principal_hover"],
                                text_color="#0A192F",
                      command=self._adjuntar_homologacion).pack(side="right")

        self._frame_homo = ctk.CTkScrollableFrame(
            sec_homo, fg_color="transparent", height=160)
        self._frame_homo.pack(fill="both", expand=True, padx=8, pady=4)

        self._cargar_homologaciones()

        # ── Sección Contratos ──────────────────────────────────────────────────
        sec_cont = ctk.CTkFrame(self._panel_der, corner_radius=8,
                                fg_color=col["fondo_oscuro"])
        sec_cont.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        ctk.CTkLabel(sec_cont, text="📄 Contratos de Licencias",
                     font=self.estilos["fuentes"]["subtitulo"],
                     text_color=col["texto_claro"]).pack(anchor="w", padx=10, pady=(8, 2))

        self._frame_cont = ctk.CTkScrollableFrame(
            sec_cont, fg_color="transparent", height=160)
        self._frame_cont.pack(fill="both", expand=True, padx=8, pady=4)

        self._cargar_contratos()

    # ─── Homologaciones ────────────────────────────────────────────────────────
    def _cargar_homologaciones(self):
        for w in self._frame_homo.winfo_children():
            w.destroy()
        col = self.col
        docs = listar_homologaciones(self._modelo_id)

        if not docs:
            ctk.CTkLabel(self._frame_homo, text="Sin homologaciones adjuntas",
                         text_color="#5A7BAF",
                         font=self.estilos["fuentes"]["normal"]).pack(pady=8)
            return

        for doc_id, nombre, ruta, fecha in docs:
            fila = ctk.CTkFrame(self._frame_homo, fg_color=col["tarjetas"],
                                corner_radius=6, height=34)
            fila.pack(fill="x", pady=2)
            fila.pack_propagate(False)

            btn_frame = ctk.CTkFrame(fila, fg_color="transparent", width=76)
            btn_frame.pack(side="right", fill="y")
            btn_frame.pack_propagate(False)

            ctk.CTkButton(btn_frame, text="📂", width=34, height=28,
                          fg_color="transparent",
                          hover_color=col["principal"],
                          command=lambda r=ruta: _abrir_archivo(r)).pack(side="left", padx=1)
            ctk.CTkButton(btn_frame, text="🗑", width=34, height=28,
                          fg_color="transparent",
                          hover_color="#C0392B",
                          text_color="#E74C3C",
                          command=lambda did=doc_id, r=ruta: self._eliminar_homo(did, r)).pack(side="left", padx=1)

            ctk.CTkLabel(fila, text=f"  {nombre}",
                         font=self.estilos["fuentes"]["normal"],
                         text_color=col["texto_oscuro"],
                         anchor="w").pack(side="left", fill="both", expand=True)

    def _adjuntar_homologacion(self):
        ruta = filedialog.askopenfilename(
            title="Seleccionar homologación",
            filetypes=[("Documentos", "*.pdf *.doc *.docx *.jpg *.jpeg *.png"),
                       ("Todos", "*.*")]
        )
        if not ruta:
            return
        nombre = os.path.basename(ruta)
        ext    = os.path.splitext(nombre)[1]
        destino_nombre = f"{self._modelo_nom}_{uuid.uuid4().hex[:8]}{ext}"
        destino = os.path.join(DOCS_DIR, destino_nombre)
        shutil.copy2(ruta, destino)
        agregar_homologacion(self._modelo_id, nombre, destino)
        self._cargar_homologaciones()

    def _eliminar_homo(self, doc_id: int, ruta: str):
        if not messagebox.askyesno("Confirmar", "¿Eliminar este documento?"):
            return
        try:
            if os.path.isfile(ruta):
                os.remove(ruta)
        except Exception:
            pass
        eliminar_homologacion(doc_id)
        self._cargar_homologaciones()

    # ─── Contratos ─────────────────────────────────────────────────────────────
    def _cargar_contratos(self):
        for w in self._frame_cont.winfo_children():
            w.destroy()
        col = self.col
        licencias = listar_licencias_con_contrato(self._modelo_id)

        if not licencias:
            ctk.CTkLabel(self._frame_cont,
                         text="No hay licencias con contrato adjunto para este sistema",
                         text_color="#5A7BAF",
                         font=self.estilos["fuentes"]["normal"]).pack(pady=8)
            return

        for lic_id, licencia, version, cliente, ruta in licencias:
            fila = ctk.CTkFrame(self._frame_cont, fg_color=col["tarjetas"],
                                corner_radius=6, height=34)
            fila.pack(fill="x", pady=2)
            fila.pack_propagate(False)

            ctk.CTkButton(fila, text="📂", width=34, height=28,
                          fg_color="transparent",
                          hover_color=col["principal"],
                          command=lambda r=ruta: _abrir_archivo(r)).pack(side="right", padx=4)

            texto = f"  {licencia}  |  v{version}  |  {cliente or '—'}"
            ctk.CTkLabel(fila, text=texto,
                         font=self.estilos["fuentes"]["normal"],
                         text_color=col["texto_oscuro"],
                         anchor="w").pack(side="left", fill="both", expand=True)


# ─── Función pública ────────────────────────────────────────────────────────────
def imprimir_homologacion_al_registrar(modelo_id: int):
    """
    Abre automáticamente todas las homologaciones del modelo al registrar
    una nueva licencia. Si no hay ninguna adjunta, no hace nada.
    """
    homologaciones = listar_homologaciones(modelo_id)
    for _did, _nombre, ruta, _fecha in homologaciones:
        _abrir_archivo(ruta)
