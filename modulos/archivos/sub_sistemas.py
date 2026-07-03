"""
modulos/archivos/sub_sistemas.py
==================================
Submódulo de control de sistemas instalados.

Flujo:
  Vista Modelos  →  [➕ Nuevo Sistema]  →  Formulario modal
  Tarjeta Sistema→  [📋 Ver/Registrar Licencias] → Vista Licencias
  Vista Licencias→  Formulario (licencia + versión + fecha) + tabla

Estructura BD:
  modelos_sistemas  — nombre, proveedor, imagen
  sistemas_licencias — modelo_id, licencia, version, fecha_licencia
"""

import os
import shutil
import sqlite3
import tkinter.filedialog as fd
import customtkinter as ctk
from core.permisos import puede
from tkinter import messagebox
from PIL import Image
from core.database import DB_NAME, obtener_proveedores_sistemas
from modulos.documentos.sub_sistemas_docs import imprimir_homologacion_al_registrar


class SubmoduloSistemas(ctk.CTkFrame):
    """Panel de modelos de sistemas y sus licencias registradas."""

    def __init__(self, parent, estilos, permisos=None):
        super().__init__(parent, fg_color="transparent")
        self.estilos  = estilos
        self.permisos = permisos or {}
        self._puede_editar   = puede(self.permisos, "Archivos.Sistemas", "editar")
        self._puede_eliminar = puede(self.permisos, "Archivos.Sistemas", "eliminar")

        # ── Encabezado ────────────────────────────────────────────────────────
        self.header = ctk.CTkFrame(self, fg_color="transparent")
        self.header.pack(fill="x", padx=10, pady=(5, 10))

        self.lbl_titulo = ctk.CTkLabel(
            self.header,
            text="🖥️ PANEL DE SISTEMAS",
            font=estilos["fuentes"]["subtitulo"],
            text_color=estilos["colores"]["texto_oscuro"],
        )
        self.lbl_titulo.pack(side="left")

        self.btn_nuevo = ctk.CTkButton(
            self.header, text="➕ Nuevo Sistema",
            font=estilos["fuentes"]["normal"],
            fg_color=estilos["colores"]["principal"],
            hover_color=estilos["colores"]["principal_hover"],
            text_color="#0A192F", width=160, height=34,
            command=self._abrir_ventana_crear_sistema,
        )
        if self._puede_editar:
            self.btn_nuevo.pack(side="right")

        # ── Área de contenido ─────────────────────────────────────────────────
        self.area_contenido = ctk.CTkFrame(self, fg_color="transparent")
        self.area_contenido.pack(fill="both", expand=True, padx=10, pady=5)

        self._mostrar_vista_modelos()

    # ─────────────────────────────────────────────────────────────────────────
    # VISTA MODELOS (cuadrícula de tarjetas)
    # ─────────────────────────────────────────────────────────────────────────

    def _limpiar_contenido(self):
        for w in self.area_contenido.winfo_children():
            w.destroy()

    def _mostrar_vista_modelos(self):
        self._limpiar_contenido()
        self.lbl_titulo.configure(text="🖥️ PANEL DE SISTEMAS")
        self.btn_nuevo.pack(side="right")

        self._grid_frame = ctk.CTkScrollableFrame(
            self.area_contenido, fg_color="#020C1B", corner_radius=8
        )
        self._grid_frame.pack(fill="both", expand=True)
        self._refrescar_cuadricula()

    def _refrescar_cuadricula(self):
        for w in self._grid_frame.winfo_children():
            w.destroy()
        for i in range(3):
            self._grid_frame.columnconfigure(i, weight=1)

        try:
            con = sqlite3.connect(DB_NAME)
            cur = con.cursor()
            cur.execute("""
                SELECT id, nombre, proveedor, nombre_imagen
                FROM modelos_sistemas
                ORDER BY nombre ASC
            """)
            modelos = cur.fetchall()
            con.close()
        except Exception:
            modelos = []

        if not modelos:
            ctk.CTkLabel(
                self._grid_frame,
                text="No hay sistemas registrados.\nPresiona  ➕ Nuevo Sistema  para comenzar.",
                font=self.estilos["fuentes"]["normal"],
                text_color="#4A6FA5",
            ).grid(row=0, column=0, columnspan=3, pady=60)
            return

        for idx, (mid, nombre, proveedor, img_nombre) in enumerate(modelos):
            fila, col_idx = divmod(idx, 3)
            self._crear_tarjeta(mid, nombre, proveedor, img_nombre, fila, col_idx)

    def _crear_tarjeta(self, mid, nombre, proveedor, img_nombre, fila, col_idx):
        col = self.estilos["colores"]
        card = ctk.CTkFrame(
            self._grid_frame, fg_color=col["tarjetas"],
            corner_radius=12, border_width=1, border_color="#1A3550",
        )
        card.grid(row=fila, column=col_idx, padx=15, pady=15, sticky="nsew")

        # Imagen del sistema
        ruta_img = os.path.join("imagenes", img_nombre) if img_nombre else ""
        if ruta_img and os.path.exists(ruta_img):
            try:
                img_obj = ctk.CTkImage(
                    light_image=Image.open(ruta_img),
                    dark_image=Image.open(ruta_img), size=(120, 100),
                )
                lbl_img = ctk.CTkLabel(card, image=img_obj, text="")
                lbl_img.pack(pady=(15, 5))
                lbl_img._img_ref = img_obj
            except Exception:
                ctk.CTkLabel(card, text="📷 Error",
                             font=self.estilos["fuentes"]["normal"],
                             text_color=col["error"]).pack(pady=20)
        else:
            ctk.CTkLabel(card, text="🖥️ Sin Imagen",
                         font=self.estilos["fuentes"]["normal"],
                         text_color="#4A6FA5").pack(pady=25)

        ctk.CTkLabel(card, text=nombre,
                     font=self.estilos["fuentes"]["subtitulo"],
                     text_color=col["texto_oscuro"]).pack()
        ctk.CTkLabel(card, text=f"Proveedor: {proveedor or '—'}",
                     font=self.estilos["fuentes"]["normal"],
                     text_color=col["principal"]).pack(pady=(0, 6))

        # Contador de licencias
        try:
            con = sqlite3.connect(DB_NAME)
            cur = con.cursor()
            cur.execute("SELECT COUNT(*) FROM sistemas_licencias WHERE modelo_id=?", (mid,))
            total = cur.fetchone()[0]
            con.close()
        except Exception:
            total = 0
        ctk.CTkLabel(card, text=f"Licencias: {total}",
                     font=self.estilos["fuentes"]["normal"],
                     text_color="#4A6FA5").pack(pady=(0, 8))

        ctk.CTkButton(
            card, text="📋 Ver / Registrar Licencias",
            font=self.estilos["fuentes"]["normal"],
            fg_color="#1A3550", hover_color=col["principal_hover"],
            text_color=col["texto_oscuro"],
            command=lambda i=mid, n=nombre, p=proveedor: self._mostrar_vista_licencias(i, n, p),
        ).pack(fill="x", padx=15, pady=(0, 5))

        ctk.CTkButton(
            card, text="✏️ Editar Sistema",
            font=self.estilos["fuentes"]["normal"],
            fg_color="#1A3550", hover_color=col["principal_hover"],
            text_color=col["texto_oscuro"],
            command=lambda i=mid, n=nombre, p=proveedor, im=img_nombre: self._editar_modelo(i, n, p, im),
        ).pack(fill="x", padx=15, pady=(0, 5))

        if self._puede_eliminar:
            ctk.CTkButton(
                card, text="🗑️ Eliminar Sistema",
                font=self.estilos["fuentes"]["normal"],
                fg_color=col["error"], hover_color="#8B1E1E",
                command=lambda i=mid: self._eliminar_modelo(i),
            ).pack(fill="x", padx=15, pady=(0, 15))

    def _eliminar_modelo(self, mid):
        # Verificar si tiene licencias registradas
        try:
            con = sqlite3.connect(DB_NAME)
            cur = con.cursor()
            cur.execute("SELECT COUNT(*) FROM sistemas_licencias WHERE modelo_id=?", (mid,))
            total = cur.fetchone()[0]
            con.close()
        except Exception:
            total = 0
        if total > 0:
            messagebox.showwarning(
                "No se puede eliminar",
                f"Este sistema tiene {total} licencia(s) registrada(s).\n"
                "Elimine primero todas las licencias asociadas.",
            )
            return
        if not messagebox.askyesno("Confirmar", "¿Eliminar este sistema?"):
            return
        try:
            con = sqlite3.connect(DB_NAME)
            cur = con.cursor()
            cur.execute("PRAGMA foreign_keys = ON")
            cur.execute("DELETE FROM modelos_sistemas WHERE id=?", (mid,))
            con.commit()
            con.close()
        except Exception:
            pass
        self._refrescar_cuadricula()

    def _editar_modelo(self, mid, nombre_actual, proveedor_actual, img_actual):
        col  = self.estilos["colores"]
        font = self.estilos["fuentes"]["normal"]

        ventana = ctk.CTkToplevel(self)
        ventana.title("Editar Sistema")
        ventana.geometry("480x520")
        ventana.resizable(False, False)
        ventana.configure(fg_color=col["fondo_oscuro"])
        ventana.grab_set()
        ventana.lift()

        ctk.CTkLabel(ventana, text="✏️ EDITAR SISTEMA",
                     font=self.estilos["fuentes"]["subtitulo"],
                     text_color=col["principal"]).pack(pady=(25, 10))

        ctk.CTkLabel(ventana, text="Nombre del sistema:", font=font,
                     text_color=col["texto_oscuro"]).pack(anchor="w", padx=40)
        entry_nombre = ctk.CTkEntry(ventana, width=400, font=font,
                                    border_color=col["principal"])
        entry_nombre.insert(0, nombre_actual or "")
        entry_nombre.pack(padx=40, pady=(4, 16))

        ctk.CTkLabel(ventana, text="Proveedor de Sistema:",
                     font=font, text_color=col["texto_oscuro"]).pack(anchor="w", padx=40)
        proveedores = obtener_proveedores_sistemas()
        valores_prov = proveedores if proveedores else ["⚠ Registre un proveedor tipo Sistemas"]
        cmb_prov = ctk.CTkComboBox(ventana, values=valores_prov,
                                    width=400, height=34,
                                    dropdown_fg_color="#1A3550")
        cmb_prov.set(proveedor_actual if proveedor_actual in valores_prov else valores_prov[0])
        cmb_prov.pack(padx=40, pady=(4, 16))

        self._ruta_img_edicion = ""
        ctk.CTkLabel(ventana, text="Imagen del sistema (opcional):",
                     font=font, text_color=col["texto_oscuro"]).pack(anchor="w", padx=40)
        frame_img = ctk.CTkFrame(ventana, fg_color="transparent")
        frame_img.pack(fill="x", padx=40, pady=(4, 16))
        lbl_img = ctk.CTkLabel(frame_img,
                               text=img_actual if img_actual else "Sin imagen seleccionada",
                               font=font, text_color=col["principal"] if img_actual else "#4A6FA5")
        lbl_img.pack(side="left", fill="x", expand=True)

        def seleccionar_imagen():
            ruta = fd.askopenfilename(
                title="Selecciona imagen del sistema",
                filetypes=[("Imágenes", "*.png *.jpg *.jpeg *.bmp *.webp")],
            )
            if ruta:
                self._ruta_img_edicion = ruta
                lbl_img.configure(text=os.path.basename(ruta), text_color=col["principal"])

        ctk.CTkButton(frame_img, text="📁 Buscar", font=font, width=110,
                      fg_color="#1A3550", hover_color=col["principal_hover"],
                      text_color=col["texto_oscuro"],
                      command=seleccionar_imagen).pack(side="right")

        lbl_status = ctk.CTkLabel(ventana, text="", font=font, text_color=col["error"])
        lbl_status.pack(pady=6)

        def guardar():
            nombre = entry_nombre.get().strip()
            proveedor = cmb_prov.get()
            if not nombre:
                lbl_status.configure(text="⚠ El nombre del sistema es obligatorio.")
                return
            if "⚠" in proveedor:
                lbl_status.configure(text="⚠ Selecciona un proveedor válido.")
                return
            nombre_img = img_actual or ""
            if self._ruta_img_edicion and os.path.exists(self._ruta_img_edicion):
                nombre_img = os.path.basename(self._ruta_img_edicion)
                destino = os.path.join("imagenes", nombre_img)
                try:
                    if not os.path.exists(destino):
                        shutil.copy2(self._ruta_img_edicion, destino)
                except Exception:
                    pass
            try:
                con = sqlite3.connect(DB_NAME)
                cur = con.cursor()
                cur.execute("""
                    UPDATE modelos_sistemas
                       SET nombre=?, proveedor=?, nombre_imagen=?
                     WHERE id=?
                """, (nombre, proveedor, nombre_img, mid))
                con.commit()
                con.close()
                ventana.destroy()
                self._refrescar_cuadricula()
            except sqlite3.IntegrityError:
                lbl_status.configure(text="⚠ Ya existe un sistema con ese nombre.")
            except Exception as e:
                lbl_status.configure(text=f"Error: {e}")

        ctk.CTkButton(
            ventana, text="💾 GUARDAR CAMBIOS",
            font=font, width=400, height=42,
            fg_color=col["principal"], hover_color=col["principal_hover"],
            text_color="#0A192F", command=guardar,
        ).pack(pady=10, padx=40)

    # ─────────────────────────────────────────────────────────────────────────
    # VENTANA MODAL: CREAR SISTEMA
    # ─────────────────────────────────────────────────────────────────────────

    def _abrir_ventana_crear_sistema(self):
        col  = self.estilos["colores"]
        font = self.estilos["fuentes"]["normal"]

        ventana = ctk.CTkToplevel(self)
        ventana.title("Nuevo Sistema")
        ventana.geometry("480x500")
        ventana.resizable(False, False)
        ventana.configure(fg_color=col["fondo_oscuro"])
        ventana.grab_set()
        ventana.lift()

        ctk.CTkLabel(ventana, text="➕ REGISTRAR NUEVO SISTEMA",
                     font=self.estilos["fuentes"]["subtitulo"],
                     text_color=col["principal"]).pack(pady=(25, 10))

        # Nombre del sistema
        ctk.CTkLabel(ventana, text="Nombre del sistema:", font=font,
                     text_color=col["texto_oscuro"]).pack(anchor="w", padx=40)
        entry_nombre = ctk.CTkEntry(ventana, width=400, font=font,
                                    border_color=col["principal"])
        entry_nombre.pack(padx=40, pady=(4, 16))

        # Proveedor de sistemas
        ctk.CTkLabel(ventana, text="Proveedor de Sistema:",
                     font=font, text_color=col["texto_oscuro"]).pack(anchor="w", padx=40)

        proveedores = obtener_proveedores_sistemas()
        valores_prov = proveedores if proveedores else ["⚠ Registre un proveedor tipo Sistemas"]

        cmb_prov = ctk.CTkComboBox(ventana, values=valores_prov,
                                    width=400, height=34,
                                    dropdown_fg_color="#1A3550")
        cmb_prov.set(valores_prov[0])
        cmb_prov.pack(padx=40, pady=(4, 16))

        # Imagen opcional
        self._ruta_img_seleccionada = ""
        ctk.CTkLabel(ventana, text="Imagen del sistema (opcional):",
                     font=font, text_color=col["texto_oscuro"]).pack(anchor="w", padx=40)

        frame_img = ctk.CTkFrame(ventana, fg_color="transparent")
        frame_img.pack(fill="x", padx=40, pady=(4, 16))

        lbl_img = ctk.CTkLabel(frame_img, text="Sin imagen seleccionada",
                               font=font, text_color="#4A6FA5")
        lbl_img.pack(side="left", fill="x", expand=True)

        def seleccionar_imagen():
            ruta = fd.askopenfilename(
                title="Selecciona imagen del sistema",
                filetypes=[("Imágenes", "*.png *.jpg *.jpeg *.bmp *.webp")],
            )
            if ruta:
                self._ruta_img_seleccionada = ruta
                lbl_img.configure(text=os.path.basename(ruta), text_color=col["principal"])

        ctk.CTkButton(frame_img, text="📁 Buscar", font=font, width=110,
                      fg_color="#1A3550", hover_color=col["principal_hover"],
                      text_color=col["texto_oscuro"],
                      command=seleccionar_imagen).pack(side="right")

        lbl_status = ctk.CTkLabel(ventana, text="", font=font, text_color=col["error"])
        lbl_status.pack(pady=6)

        def guardar():
            nombre = entry_nombre.get().strip()
            proveedor = cmb_prov.get()

            if not nombre:
                lbl_status.configure(text="⚠ El nombre del sistema es obligatorio.")
                return
            if "⚠" in proveedor:
                lbl_status.configure(text="⚠ Selecciona un proveedor válido.")
                return

            nombre_img = ""
            if self._ruta_img_seleccionada and os.path.exists(self._ruta_img_seleccionada):
                nombre_img = os.path.basename(self._ruta_img_seleccionada)
                destino = os.path.join("imagenes", nombre_img)
                try:
                    if not os.path.exists(destino):
                        shutil.copy2(self._ruta_img_seleccionada, destino)
                except Exception:
                    pass

            try:
                con = sqlite3.connect(DB_NAME)
                cur = con.cursor()
                cur.execute("""
                    INSERT INTO modelos_sistemas (nombre, proveedor, nombre_imagen)
                    VALUES (?, ?, ?)
                """, (nombre, proveedor, nombre_img))
                con.commit()
                con.close()
                ventana.destroy()
                self._refrescar_cuadricula()
            except sqlite3.IntegrityError:
                lbl_status.configure(text="⚠ Ya existe un sistema con ese nombre.")
            except Exception as e:
                lbl_status.configure(text=f"Error: {e}")

        ctk.CTkButton(
            ventana, text="💾 GUARDAR SISTEMA",
            font=font, width=400, height=42,
            fg_color=col["principal"], hover_color=col["principal_hover"],
            text_color="#0A192F", command=guardar,
        ).pack(pady=10, padx=40)

    # ─────────────────────────────────────────────────────────────────────────
    # VISTA LICENCIAS
    # ─────────────────────────────────────────────────────────────────────────

    def _mostrar_vista_licencias(self, mid, nombre_mod, proveedor):
        self._limpiar_contenido()
        self.lbl_titulo.configure(text=f"📋 Licencias › {nombre_mod}")
        self.btn_nuevo.pack_forget()

        col  = self.estilos["colores"]
        font = self.estilos["fuentes"]["normal"]

        # Estado edición: [id] o [None]
        _editando_id  = [None]
        _ruta_contrato = [""]       # ruta del archivo seleccionado en el form
        _dropdown_top  = [None]     # Toplevel del autocomplete

        # Botón volver
        barra = ctk.CTkFrame(self.area_contenido, fg_color="transparent")
        barra.pack(fill="x", pady=(0, 8))
        ctk.CTkButton(
            barra, text="← Volver a Sistemas", font=font,
            fg_color="#1A3550", hover_color=col["principal_hover"],
            text_color=col["texto_oscuro"], width=180, height=32,
            command=self._mostrar_vista_modelos,
        ).pack(side="left")

        # Layout: formulario izquierda | lista derecha
        layout = ctk.CTkFrame(self.area_contenido, fg_color="transparent")
        layout.pack(fill="both", expand=True)
        layout.columnconfigure(0, weight=1)
        layout.columnconfigure(1, weight=2)
        layout.rowconfigure(0, weight=1)

        # ── Formulario ────────────────────────────────────────────────────────
        form = ctk.CTkScrollableFrame(layout, fg_color="#020C1B", corner_radius=8)
        form.grid(row=0, column=0, padx=(0, 8), pady=0, sticky="nsew")

        lbl_form_titulo = ctk.CTkLabel(
            form, text="REGISTRAR LICENCIA",
            font=self.estilos["fuentes"]["subtitulo"],
            text_color=col["principal"],
        )
        lbl_form_titulo.pack(pady=(20, 10), padx=15)

        # Campo Licencia
        ctk.CTkLabel(form, text="Número de Licencia:", font=font,
                     text_color=col["texto_oscuro"]).pack(anchor="w", padx=20)
        entry_licencia = ctk.CTkEntry(form, placeholder_text="Ej: LIC-2026-00123",
                                      width=270, font=font,
                                      border_color=col["principal"])
        entry_licencia.pack(pady=(4, 10), padx=20)

        # Campo Versión
        ctk.CTkLabel(form, text="Versión:", font=font,
                     text_color=col["texto_oscuro"]).pack(anchor="w", padx=20)
        entry_version = ctk.CTkEntry(form, placeholder_text="Ej: 4.1.2",
                                     width=270, font=font,
                                     border_color=col["principal"])
        entry_version.pack(pady=(4, 10), padx=20)

        # Campo Fecha
        ctk.CTkLabel(form, text="Fecha de Licencia:", font=font,
                     text_color=col["texto_oscuro"]).pack(anchor="w", padx=20)
        entry_fecha = ctk.CTkEntry(form, placeholder_text="Ej: 2026-12-31",
                                   width=270, font=font,
                                   border_color=col["principal"])
        entry_fecha.pack(pady=(4, 10), padx=20)

        # ── Campo Cliente con autocomplete ────────────────────────────────────
        ctk.CTkLabel(form, text="Cliente:", font=font,
                     text_color=col["texto_oscuro"]).pack(anchor="w", padx=20)
        try:
            con_c = sqlite3.connect(DB_NAME)
            cur_c = con_c.cursor()
            cur_c.execute("SELECT razon_social FROM clientes ORDER BY razon_social ASC")
            _todos_clientes = [r[0] for r in cur_c.fetchall()]
            con_c.close()
        except Exception:
            _todos_clientes = []

        entry_cliente = ctk.CTkEntry(
            form, placeholder_text="Escribe para buscar cliente…",
            width=270, font=font, border_color=col["principal"],
        )
        entry_cliente.pack(pady=(4, 10), padx=20)

        def _cerrar_dropdown(event=None):
            if _dropdown_top[0] and _dropdown_top[0].winfo_exists():
                _dropdown_top[0].destroy()
            _dropdown_top[0] = None

        def _seleccionar_cliente(nombre):
            entry_cliente.delete(0, "end")
            entry_cliente.insert(0, nombre)
            _cerrar_dropdown()

        def _actualizar_dropdown(event=None):
            _cerrar_dropdown()
            texto = entry_cliente.get().strip().lower()
            if not texto:
                return
            coincidencias = [c for c in _todos_clientes if texto in c.lower()]
            if not coincidencias:
                return

            entry_cliente.update_idletasks()
            x = entry_cliente.winfo_rootx()
            y = entry_cliente.winfo_rooty() + entry_cliente.winfo_height()
            w = entry_cliente.winfo_width()
            h = min(len(coincidencias) * 32, 192)

            top = ctk.CTkToplevel(self)
            top.overrideredirect(True)
            top.geometry(f"{w}x{h}+{x}+{y}")
            top.configure(fg_color="#1A3550")
            top.attributes("-topmost", True)
            top.lift()
            _dropdown_top[0] = top

            scr_d = ctk.CTkScrollableFrame(top, fg_color="#1A3550", corner_radius=0)
            scr_d.pack(fill="both", expand=True)
            for nombre in coincidencias:
                ctk.CTkButton(
                    scr_d, text=nombre, font=font,
                    fg_color="transparent", hover_color=col["principal_hover"],
                    text_color=col["texto_oscuro"], anchor="w", height=30,
                    command=lambda n=nombre: _seleccionar_cliente(n),
                ).pack(fill="x", padx=2, pady=1)

        entry_cliente.bind("<KeyRelease>", _actualizar_dropdown)
        # Cierra dropdown con pequeño delay para permitir el click en la opción
        entry_cliente.bind("<FocusOut>", lambda e: form.after(150, _cerrar_dropdown))

        # ── Campo Contrato (adjunto) ───────────────────────────────────────────
        ctk.CTkLabel(form, text="Contrato (PDF/DOC):", font=font,
                     text_color=col["texto_oscuro"]).pack(anchor="w", padx=20)
        frm_doc = ctk.CTkFrame(form, fg_color="transparent")
        frm_doc.pack(fill="x", padx=20, pady=(4, 10))
        lbl_doc = ctk.CTkLabel(frm_doc, text="Sin documento adjunto",
                               font=font, text_color="#4A6FA5", anchor="w")
        lbl_doc.pack(side="left", fill="x", expand=True)

        def seleccionar_contrato():
            ruta = fd.askopenfilename(
                title="Seleccionar contrato",
                filetypes=[("Documentos", "*.pdf *.doc *.docx *.jpg *.png"),
                           ("Todos los archivos", "*.*")],
            )
            if ruta:
                _ruta_contrato[0] = ruta
                lbl_doc.configure(text=os.path.basename(ruta),
                                  text_color=col["principal"])

        ctk.CTkButton(frm_doc, text="📎 Adjuntar", font=font, width=100,
                      fg_color="#1A3550", hover_color=col["principal_hover"],
                      text_color=col["texto_oscuro"],
                      command=seleccionar_contrato).pack(side="right")

        lbl_st = ctk.CTkLabel(form, text="", font=font, text_color=col["error"])
        lbl_st.pack(pady=4)

        # Botones del formulario
        btn_guardar = ctk.CTkButton(
            form, text="💾 REGISTRAR LICENCIA", font=font, width=270, height=40,
            fg_color=col["principal"], hover_color=col["principal_hover"],
            text_color="#0A192F",
        )
        btn_guardar.pack(pady=(0, 4), padx=20)

        btn_cancelar = ctk.CTkButton(
            form, text="🚫 Cancelar edición", font=font, width=270, height=34,
            fg_color="#1A3550", hover_color=col["error"],
            text_color=col["texto_oscuro"],
        )
        # Se muestra solo en modo edición

        # ── Lista de licencias ────────────────────────────────────────────────
        panel = ctk.CTkFrame(layout, fg_color="#020C1B", corner_radius=8)
        panel.grid(row=0, column=1, pady=0, sticky="nsew")

        ctk.CTkLabel(panel, text=f"LICENCIAS — {nombre_mod.upper()}",
                     font=self.estilos["fuentes"]["subtitulo"],
                     text_color=col["texto_oscuro"]).pack(pady=(20, 10), padx=15)

        scroll = ctk.CTkScrollableFrame(panel, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        def abrir_contrato(ruta):
            import subprocess, sys
            try:
                if sys.platform.startswith("win"):
                    os.startfile(ruta)
                elif sys.platform == "darwin":
                    subprocess.call(["open", ruta])
                else:
                    subprocess.call(["xdg-open", ruta])
            except Exception as ex:
                messagebox.showerror("Error", f"No se pudo abrir el archivo:\n{ex}")

        def limpiar_form():
            _editando_id[0] = None
            _ruta_contrato[0] = ""
            entry_licencia.delete(0, "end")
            entry_version.delete(0, "end")
            entry_fecha.delete(0, "end")
            entry_cliente.delete(0, "end")
            lbl_doc.configure(text="Sin documento adjunto", text_color="#4A6FA5")
            lbl_st.configure(text="")
            lbl_form_titulo.configure(text="REGISTRAR LICENCIA")
            btn_guardar.configure(text="💾 REGISTRAR LICENCIA")
            btn_cancelar.pack_forget()

        btn_cancelar.configure(command=limpiar_form)

        def cargar_en_form(lid, licencia, version, fecha, cliente, ruta_c):
            _editando_id[0] = lid
            _ruta_contrato[0] = ruta_c or ""
            entry_licencia.delete(0, "end");  entry_licencia.insert(0, licencia or "")
            entry_version.delete(0, "end");   entry_version.insert(0, version or "")
            entry_fecha.delete(0, "end");     entry_fecha.insert(0, fecha or "")
            entry_cliente.delete(0, "end");   entry_cliente.insert(0, cliente or "")
            if ruta_c and os.path.exists(ruta_c):
                lbl_doc.configure(text=os.path.basename(ruta_c),
                                  text_color=col["principal"])
            else:
                lbl_doc.configure(text="Sin documento adjunto", text_color="#4A6FA5")
            lbl_form_titulo.configure(text="✏️ EDITANDO LICENCIA")
            btn_guardar.configure(text="✏️ ACTUALIZAR LICENCIA")
            btn_cancelar.pack(pady=(0, 10), padx=20)
            lbl_st.configure(text="")
            try:
                form._parent_canvas.yview_moveto(0)
            except Exception:
                pass

        def cargar_lista():
            for w in scroll.winfo_children():
                w.destroy()
            try:
                con = sqlite3.connect(DB_NAME)
                cur = con.cursor()
                cur.execute("""
                    SELECT id, licencia, version, fecha_licencia, cliente, ruta_contrato
                    FROM sistemas_licencias
                    WHERE modelo_id=?
                    ORDER BY id DESC
                """, (mid,))
                rows = cur.fetchall()
                con.close()
            except Exception:
                rows = []

            if not rows:
                ctk.CTkLabel(scroll, text="Sin licencias registradas.",
                             font=font, text_color="#4A6FA5").pack(pady=20)
                return

            headers = ["Licencia", "Versión", "Fecha", "Cliente", "Acciones"]
            widths   = [150, 70, 100, 130, 100]
            hdr_row = ctk.CTkFrame(scroll, fg_color="#0A192F")
            hdr_row.pack(fill="x", pady=(0, 4))
            for h, w in zip(headers, widths):
                ctk.CTkLabel(hdr_row, text=h,
                             font=(font[0], font[1], "bold"),
                             text_color=col["principal"],
                             width=w, anchor="w").pack(side="left", padx=4)

            for i, (lid, licencia, version, fecha, cliente, ruta_c) in enumerate(rows):
                bg = col["tarjetas"] if i % 2 == 0 else "#0A192F"
                fila = ctk.CTkFrame(scroll, fg_color=bg, corner_radius=4, height=34)
                fila.pack(fill="x", pady=2)
                fila.pack_propagate(False)

                # Botones a la derecha primero (100px: ✏️ + 🗑 + 📄)
                btn_frame = ctk.CTkFrame(fila, fg_color="transparent", width=100, height=34)
                btn_frame.pack(side="right", padx=2)
                btn_frame.pack_propagate(False)

                ctk.CTkButton(
                    btn_frame, text="🗑", width=30, height=28, font=font,
                    fg_color="transparent", hover_color=col["error"],
                    text_color=col["error"],
                    command=lambda i=lid: eliminar_licencia(i),
                ).pack(side="right", padx=1)

                ctk.CTkButton(
                    btn_frame, text="✏️", width=30, height=28, font=font,
                    fg_color="transparent", hover_color="#1A3550",
                    text_color=col["principal"],
                    command=lambda i=lid, l=licencia, v=version, f=fecha,
                                   c=cliente, r=ruta_c:
                        cargar_en_form(i, l, v, f, c, r),
                ).pack(side="right", padx=1)

                if ruta_c and os.path.exists(ruta_c):
                    ctk.CTkButton(
                        btn_frame, text="📄", width=30, height=28, font=font,
                        fg_color="transparent", hover_color="#1A3550",
                        text_color=col["principal"],
                        command=lambda r=ruta_c: abrir_contrato(r),
                    ).pack(side="right", padx=1)
                else:
                    ctk.CTkLabel(btn_frame, text="—", width=30, font=font,
                                 text_color="#4A6FA5").pack(side="right", padx=1)

                for val, w in zip([licencia, version or "—", fecha or "—",
                                   cliente or "—"], widths[:-1]):
                    ctk.CTkLabel(fila, text=str(val), font=font,
                                 text_color=col["texto_oscuro"],
                                 width=w, anchor="w").pack(side="left", padx=4, pady=2)

        def eliminar_licencia(lid):
            if not messagebox.askyesno("Confirmar", "¿Eliminar esta licencia?"):
                return
            if _editando_id[0] == lid:
                limpiar_form()
            try:
                con = sqlite3.connect(DB_NAME)
                cur = con.cursor()
                cur.execute("DELETE FROM sistemas_licencias WHERE id=?", (lid,))
                con.commit()
                con.close()
            except Exception:
                pass
            cargar_lista()

        def guardar_licencia():
            licencia = entry_licencia.get().strip()
            version  = entry_version.get().strip()
            fecha    = entry_fecha.get().strip()
            cliente  = entry_cliente.get().strip()

            if not licencia:
                lbl_st.configure(text="El número de licencia es obligatorio.",
                                 text_color=col["error"])
                return
            if not version:
                lbl_st.configure(text="La versión es obligatoria.",
                                 text_color=col["error"])
                return

            # Copiar contrato solo si es un archivo nuevo (no ya guardado)
            ruta_guardada = _ruta_contrato[0]
            ruta_src = _ruta_contrato[0]
            if ruta_src and os.path.exists(ruta_src) \
                    and not ruta_src.startswith("contratos"):
                carpeta = "contratos"
                os.makedirs(carpeta, exist_ok=True)
                import uuid as _uuid
                ext = os.path.splitext(ruta_src)[1]
                nombre_dest = (
                    f"contrato_{licencia.replace(' ','_')}"
                    f"_{_uuid.uuid4().hex[:6]}{ext}"
                )
                destino = os.path.join(carpeta, nombre_dest)
                try:
                    shutil.copy2(ruta_src, destino)
                    ruta_guardada = destino
                except Exception as e:
                    lbl_st.configure(text=f"⚠ No se pudo copiar el contrato: {e}",
                                     text_color=col["error"])
                    return

            try:
                con = sqlite3.connect(DB_NAME)
                cur = con.cursor()
                if _editando_id[0] is None:
                    cur.execute("""
                        INSERT INTO sistemas_licencias
                            (modelo_id, licencia, version, fecha_licencia,
                             cliente, ruta_contrato)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (mid, licencia, version, fecha or None,
                          cliente, ruta_guardada))
                    lbl_st.configure(text="✅ Licencia registrada. Abriendo homologación…",
                                     text_color=col["principal"])
                    self.after(400, lambda m=mid: imprimir_homologacion_al_registrar(m))
                else:
                    cur.execute("""
                        UPDATE sistemas_licencias
                        SET licencia=?, version=?, fecha_licencia=?,
                            cliente=?, ruta_contrato=?
                        WHERE id=?
                    """, (licencia, version, fecha or None,
                          cliente, ruta_guardada, _editando_id[0]))
                    lbl_st.configure(text="✅ Licencia actualizada.",
                                     text_color=col["principal"])
                con.commit()
                con.close()
                limpiar_form()
                cargar_lista()
            except sqlite3.IntegrityError:
                lbl_st.configure(text="Error: Licencia duplicada.",
                                 text_color=col["error"])
            except Exception as e:
                lbl_st.configure(text=f"Error: {e}", text_color=col["error"])

        btn_guardar.configure(command=guardar_licencia)
        cargar_lista()
