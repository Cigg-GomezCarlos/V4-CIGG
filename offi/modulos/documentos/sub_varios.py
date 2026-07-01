"""
modulos/documentos/sub_varios.py
=================================
Submódulo Documentos › Varios
  - Panel izquierdo: carpetas personalizadas (crear / eliminar)
  - Panel derecho: documentos dentro de la carpeta seleccionada (agregar / ver / eliminar)
"""

import os
import shutil
import uuid
import subprocess
import sys
import customtkinter as ctk
from tkinter import filedialog, messagebox, simpledialog

from core.database import (
    listar_carpetas,
    crear_carpeta,
    eliminar_carpeta,
    listar_doc_varios,
    agregar_doc_varios,
    eliminar_doc_varios,
)

DOCS_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "documentos", "varios")


def _abrir_archivo(ruta: str):
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


class SubmoduloVarios(ctk.CTkFrame):

    def __init__(self, parent, estilos):
        super().__init__(parent, corner_radius=0, fg_color="transparent")
        self.estilos     = estilos
        self.col         = estilos["colores"]
        self._carpeta_id  = None
        self._carpeta_nom = ""
        os.makedirs(DOCS_DIR, exist_ok=True)
        self._construir_ui()
        self._cargar_carpetas()

    # ─── Layout ────────────────────────────────────────────────────────────────
    def _construir_ui(self):
        col = self.col

        # Panel izquierdo — carpetas
        self._panel_izq = ctk.CTkFrame(self, width=200, corner_radius=8,
                                        fg_color=col["tarjetas"])
        self._panel_izq.pack(side="left", fill="y", padx=(0, 8))
        self._panel_izq.pack_propagate(False)

        ctk.CTkLabel(self._panel_izq, text="📁 Carpetas",
                     font=self.estilos["fuentes"]["subtitulo"],
                     text_color=col["principal"]).pack(pady=(12, 4), padx=8)

        ctk.CTkButton(self._panel_izq, text="➕ Nueva carpeta",
                      height=30, fg_color=col["principal"],
                      hover_color=col["principal_hover"],
                                text_color="#0A192F",
                      command=self._nueva_carpeta).pack(padx=8, pady=(0, 6), fill="x")

        self._lista_carpetas = ctk.CTkScrollableFrame(
            self._panel_izq, fg_color="transparent", corner_radius=0)
        self._lista_carpetas.pack(fill="both", expand=True, padx=4, pady=4)

        # Panel derecho — documentos
        self._panel_der = ctk.CTkFrame(self, corner_radius=8,
                                        fg_color=col["tarjetas"])
        self._panel_der.pack(side="left", fill="both", expand=True)

        self._placeholder()

    def _placeholder(self):
        for w in self._panel_der.winfo_children():
            w.destroy()
        ctk.CTkLabel(self._panel_der,
                     text="← Selecciona o crea una carpeta",
                     font=self.estilos["fuentes"]["normal"],
                     text_color="#5A7BAF").pack(expand=True)

    # ─── Carpetas ──────────────────────────────────────────────────────────────
    def _cargar_carpetas(self):
        for w in self._lista_carpetas.winfo_children():
            w.destroy()
        col = self.col
        carpetas = listar_carpetas()

        if not carpetas:
            ctk.CTkLabel(self._lista_carpetas, text="Sin carpetas",
                         text_color="#5A7BAF",
                         font=self.estilos["fuentes"]["normal"]).pack(pady=10)
            return

        for cid, nombre in carpetas:
            fila = ctk.CTkFrame(self._lista_carpetas, fg_color="transparent", height=34)
            fila.pack(fill="x", pady=2)
            fila.pack_propagate(False)

            ctk.CTkButton(fila, text="🗑", width=28, height=28,
                          fg_color="transparent", hover_color="#C0392B",
                          text_color="#E74C3C",
                          command=lambda ci=cid, n=nombre: self._eliminar_carpeta(ci, n)).pack(
                              side="right", padx=2)

            activa = (cid == self._carpeta_id)
            ctk.CTkButton(fila,
                          text=f"📁 {nombre}",
                          fg_color=col["principal"] if activa else "transparent",
                          text_color="#0A192F" if activa else col["texto_oscuro"],
                          hover_color=col["principal"],
                          anchor="w", height=28,
                          command=lambda ci=cid, n=nombre: self._seleccionar_carpeta(ci, n)).pack(
                              side="left", fill="x", expand=True)

    def _nueva_carpeta(self):
        nombre = simpledialog.askstring("Nueva carpeta", "Nombre de la carpeta:",
                                        parent=self)
        if not nombre or not nombre.strip():
            return
        nombre = nombre.strip()
        resultado = crear_carpeta(nombre)
        if resultado == -1:
            messagebox.showwarning("Atención", f"Ya existe una carpeta llamada '{nombre}'.")
            return
        carpeta_dir = os.path.join(DOCS_DIR, nombre)
        os.makedirs(carpeta_dir, exist_ok=True)
        self._carpeta_id  = resultado
        self._carpeta_nom = nombre
        self._cargar_carpetas()
        self._mostrar_documentos()

    def _seleccionar_carpeta(self, cid, nombre):
        self._carpeta_id  = cid
        self._carpeta_nom = nombre
        self._cargar_carpetas()
        self._mostrar_documentos()

    def _eliminar_carpeta(self, cid, nombre):
        if not messagebox.askyesno(
                "Confirmar",
                f"¿Eliminar la carpeta '{nombre}' y todos sus documentos?"):
            return
        eliminar_carpeta(cid)
        try:
            carpeta_dir = os.path.join(DOCS_DIR, nombre)
            if os.path.isdir(carpeta_dir):
                shutil.rmtree(carpeta_dir)
        except Exception:
            pass
        if self._carpeta_id == cid:
            self._carpeta_id  = None
            self._carpeta_nom = ""
            self._placeholder()
        self._cargar_carpetas()

    # ─── Documentos ────────────────────────────────────────────────────────────
    def _mostrar_documentos(self):
        for w in self._panel_der.winfo_children():
            w.destroy()
        col = self.col

        # Encabezado
        hdr = ctk.CTkFrame(self._panel_der, fg_color="transparent", height=46)
        hdr.pack(fill="x", padx=12, pady=(10, 4))
        hdr.pack_propagate(False)

        ctk.CTkLabel(hdr, text=f"📁 {self._carpeta_nom}",
                     font=self.estilos["fuentes"]["subtitulo"],
                     text_color=col["principal"]).pack(side="left")

        ctk.CTkButton(hdr, text="➕ Agregar documento",
                      width=170, height=32,
                      fg_color=col["principal"],
                      hover_color=col["principal_hover"],
                                text_color="#0A192F",
                      command=self._agregar_documento).pack(side="right")

        # Tabla encabezado
        th = ctk.CTkFrame(self._panel_der, fg_color="#0A192F",
                          corner_radius=6, height=30)
        th.pack(fill="x", padx=12, pady=(0, 2))
        th.pack_propagate(False)
        for txt, w in [("Nombre", None), ("Descripción", None), ("Acciones", 76)]:
            ctk.CTkLabel(th, text=txt,
                         font=self.estilos["fuentes"]["normal"],
                         text_color=col["texto_claro"],
                         width=w or 0, anchor="w").pack(side="left", padx=8)

        self._frame_docs = ctk.CTkScrollableFrame(
            self._panel_der, fg_color="transparent")
        self._frame_docs.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        self._cargar_documentos()

    def _cargar_documentos(self):
        for w in self._frame_docs.winfo_children():
            w.destroy()
        col = self.col
        docs = listar_doc_varios(self._carpeta_id)

        if not docs:
            ctk.CTkLabel(self._frame_docs,
                         text="Esta carpeta está vacía",
                         text_color="#5A7BAF",
                         font=self.estilos["fuentes"]["normal"]).pack(pady=20)
            return

        for doc_id, nombre, descripcion, ruta, fecha in docs:
            fila = ctk.CTkFrame(self._frame_docs, fg_color=col["fondo_oscuro"],
                                corner_radius=6, height=34)
            fila.pack(fill="x", pady=2)
            fila.pack_propagate(False)

            btn_f = ctk.CTkFrame(fila, fg_color="transparent", width=76)
            btn_f.pack(side="right", fill="y", padx=4)
            btn_f.pack_propagate(False)

            ctk.CTkButton(btn_f, text="📂", width=34, height=28,
                          fg_color="transparent", hover_color=col["principal"],
                          command=lambda r=ruta: _abrir_archivo(r)).pack(side="left", padx=1)
            ctk.CTkButton(btn_f, text="🗑", width=34, height=28,
                          fg_color="transparent", hover_color="#C0392B",
                          text_color="#E74C3C",
                          command=lambda did=doc_id, r=ruta: self._eliminar_doc(did, r)).pack(
                              side="left", padx=1)

            ctk.CTkLabel(fila, text=f"  {nombre}",
                         font=self.estilos["fuentes"]["normal"],
                         text_color=col["texto_oscuro"],
                         width=200, anchor="w").pack(side="left")
            ctk.CTkLabel(fila, text=descripcion or "—",
                         font=self.estilos["fuentes"]["normal"],
                         text_color="#5A7BAF",
                         anchor="w").pack(side="left", fill="x", expand=True)

    def _agregar_documento(self):
        col = self.col
        modal = ctk.CTkToplevel(self)
        modal.title("Agregar Documento")
        modal.geometry("460x260")
        modal.grab_set()

        ctk.CTkLabel(modal, text="📄 Agregar Documento",
                     font=self.estilos["fuentes"]["subtitulo"],
                     text_color=col["principal"]).pack(pady=(14, 8))

        form = ctk.CTkFrame(modal, fg_color="transparent")
        form.pack(fill="x", padx=24)
        form.columnconfigure(1, weight=1)

        campos_w = {}
        for i, (lbl, key) in enumerate([("Nombre *", "nombre"),
                                         ("Descripción", "desc")]):
            ctk.CTkLabel(form, text=lbl, anchor="w",
                         font=self.estilos["fuentes"]["normal"],
                         text_color=col["texto_oscuro"]).grid(
                             row=i, column=0, sticky="w", padx=(0, 8), pady=4)
            e = ctk.CTkEntry(form, height=32)
            e.grid(row=i, column=1, sticky="ew", pady=4)
            campos_w[key] = e

        ctk.CTkLabel(form, text="Archivo *", anchor="w",
                     font=self.estilos["fuentes"]["normal"],
                     text_color=col["texto_oscuro"]).grid(
                         row=2, column=0, sticky="w", padx=(0, 8), pady=4)

        archivo_var = ctk.StringVar(value="Sin seleccionar")
        ruta_sel    = {"v": ""}

        farch = ctk.CTkFrame(form, fg_color="transparent")
        farch.grid(row=2, column=1, sticky="ew", pady=4)
        ctk.CTkLabel(farch, textvariable=archivo_var,
                     text_color="#5A7BAF",
                     font=self.estilos["fuentes"]["normal"]).pack(side="left", expand=True, anchor="w")

        def seleccionar():
            ruta = filedialog.askopenfilename(
                filetypes=[("Documentos", "*.pdf *.doc *.docx *.jpg *.jpeg *.png *.xlsx *.xls"),
                           ("Todos", "*.*")]
            )
            if ruta:
                ruta_sel["v"] = ruta
                archivo_var.set(os.path.basename(ruta))

        ctk.CTkButton(farch, text="📎 Seleccionar",
                      width=120, height=28,
                      fg_color=col["principal"],
                      hover_color=col["principal_hover"],
                                text_color="#0A192F",
                      command=seleccionar).pack(side="right")

        def guardar():
            nombre = campos_w["nombre"].get().strip()
            desc   = campos_w["desc"].get().strip()
            ruta   = ruta_sel["v"]

            if not nombre:
                messagebox.showwarning("Atención", "El nombre es obligatorio.", parent=modal)
                return
            if not ruta:
                messagebox.showwarning("Atención", "Selecciona un archivo.", parent=modal)
                return

            carpeta_dir = os.path.join(DOCS_DIR, self._carpeta_nom)
            os.makedirs(carpeta_dir, exist_ok=True)
            ext = os.path.splitext(ruta)[1]
            destino = os.path.join(carpeta_dir, f"{uuid.uuid4().hex[:10]}{ext}")
            shutil.copy2(ruta, destino)
            agregar_doc_varios(self._carpeta_id, nombre, desc, destino)
            modal.destroy()
            self._cargar_documentos()

        ctk.CTkButton(modal, text="💾 Guardar",
                      width=130, height=34,
                      fg_color=col["principal"],
                      hover_color=col["principal_hover"],
                                text_color="#0A192F",
                      command=guardar).pack(pady=14)

    def _eliminar_doc(self, doc_id, ruta):
        if not messagebox.askyesno("Confirmar", "¿Eliminar este documento?"):
            return
        try:
            if os.path.isfile(ruta):
                os.remove(ruta)
        except Exception:
            pass
        eliminar_doc_varios(doc_id)
        self._cargar_documentos()
