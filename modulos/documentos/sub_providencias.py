"""
modulos/documentos/sub_providencias.py
========================================
Submódulo Documentos › Providencias Administrativas
  - Agregar / ver / eliminar providencias del SENIAT y leyes del país
  - Búsqueda por nombre o descripción
"""

import os
import shutil
import uuid
import subprocess
import sys
import customtkinter as ctk
from tkinter import filedialog, messagebox

from core.database import (
    listar_providencias,
    agregar_providencia,
    eliminar_providencia,
)

DOCS_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "documentos", "providencias")


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


class SubmoduloProvidencias(ctk.CTkFrame):

    def __init__(self, parent, estilos):
        super().__init__(parent, corner_radius=0, fg_color="transparent")
        self.estilos = estilos
        self.col     = estilos["colores"]
        os.makedirs(DOCS_DIR, exist_ok=True)
        self._construir_ui()
        self._cargar_lista()

    # ─── Layout ────────────────────────────────────────────────────────────────
    def _construir_ui(self):
        col = self.col

        # ── Barra superior ─────────────────────────────────────────────────────
        barra = ctk.CTkFrame(self, fg_color=col["tarjetas"],
                             corner_radius=8, height=50)
        barra.pack(fill="x", padx=0, pady=(0, 8))
        barra.pack_propagate(False)

        ctk.CTkButton(barra, text="➕ Agregar Providencia",
                      width=190, height=34,
                      fg_color=col["principal"],
                      hover_color=col["principal_hover"],
                                text_color="#0A192F",
                      command=self._modal_agregar).pack(side="left", padx=10, pady=8)

        self._entry_buscar = ctk.CTkEntry(barra, placeholder_text="🔍 Buscar...",
                                          width=260, height=34)
        self._entry_buscar.pack(side="left", padx=8, pady=8)
        self._entry_buscar.bind("<KeyRelease>", lambda e: self._cargar_lista())

        # ── Lista ──────────────────────────────────────────────────────────────
        # Encabezado
        hdr = ctk.CTkFrame(self, fg_color="#0A192F",
                           corner_radius=6, height=32)
        hdr.pack(fill="x", padx=0, pady=(0, 2))
        hdr.pack_propagate(False)

        for txt, w in [("Nombre", None), ("Descripción", None),
                       ("Fecha Pub.", 110), ("Acciones", 76)]:
            ctk.CTkLabel(hdr, text=txt,
                         font=self.estilos["fuentes"]["normal"],
                         text_color=col["texto_claro"],
                         width=w or 0,
                         anchor="w").pack(side="left", padx=8)

        self._frame_lista = ctk.CTkScrollableFrame(
            self, fg_color="transparent")
        self._frame_lista.pack(fill="both", expand=True)

    # ─── Lista ─────────────────────────────────────────────────────────────────
    def _cargar_lista(self):
        for w in self._frame_lista.winfo_children():
            w.destroy()
        col = self.col
        filtro = self._entry_buscar.get().strip()
        docs   = listar_providencias(filtro)

        if not docs:
            ctk.CTkLabel(self._frame_lista,
                         text="Sin providencias registradas",
                         text_color="#5A7BAF",
                         font=self.estilos["fuentes"]["normal"]).pack(pady=20)
            return

        for doc_id, nombre, descripcion, ruta, fecha_pub, fecha_sub in docs:
            fila = ctk.CTkFrame(self._frame_lista, fg_color=col["tarjetas"],
                                corner_radius=6, height=36)
            fila.pack(fill="x", pady=2)
            fila.pack_propagate(False)

            # Botones (derecha primero)
            btn_f = ctk.CTkFrame(fila, fg_color="transparent", width=76)
            btn_f.pack(side="right", fill="y", padx=4)
            btn_f.pack_propagate(False)

            ctk.CTkButton(btn_f, text="📂", width=34, height=28,
                          fg_color="transparent", hover_color=col["principal"],
                          command=lambda r=ruta: _abrir_archivo(r)).pack(side="left", padx=1)
            ctk.CTkButton(btn_f, text="🗑", width=34, height=28,
                          fg_color="transparent", hover_color="#C0392B",
                          text_color="#E74C3C",
                          command=lambda did=doc_id, r=ruta: self._eliminar(did, r)).pack(side="left", padx=1)

            # Fecha publicación
            ctk.CTkLabel(fila, text=fecha_pub or "—",
                         width=110,
                         font=self.estilos["fuentes"]["normal"],
                         text_color=col["texto_oscuro"]).pack(side="right", padx=4)

            # Nombre + descripción
            ctk.CTkLabel(fila,
                         text=f"  {nombre}",
                         font=self.estilos["fuentes"]["normal"],
                         text_color=col["texto_oscuro"],
                         anchor="w", width=200).pack(side="left")
            ctk.CTkLabel(fila,
                         text=descripcion or "—",
                         font=self.estilos["fuentes"]["normal"],
                         text_color="#5A7BAF",
                         anchor="w").pack(side="left", fill="x", expand=True)

    # ─── Modal agregar ─────────────────────────────────────────────────────────
    def _modal_agregar(self):
        col = self.col
        modal = ctk.CTkToplevel(self)
        modal.title("Agregar Providencia")
        modal.geometry("480x360")
        modal.grab_set()

        ctk.CTkLabel(modal, text="📜 Nueva Providencia",
                     font=self.estilos["fuentes"]["subtitulo"],
                     text_color=col["principal"]).pack(pady=(16, 8))

        form = ctk.CTkFrame(modal, fg_color="transparent")
        form.pack(fill="x", padx=24)
        form.columnconfigure(1, weight=1)

        campos = [
            ("Nombre *", "entry_nombre"),
            ("Descripción", "entry_desc"),
            ("Fecha Publicación (YYYY-MM-DD)", "entry_fecha"),
        ]
        widgets = {}
        for i, (lbl, key) in enumerate(campos):
            ctk.CTkLabel(form, text=lbl, anchor="w",
                         font=self.estilos["fuentes"]["normal"],
                         text_color=col["texto_oscuro"]).grid(row=i, column=0, sticky="w",
                                                              padx=(0, 8), pady=4)
            e = ctk.CTkEntry(form, height=32)
            e.grid(row=i, column=1, sticky="ew", pady=4)
            widgets[key] = e

        # Archivo
        ctk.CTkLabel(form, text="Archivo *", anchor="w",
                     font=self.estilos["fuentes"]["normal"],
                     text_color=col["texto_oscuro"]).grid(row=3, column=0, sticky="w",
                                                           padx=(0, 8), pady=4)
        archivo_var = ctk.StringVar(value="Sin seleccionar")
        ruta_seleccionada = {"v": ""}

        fila_arch = ctk.CTkFrame(form, fg_color="transparent")
        fila_arch.grid(row=3, column=1, sticky="ew", pady=4)
        lbl_arch = ctk.CTkLabel(fila_arch, textvariable=archivo_var,
                                text_color="#5A7BAF",
                                font=self.estilos["fuentes"]["normal"])
        lbl_arch.pack(side="left", expand=True, anchor="w")

        def seleccionar():
            ruta = filedialog.askopenfilename(
                title="Seleccionar archivo",
                filetypes=[("Documentos", "*.pdf *.doc *.docx *.jpg *.jpeg *.png"),
                           ("Todos", "*.*")]
            )
            if ruta:
                ruta_seleccionada["v"] = ruta
                archivo_var.set(os.path.basename(ruta))

        ctk.CTkButton(fila_arch, text="📎 Seleccionar",
                      width=120, height=28,
                      fg_color=col["principal"],
                      hover_color=col["principal_hover"],
                                text_color="#0A192F",
                      command=seleccionar).pack(side="right")

        # Botón guardar
        def guardar():
            nombre = widgets["entry_nombre"].get().strip()
            desc   = widgets["entry_desc"].get().strip()
            fecha  = widgets["entry_fecha"].get().strip()
            ruta   = ruta_seleccionada["v"]

            if not nombre:
                messagebox.showwarning("Atención", "El nombre es obligatorio.", parent=modal)
                return
            if not ruta:
                messagebox.showwarning("Atención", "Selecciona un archivo.", parent=modal)
                return

            ext     = os.path.splitext(ruta)[1]
            destino = os.path.join(DOCS_DIR, f"{uuid.uuid4().hex[:10]}{ext}")
            shutil.copy2(ruta, destino)
            agregar_providencia(nombre, desc, destino, fecha)
            modal.destroy()
            self._cargar_lista()

        ctk.CTkButton(modal, text="💾 Guardar",
                      width=140, height=34,
                      fg_color=col["principal"],
                      hover_color=col["principal_hover"],
                                text_color="#0A192F",
                      command=guardar).pack(pady=16)

    # ─── Eliminar ──────────────────────────────────────────────────────────────
    def _eliminar(self, doc_id, ruta):
        if not messagebox.askyesno("Confirmar", "¿Eliminar esta providencia?"):
            return
        try:
            if os.path.isfile(ruta):
                os.remove(ruta)
        except Exception:
            pass
        eliminar_providencia(doc_id)
        self._cargar_lista()
