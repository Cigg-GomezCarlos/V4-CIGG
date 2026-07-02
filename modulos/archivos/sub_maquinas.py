"""
modulos/archivos/sub_maquinas.py
=================================
Submódulo de control de máquinas fiscales.

Flujo:
  Vista Modelos  →  [➕ Nuevo Modelo]  →  Formulario modal
  Tarjeta Modelo →  [📋 Ver/Registrar Unidades] → Vista Unidades
  Vista Unidades →  Formulario registro + tabla de unidades

Correcciones v2:
  - fabricante guardado como TEXT (no FK a tabla separada)
  - columna nombre_imagen usada consistentemente
  - ComboBox carga proveedores fiscales reales desde BD
  - Ruta de imagen corregida (self._ruta_img_seleccionada)
"""
import os
import shutil
import sqlite3
import tkinter.filedialog as fd
import customtkinter as ctk
from core.permisos import puede
from tkinter import messagebox
from PIL import Image
from core.database import DB_NAME, obtener_proveedores_fiscales
from modulos.documentos.sub_maquinas_docs import imprimir_docs_al_registrar


class SubmoduloMaquinas(ctk.CTkFrame):
    """Panel de modelos y unidades de máquinas fiscales."""

    def __init__(self, parent, estilos, permisos=None):
        super().__init__(parent, fg_color="transparent")
        self.estilos  = estilos
        self.permisos = permisos or {}
        self._puede_editar   = puede(self.permisos, "Archivos.Máquinas", "editar")
        self._puede_eliminar = puede(self.permisos, "Archivos.Máquinas", "eliminar")

        # ── Encabezado ────────────────────────────────────────────────────────
        self.header = ctk.CTkFrame(self, fg_color="transparent")
        self.header.pack(fill="x", padx=10, pady=(5, 10))

        self.lbl_titulo = ctk.CTkLabel(
            self.header,
            text="🛠️ PANEL DE MODELOS Y HARDWARE FISCAL",
            font=estilos["fuentes"]["subtitulo"],
            text_color=estilos["colores"]["texto_oscuro"],
        )
        self.lbl_titulo.pack(side="left")

        self.btn_nuevo_modelo = ctk.CTkButton(
            self.header, text="➕ Nuevo Modelo",
            font=estilos["fuentes"]["normal"],
            fg_color=estilos["colores"]["principal"],
            hover_color=estilos["colores"]["principal_hover"],
            text_color="#0A192F", width=150, height=34,
            command=self._abrir_ventana_crear_modelo,
        )
        if self._puede_editar:
            self.btn_nuevo_modelo.pack(side="right")

        # ── Área de contenido (se intercambia entre vistas) ───────────────────
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
        self.lbl_titulo.configure(text="🛠️ PANEL DE MODELOS Y HARDWARE FISCAL")
        self.btn_nuevo_modelo.pack(side="right")

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
                SELECT id, nombre, fabricante, nombre_imagen
                FROM modelos_maquinas
                ORDER BY nombre ASC
            """)
            modelos = cur.fetchall()
            con.close()
        except Exception:
            modelos = []

        if not modelos:
            ctk.CTkLabel(
                self._grid_frame,
                text="No hay modelos registrados.\nPresiona  ➕ Nuevo Modelo  para comenzar.",
                font=self.estilos["fuentes"]["normal"],
                text_color="#4A6FA5",
            ).grid(row=0, column=0, columnspan=3, pady=60)
            return

        for idx, (mid, nombre, fabricante, img_nombre) in enumerate(modelos):
            fila, col_idx = divmod(idx, 3)
            self._crear_tarjeta(mid, nombre, fabricante, img_nombre, fila, col_idx)

    def _crear_tarjeta(self, mid, nombre, fabricante, img_nombre, fila, col_idx):
        col = self.estilos["colores"]
        card = ctk.CTkFrame(
            self._grid_frame, fg_color=col["tarjetas"],
            corner_radius=12, border_width=1, border_color="#1A3550",
        )
        card.grid(row=fila, column=col_idx, padx=15, pady=15, sticky="nsew")

        # Imagen del modelo
        ruta_img = os.path.join("imagenes", img_nombre) if img_nombre else ""
        if ruta_img and os.path.exists(ruta_img):
            try:
                img_obj = ctk.CTkImage(
                    light_image=Image.open(ruta_img),
                    dark_image=Image.open(ruta_img), size=(120, 100),
                )
                lbl_img = ctk.CTkLabel(card, image=img_obj, text="")
                lbl_img.pack(pady=(15, 5))
                lbl_img._img_ref = img_obj   # evitar garbage collection
            except Exception:
                ctk.CTkLabel(card, text="📷 Error",
                             font=self.estilos["fuentes"]["normal"],
                             text_color=col["error"]).pack(pady=20)
        else:
            ctk.CTkLabel(card, text="📦 Sin Imagen",
                         font=self.estilos["fuentes"]["normal"],
                         text_color="#4A6FA5").pack(pady=25)

        ctk.CTkLabel(card, text=nombre,
                     font=self.estilos["fuentes"]["subtitulo"],
                     text_color=col["texto_oscuro"]).pack()
        ctk.CTkLabel(card, text=f"Fabricante: {fabricante or '—'}",
                     font=self.estilos["fuentes"]["normal"],
                     text_color=col["principal"]).pack(pady=(0, 6))

        # Contador de unidades
        try:
            con = sqlite3.connect(DB_NAME)
            cur = con.cursor()
            cur.execute("SELECT COUNT(*) FROM maquinas_fiscales WHERE modelo_id=?", (mid,))
            total = cur.fetchone()[0]
            con.close()
        except Exception:
            total = 0
        ctk.CTkLabel(card, text=f"Unidades: {total}",
                     font=self.estilos["fuentes"]["normal"],
                     text_color="#4A6FA5").pack(pady=(0, 8))

        ctk.CTkButton(
            card, text="📋 Ver / Registrar Unidades",
            font=self.estilos["fuentes"]["normal"],
            fg_color="#1A3550", hover_color=col["principal_hover"],
            text_color=col["texto_oscuro"],
            command=lambda i=mid, n=nombre, f=fabricante: self._mostrar_vista_unidades(i, n, f),
        ).pack(fill="x", padx=15, pady=(0, 5))

        if self._puede_eliminar:
            ctk.CTkButton(
                card, text="🗑️ Eliminar Modelo",
                font=self.estilos["fuentes"]["normal"],
                fg_color=col["error"], hover_color="#8B1E1E",
                command=lambda i=mid: self._eliminar_modelo(i),
            ).pack(fill="x", padx=15, pady=(0, 15))

    def _eliminar_modelo(self, mid):
        try:
            con = sqlite3.connect(DB_NAME)
            cur = con.cursor()
            cur.execute("PRAGMA foreign_keys = ON")
            cur.execute("DELETE FROM modelos_maquinas WHERE id=?", (mid,))
            con.commit()
            con.close()
        except Exception:
            pass
        self._refrescar_cuadricula()

    # ─────────────────────────────────────────────────────────────────────────
    # VENTANA MODAL: CREAR MODELO
    # ─────────────────────────────────────────────────────────────────────────

    def _abrir_ventana_crear_modelo(self):
        col  = self.estilos["colores"]
        font = self.estilos["fuentes"]["normal"]

        ventana = ctk.CTkToplevel(self)
        ventana.title("Nuevo Modelo de Máquina")
        ventana.geometry("480x500")
        ventana.resizable(False, False)
        ventana.configure(fg_color=col["fondo_oscuro"])
        ventana.grab_set()
        ventana.lift()

        ctk.CTkLabel(ventana, text="➕ REGISTRAR NUEVO MODELO",
                     font=self.estilos["fuentes"]["subtitulo"],
                     text_color=col["principal"]).pack(pady=(25, 10))

        # Nombre del modelo
        ctk.CTkLabel(ventana, text="Nombre del modelo:", font=font,
                     text_color=col["texto_oscuro"]).pack(anchor="w", padx=40)
        entry_nombre = ctk.CTkEntry(ventana, width=400, font=font,
                                    border_color=col["principal"])
        entry_nombre.pack(padx=40, pady=(4, 16))

        # Fabricante (cargado desde proveedores fiscales)
        ctk.CTkLabel(ventana, text="Fabricante (proveedor tipo Máquinas Fiscales):",
                     font=font, text_color=col["texto_oscuro"]).pack(anchor="w", padx=40)

        fabricantes = obtener_proveedores_fiscales()
        if fabricantes:
            valores_fab = fabricantes
        else:
            valores_fab = ["⚠ Registre un proveedor de Máquinas Fiscales"]

        cmb_fab = ctk.CTkComboBox(ventana, values=valores_fab,
                                   width=400, height=34,
                                   dropdown_fg_color="#1A3550")
        cmb_fab.set(valores_fab[0])
        cmb_fab.pack(padx=40, pady=(4, 16))

        # Imagen opcional
        self._ruta_img_seleccionada = ""
        ctk.CTkLabel(ventana, text="Imagen del modelo (opcional):",
                     font=font, text_color=col["texto_oscuro"]).pack(anchor="w", padx=40)

        frame_img = ctk.CTkFrame(ventana, fg_color="transparent")
        frame_img.pack(fill="x", padx=40, pady=(4, 16))

        lbl_img = ctk.CTkLabel(frame_img, text="Sin imagen seleccionada",
                               font=font, text_color="#4A6FA5")
        lbl_img.pack(side="left", fill="x", expand=True)

        def seleccionar_imagen():
            ruta = fd.askopenfilename(
                title="Selecciona imagen del modelo",
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
            fabricante = cmb_fab.get()

            if not nombre:
                lbl_status.configure(text="⚠ El nombre del modelo es obligatorio.")
                return
            if "⚠" in fabricante:
                lbl_status.configure(text="⚠ Selecciona un fabricante válido.")
                return

            # Copiar imagen a la carpeta imagenes/
            nombre_img = ""
            if self._ruta_img_seleccionada and os.path.exists(self._ruta_img_seleccionada):
                nombre_img = os.path.basename(self._ruta_img_seleccionada)
                destino = os.path.join("imagenes", nombre_img)
                try:
                    if not os.path.exists(destino):
                        shutil.copy2(self._ruta_img_seleccionada, destino)
                except Exception:
                    pass  # La imagen es opcional, continuar si falla

            try:
                con = sqlite3.connect(DB_NAME)
                cur = con.cursor()
                cur.execute("""
                    INSERT INTO modelos_maquinas (nombre, fabricante, nombre_imagen)
                    VALUES (?, ?, ?)
                """, (nombre, fabricante, nombre_img))
                con.commit()
                con.close()
                ventana.destroy()
                self._refrescar_cuadricula()
            except sqlite3.IntegrityError:
                lbl_status.configure(text="⚠ Ya existe un modelo con ese nombre.")
            except Exception as e:
                lbl_status.configure(text=f"Error: {e}")

        ctk.CTkButton(
            ventana, text="💾 GUARDAR MODELO",
            font=font, width=400, height=42,
            fg_color=col["principal"], hover_color=col["principal_hover"],
            text_color="#0A192F", command=guardar,
        ).pack(pady=10, padx=40)

    # ─────────────────────────────────────────────────────────────────────────
    # HELPERS
    # ─────────────────────────────────────────────────────────────────────────

    def _obtener_clientes_lista(self) -> list[str]:
        """Retorna nombres/razón social de clientes (legado, no usado en UI)."""
        try:
            con = sqlite3.connect(DB_NAME)
            cur = con.cursor()
            cur.execute("SELECT razon_social FROM clientes ORDER BY razon_social ASC")
            rows = [r[0] for r in cur.fetchall()]
            con.close()
        except Exception:
            rows = []
        return ["DISPONIBLE EN STOCK"] + rows

    # ─────────────────────────────────────────────────────────────────────────
    # VISTA UNIDADES
    # ─────────────────────────────────────────────────────────────────────────

    def _mostrar_vista_unidades(self, mid, nombre_mod, fabricante):
        self._limpiar_contenido()
        self.lbl_titulo.configure(text=f"📋 Unidades › {nombre_mod}")
        self.btn_nuevo_modelo.pack_forget()

        col  = self.estilos["colores"]
        font = self.estilos["fuentes"]["normal"]
        fnt  = self.estilos["fuentes"]

        # Botón volver
        barra = ctk.CTkFrame(self.area_contenido, fg_color="transparent")
        barra.pack(fill="x", pady=(0, 8))
        ctk.CTkButton(
            barra, text="← Volver a Modelos", font=font,
            fg_color="#1A3550", hover_color=col["principal_hover"],
            text_color=col["texto_oscuro"], width=170, height=32,
            command=self._mostrar_vista_modelos,
        ).pack(side="left")

        # Layout: formulario izquierda | lista derecha
        layout = ctk.CTkFrame(self.area_contenido, fg_color="transparent")
        layout.pack(fill="both", expand=True)
        layout.columnconfigure(0, weight=1)
        layout.columnconfigure(1, weight=2)
        layout.rowconfigure(0, weight=1)

        # ── Formulario ────────────────────────────────────────────────────────
        form = ctk.CTkFrame(layout, fg_color="#020C1B", corner_radius=8)
        form.grid(row=0, column=0, padx=(0, 8), pady=0, sticky="nsew")

        ctk.CTkLabel(form, text="REGISTRAR UNIDAD",
                     font=fnt["subtitulo"],
                     text_color=col["principal"]).pack(pady=(20, 10), padx=15)

        # Campos básicos
        campos = [
            ("Número de Registro:", "Ej: 00123456"),
            ("Serial Único:",       "Ej: SN-20260001"),
            ("Firmware:",           "Ej: v3.2.1"),
        ]
        entries = []
        for label, ph in campos:
            ctk.CTkLabel(form, text=label, font=font,
                         text_color=col["texto_oscuro"]).pack(anchor="w", padx=20)
            e = ctk.CTkEntry(form, placeholder_text=ph, width=270,
                             font=font, border_color=col["principal"])
            e.pack(pady=(4, 12), padx=20)
            entries.append(e)

        entry_reg, entry_serial, entry_firmware = entries

        # ── Cliente con autocomplete ──────────────────────────────────────────
        ctk.CTkLabel(form, text="Cliente:", font=font,
                     text_color=col["texto_oscuro"]).pack(anchor="w", padx=20)
        try:
            _con_c = sqlite3.connect(DB_NAME)
            _cur_c = _con_c.cursor()
            _cur_c.execute("SELECT razon_social FROM clientes ORDER BY razon_social ASC")
            _todos_clientes = ["DISPONIBLE EN STOCK"] + [r[0] for r in _cur_c.fetchall()]
            _con_c.close()
        except Exception:
            _todos_clientes = ["DISPONIBLE EN STOCK"]

        _dropdown_top = [None]

        entry_cliente = ctk.CTkEntry(
            form, placeholder_text="Escribe para buscar cliente…",
            width=270, font=font, border_color=col["principal"],
        )
        entry_cliente.pack(pady=(4, 12), padx=20)

        def _cerrar_dropdown_form(event=None):
            if _dropdown_top[0] and _dropdown_top[0].winfo_exists():
                _dropdown_top[0].destroy()
            _dropdown_top[0] = None

        def _seleccionar_cliente_form(nombre):
            entry_cliente.delete(0, "end")
            entry_cliente.insert(0, nombre)
            _cerrar_dropdown_form()

        def _actualizar_dropdown_form(event=None):
            _cerrar_dropdown_form()
            texto = entry_cliente.get().strip().lower()
            coincidencias = [c for c in _todos_clientes
                             if not texto or texto in c.lower()]
            if not coincidencias:
                return
            entry_cliente.update_idletasks()
            x = entry_cliente.winfo_rootx()
            y = entry_cliente.winfo_rooty() + entry_cliente.winfo_height()
            w = entry_cliente.winfo_width()
            h = min(len(coincidencias) * 32, 200)
            top = ctk.CTkToplevel()
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
                    command=lambda n=nombre: _seleccionar_cliente_form(n),
                ).pack(fill="x", padx=2, pady=1)

        entry_cliente.bind("<KeyRelease>", _actualizar_dropdown_form)
        entry_cliente.bind("<FocusIn>",   _actualizar_dropdown_form)
        entry_cliente.bind("<FocusOut>",  lambda e: form.after(200, _cerrar_dropdown_form))

        lbl_st = ctk.CTkLabel(form, text="", font=font, text_color=col["error"])
        lbl_st.pack(pady=4)

        # ── Panel derecho ─────────────────────────────────────────────────────
        panel = ctk.CTkFrame(layout, fg_color="#020C1B", corner_radius=8)
        panel.grid(row=0, column=1, pady=0, sticky="nsew")
        panel.rowconfigure(2, weight=1)
        panel.columnconfigure(0, weight=1)

        ctk.CTkLabel(panel, text=f"UNIDADES — {nombre_mod.upper()}",
                     font=fnt["subtitulo"],
                     text_color=col["texto_oscuro"]).grid(row=0, column=0,
                     pady=(20, 8), padx=15, sticky="w")

        # ── Barra de filtro ───────────────────────────────────────────────────
        barra_filtro = ctk.CTkFrame(panel, fg_color="transparent")
        barra_filtro.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 6))
        barra_filtro.columnconfigure(0, weight=1)

        entry_filtro = ctk.CTkEntry(
            barra_filtro,
            placeholder_text="🔍  Filtrar por Registro, Serial o Cliente...",
            font=font, border_color=col["principal"], height=32,
        )
        entry_filtro.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ctk.CTkButton(
            barra_filtro, text="✕", width=32, height=32, font=font,
            fg_color="#1A3550", hover_color=col["error"],
            text_color=col["texto_oscuro"],
            command=lambda: (entry_filtro.delete(0, "end"), cargar_lista()),
        ).grid(row=0, column=1)

        # ── Scroll de unidades ────────────────────────────────────────────────
        scroll = ctk.CTkScrollableFrame(panel, fg_color="transparent")
        scroll.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 10))

        entry_filtro.bind("<KeyRelease>", lambda e: cargar_lista())

        # ─────────────────────────────────────────────────────────────────────
        def cargar_lista():
            for w in scroll.winfo_children():
                w.destroy()

            filtro = entry_filtro.get().strip().lower()

            try:
                con = sqlite3.connect(DB_NAME)
                cur = con.cursor()
                cur.execute("""
                    SELECT id, numero_registro, numero_serial, firmware, cliente
                    FROM maquinas_fiscales
                    WHERE modelo_id=?
                    ORDER BY id DESC
                """, (mid,))
                rows = cur.fetchall()
                con.close()
            except Exception:
                rows = []

            if filtro:
                rows = [r for r in rows if
                        filtro in (r[1] or "").lower() or
                        filtro in (r[2] or "").lower() or
                        filtro in (r[4] or "").lower()]

            if not rows:
                ctk.CTkLabel(scroll,
                             text="Sin unidades registradas." if not filtro
                                  else "Sin resultados para el filtro.",
                             font=font, text_color="#4A6FA5").pack(pady=20)
                return

            headers = ["Registro", "Serial", "Firmware", "Cliente"]
            widths  = [110, 130, 90, 170]
            hdr_row = ctk.CTkFrame(scroll, fg_color="#0A192F")
            hdr_row.pack(fill="x", pady=(0, 4))
            for h, w in zip(headers, widths):
                ctk.CTkLabel(hdr_row, text=h,
                             font=(font[0], font[1], "bold"),
                             text_color=col["principal"], width=w, anchor="w").pack(side="left", padx=4)
            ctk.CTkLabel(hdr_row, text="", width=72).pack(side="left")

            for i, (uid, reg, serial, firm, cliente) in enumerate(rows):
                bg = col["tarjetas"] if i % 2 == 0 else "#0A192F"
                fila = ctk.CTkFrame(scroll, fg_color=bg, corner_radius=4)
                fila.pack(fill="x", pady=2)

                btn_frame = ctk.CTkFrame(fila, fg_color="transparent", width=76, height=34)
                btn_frame.pack(side="right", padx=4, pady=0)
                btn_frame.pack_propagate(False)

                if self._puede_eliminar:
                    ctk.CTkButton(
                        btn_frame, text="🗑", width=34, height=28, font=font,
                        fg_color="#1A3550", hover_color=col["error"],
                        text_color=col["error"],
                        command=lambda r=reg: eliminar_unidad(r),
                    ).pack(side="right", padx=(2, 0))
                if self._puede_editar:
                    ctk.CTkButton(
                        btn_frame, text="✏️", width=34, height=28, font=font,
                        fg_color="#1A3550", hover_color=col["principal_hover"],
                        text_color=col["principal"],
                        command=lambda u=uid, r=reg, s=serial, fw=firm, cl=cliente:
                                _abrir_modal_editar(u, r, s, fw, cl),
                    ).pack(side="right", padx=(2, 0))

                for val, w in zip([reg, serial, firm, cliente or "—"], widths):
                    ctk.CTkLabel(fila, text=str(val), font=font,
                                 text_color=col["texto_oscuro"],
                                 width=w, anchor="w").pack(side="left", padx=4, pady=2)

        # ─────────────────────────────────────────────────────────────────────
        def eliminar_unidad(numero_reg):
            if not messagebox.askyesno("Confirmar",
                    f"¿Eliminar la unidad con registro {numero_reg}?"):
                return
            try:
                con = sqlite3.connect(DB_NAME)
                cur = con.cursor()
                cur.execute("DELETE FROM maquinas_fiscales WHERE numero_registro=?", (numero_reg,))
                con.commit()
                con.close()
            except Exception:
                pass
            cargar_lista()

        # ─────────────────────────────────────────────────────────────────────
        def _abrir_modal_editar(uid, reg, serial, firm, cliente):
            col2 = self.estilos["colores"]

            modal = ctk.CTkToplevel(self)
            modal.title("Editar Unidad")
            modal.geometry("460x480")
            modal.resizable(False, False)
            modal.configure(fg_color=col2["fondo_oscuro"])
            modal.grab_set()
            modal.lift()

            ctk.CTkLabel(modal, text="✏️ EDITAR UNIDAD",
                         font=fnt["subtitulo"],
                         text_color=col2["principal"]).pack(pady=(25, 12))

            campos_edit = [
                ("Número de Registro:", reg),
                ("Serial Único:",       serial),
                ("Firmware:",           firm or ""),
            ]
            entries_edit = []
            for lbl_txt, val in campos_edit:
                ctk.CTkLabel(modal, text=lbl_txt, font=font,
                             text_color=col2["texto_oscuro"]).pack(anchor="w", padx=40)
                e = ctk.CTkEntry(modal, width=380, font=font,
                                  border_color=col2["principal"])
                e.insert(0, val or "")
                e.pack(pady=(4, 10), padx=40)
                entries_edit.append(e)

            e_reg2, e_serial2, e_firm2 = entries_edit

            # ── Cliente autocomplete en modal ─────────────────────────────────
            ctk.CTkLabel(modal, text="Cliente:", font=font,
                         text_color=col2["texto_oscuro"]).pack(anchor="w", padx=40)
            try:
                _con_e = sqlite3.connect(DB_NAME)
                _cur_e = _con_e.cursor()
                _cur_e.execute("SELECT razon_social FROM clientes ORDER BY razon_social ASC")
                _clientes_edit = ["DISPONIBLE EN STOCK"] + [r[0] for r in _cur_e.fetchall()]
                _con_e.close()
            except Exception:
                _clientes_edit = ["DISPONIBLE EN STOCK"]

            _drop_edit = [None]

            entry_edit_cli = ctk.CTkEntry(
                modal, placeholder_text="Escribe para buscar cliente…",
                width=380, font=font, border_color=col2["principal"],
            )
            entry_edit_cli.insert(0, cliente if cliente else "")
            entry_edit_cli.pack(pady=(4, 10), padx=40)

            def _cerrar_drop_edit(event=None):
                if _drop_edit[0] and _drop_edit[0].winfo_exists():
                    _drop_edit[0].destroy()
                _drop_edit[0] = None

            def _sel_edit(nombre):
                entry_edit_cli.delete(0, "end")
                entry_edit_cli.insert(0, nombre)
                _cerrar_drop_edit()

            def _act_drop_edit(event=None):
                _cerrar_drop_edit()
                texto = entry_edit_cli.get().strip().lower()
                coincidencias = [c for c in _clientes_edit
                                 if not texto or texto in c.lower()]
                if not coincidencias:
                    return
                entry_edit_cli.update_idletasks()
                x = entry_edit_cli.winfo_rootx()
                y = entry_edit_cli.winfo_rooty() + entry_edit_cli.winfo_height()
                w = entry_edit_cli.winfo_width()
                h = min(len(coincidencias) * 32, 200)
                top2 = ctk.CTkToplevel()
                top2.overrideredirect(True)
                top2.geometry(f"{w}x{h}+{x}+{y}")
                top2.configure(fg_color="#1A3550")
                top2.attributes("-topmost", True)
                top2.lift()
                _drop_edit[0] = top2
                scr2 = ctk.CTkScrollableFrame(top2, fg_color="#1A3550", corner_radius=0)
                scr2.pack(fill="both", expand=True)
                for nombre in coincidencias:
                    ctk.CTkButton(
                        scr2, text=nombre, font=font,
                        fg_color="transparent", hover_color=col2["principal_hover"],
                        text_color=col2["texto_oscuro"], anchor="w", height=30,
                        command=lambda n=nombre: _sel_edit(n),
                    ).pack(fill="x", padx=2, pady=1)

            entry_edit_cli.bind("<KeyRelease>", _act_drop_edit)
            entry_edit_cli.bind("<FocusIn>",   _act_drop_edit)
            entry_edit_cli.bind("<FocusOut>",  lambda e: modal.after(200, _cerrar_drop_edit))

            lbl_err = ctk.CTkLabel(modal, text="", font=font, text_color=col2["error"])
            lbl_err.pack(pady=4)

            def guardar_edicion():
                nuevo_reg    = e_reg2.get().strip()
                nuevo_serial = e_serial2.get().strip()
                nuevo_firm   = e_firm2.get().strip()
                nuevo_cli    = entry_edit_cli.get().strip()

                if not nuevo_reg or not nuevo_serial or not nuevo_firm:
                    lbl_err.configure(text="⚠ Registro, Serial y Firmware son obligatorios.")
                    return
                try:
                    con = sqlite3.connect(DB_NAME)
                    cur = con.cursor()
                    cur.execute("""
                        UPDATE maquinas_fiscales
                        SET numero_registro=?, numero_serial=?, firmware=?, cliente=?
                        WHERE id=?
                    """, (nuevo_reg, nuevo_serial, nuevo_firm, nuevo_cli, uid))
                    con.commit()
                    con.close()
                    modal.destroy()
                    cargar_lista()
                except sqlite3.IntegrityError:
                    lbl_err.configure(text="⚠ Registro o Serial ya existe en otra unidad.")
                except Exception as ex:
                    lbl_err.configure(text=f"Error: {ex}")

            ctk.CTkButton(
                modal, text="💾 GUARDAR CAMBIOS", font=font,
                width=380, height=42,
                fg_color=col2["principal"], hover_color=col2["principal_hover"],
                text_color="#0A192F", command=guardar_edicion,
            ).pack(pady=8, padx=40)

        # ─────────────────────────────────────────────────────────────────────
        def guardar_unidad():
            reg    = entry_reg.get().strip()
            serial = entry_serial.get().strip()
            firm   = entry_firmware.get().strip()
            cli    = entry_cliente.get().strip()

            if not reg or not serial:
                lbl_st.configure(text="Registro y Serial son obligatorios.", text_color=col["error"])
                return
            if not firm:
                lbl_st.configure(text="Firmware es obligatorio.", text_color=col["error"])
                return

            try:
                con = sqlite3.connect(DB_NAME)
                cur = con.cursor()
                cur.execute("""
                    INSERT INTO maquinas_fiscales
                        (modelo_id, numero_registro, numero_serial, firmware, cliente)
                    VALUES (?,?,?,?,?)
                """, (mid, reg, serial, firm, cli))
                con.commit()
                con.close()
                lbl_st.configure(text="✅ Unidad registrada. Abriendo documentos…", text_color=col["principal"])
                for e in entries:
                    e.delete(0, "end")
                entry_cliente.delete(0, "end")
                cargar_lista()
                self.after(300, lambda: imprimir_docs_al_registrar(
                    mid, nombre_mod, reg, serial, firm, cli))
            except sqlite3.IntegrityError:
                lbl_st.configure(text="Error: Registro o Serial duplicados.", text_color=col["error"])
            except Exception as e:
                lbl_st.configure(text=f"Error: {e}", text_color=col["error"])

        ctk.CTkButton(
            form, text="💾 REGISTRAR UNIDAD", font=font, width=270, height=40,
            fg_color=col["principal"], hover_color=col["principal_hover"],
            text_color="#0A192F", command=guardar_unidad,
        ).pack(pady=10, padx=20)

        cargar_lista()
