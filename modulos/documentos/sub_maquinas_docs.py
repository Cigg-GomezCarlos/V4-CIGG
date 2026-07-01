"""
modulos/documentos/sub_maquinas_docs.py
========================================
Submódulo Documentos › Máquinas
  - Panel izquierdo: lista de modelos de máquinas fiscales
  - Panel derecho:
      · Cartas de Enajenación — adjuntar / ver / eliminar
      · Carta de Entrega      — template editable con placeholders;
                                botón "Generar" para previsualizar con datos
                                reales de una unidad seleccionada
"""

import os
import shutil
import uuid
import subprocess
import sys
import tempfile
import datetime
import customtkinter as ctk
from tkinter import filedialog, messagebox

from core.database import (
    listar_modelos_maquinas,
    listar_maquinas_por_modelo,
    listar_enajenacion,
    agregar_enajenacion,
    eliminar_enajenacion,
    obtener_carta_entrega,
    guardar_carta_entrega,
)

DOCS_DIR_ENAJ = os.path.join(
    os.path.dirname(__file__), "..", "..", "documentos", "enajenacion")

PLANTILLA_DEFAULT = """\
CARTA DE ENTREGA DE MÁQUINA FISCAL
====================================

Caracas, {fecha}

Por medio de la presente, se hace entrega formal de la siguiente máquina fiscal:

  Modelo       : {modelo}
  Nro. Registro: {registro}
  Nro. Serial  : {serial}
  Firmware     : {firmware}
  Cliente      : {cliente}

La unidad se entrega en óptimas condiciones de funcionamiento, cumpliendo con
los requisitos establecidos por el SENIAT.

____________________________
Firma del Responsable

____________________________
Firma del Cliente
"""


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


class SubmoduloMaquinasDocs(ctk.CTkFrame):

    def __init__(self, parent, estilos):
        super().__init__(parent, corner_radius=0, fg_color="transparent")
        self.estilos  = estilos
        self.col      = estilos["colores"]
        self._modelo_id  = None
        self._modelo_nom = ""

        os.makedirs(DOCS_DIR_ENAJ, exist_ok=True)
        self._construir_ui()

    # ─── Layout ────────────────────────────────────────────────────────────────
    def _construir_ui(self):
        col = self.col

        # Panel izquierdo
        self._panel_izq = ctk.CTkFrame(self, width=200, corner_radius=8,
                                        fg_color=col["tarjetas"])
        self._panel_izq.pack(side="left", fill="y", padx=(0, 8))
        self._panel_izq.pack_propagate(False)

        ctk.CTkLabel(self._panel_izq, text="🖨 Máquinas",
                     font=self.estilos["fuentes"]["subtitulo"],
                     text_color=col["principal"]).pack(pady=(12, 6), padx=8)

        self._lista_modelos = ctk.CTkScrollableFrame(
            self._panel_izq, fg_color="transparent", corner_radius=0)
        self._lista_modelos.pack(fill="both", expand=True, padx=4, pady=4)

        ctk.CTkButton(self._panel_izq, text="🔄 Actualizar",
                      height=30, fg_color=col["principal"],
                      hover_color=col["principal_hover"],
                                text_color="#0A192F",
                      command=self._cargar_modelos).pack(pady=6, padx=8, fill="x")

        # Panel derecho
        self._panel_der = ctk.CTkFrame(self, corner_radius=8,
                                        fg_color=col["tarjetas"])
        self._panel_der.pack(side="left", fill="both", expand=True)

        self._placeholder()
        self._cargar_modelos()

    def _placeholder(self):
        for w in self._panel_der.winfo_children():
            w.destroy()
        ctk.CTkLabel(self._panel_der,
                     text="← Selecciona un modelo de máquina",
                     font=self.estilos["fuentes"]["normal"],
                     text_color="#5A7BAF").pack(expand=True)

    # ─── Modelos ───────────────────────────────────────────────────────────────
    def _cargar_modelos(self):
        for w in self._lista_modelos.winfo_children():
            w.destroy()
        modelos = listar_modelos_maquinas()
        if not modelos:
            ctk.CTkLabel(self._lista_modelos, text="Sin registros",
                         text_color="#5A7BAF",
                         font=self.estilos["fuentes"]["normal"]).pack(pady=10)
            return
        for mid, nombre in modelos:
            ctk.CTkButton(
                self._lista_modelos,
                text=nombre,
                fg_color="transparent",
                text_color=self.col["texto_oscuro"],
                hover_color=self.col["principal"],
                anchor="w", height=34,
                command=lambda i=mid, n=nombre: self._seleccionar_modelo(i, n),
            ).pack(fill="x", pady=2)

    def _seleccionar_modelo(self, modelo_id, nombre):
        self._modelo_id  = modelo_id
        self._modelo_nom = nombre
        self._mostrar_contenido()

    # ─── Panel derecho ─────────────────────────────────────────────────────────
    def _mostrar_contenido(self):
        for w in self._panel_der.winfo_children():
            w.destroy()
        col = self.col

        ctk.CTkLabel(self._panel_der,
                     text=f"🖨 {self._modelo_nom}",
                     font=self.estilos["fuentes"]["subtitulo"],
                     text_color=col["principal"]).pack(pady=(14, 4), padx=16, anchor="w")

        # Scrollable para que quepan las dos secciones
        scroll = ctk.CTkScrollableFrame(self._panel_der, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=8, pady=4)

        # ── Cartas de Enajenación ──────────────────────────────────────────────
        sec_enaj = ctk.CTkFrame(scroll, corner_radius=8,
                                fg_color=col["fondo_oscuro"])
        sec_enaj.pack(fill="x", pady=(0, 8))

        hdr = ctk.CTkFrame(sec_enaj, fg_color="transparent", height=36)
        hdr.pack(fill="x", padx=10, pady=(8, 2))
        hdr.pack_propagate(False)

        ctk.CTkLabel(hdr, text="📑 Cartas de Enajenación",
                     font=self.estilos["fuentes"]["subtitulo"],
                     text_color=col["texto_claro"]).pack(side="left")
        ctk.CTkButton(hdr, text="➕ Adjuntar",
                      width=110, height=28,
                      fg_color=col["principal"],
                      hover_color=col["principal_hover"],
                                text_color="#0A192F",
                      command=self._adjuntar_enajenacion).pack(side="right")

        self._frame_enaj = ctk.CTkScrollableFrame(
            sec_enaj, fg_color="transparent", height=140)
        self._frame_enaj.pack(fill="x", padx=8, pady=4)
        self._cargar_enajenaciones()

        # ── Carta de Entrega ───────────────────────────────────────────────────
        sec_carta = ctk.CTkFrame(scroll, corner_radius=8,
                                 fg_color=col["fondo_oscuro"])
        sec_carta.pack(fill="x", pady=(0, 8))

        hdr2 = ctk.CTkFrame(sec_carta, fg_color="transparent", height=36)
        hdr2.pack(fill="x", padx=10, pady=(8, 2))
        hdr2.pack_propagate(False)

        ctk.CTkLabel(hdr2, text="📝 Carta de Entrega (Template)",
                     font=self.estilos["fuentes"]["subtitulo"],
                     text_color=col["texto_claro"]).pack(side="left")

        ctk.CTkLabel(sec_carta,
                     text="Placeholders: {modelo} {registro} {serial} "
                          "{firmware} {cliente} {fecha}",
                     font=("Roboto Mono", 10),
                     text_color="#5A7BAF").pack(anchor="w", padx=10)

        self._txt_carta = ctk.CTkTextbox(sec_carta, height=220,
                                         font=("Roboto Mono", 11),
                                         fg_color=col["tarjetas"],
                                         text_color=col["texto_oscuro"])
        self._txt_carta.pack(fill="x", padx=10, pady=4)

        # Cargar template guardado (o plantilla default)
        contenido_guardado = obtener_carta_entrega(self._modelo_id)
        self._txt_carta.delete("1.0", "end")
        self._txt_carta.insert("1.0", contenido_guardado or PLANTILLA_DEFAULT)

        # Botones
        btn_row = ctk.CTkFrame(sec_carta, fg_color="transparent")
        btn_row.pack(fill="x", padx=10, pady=(0, 10))

        ctk.CTkButton(btn_row, text="💾 Guardar Template",
                      width=160, height=30,
                      fg_color=col["principal"],
                      hover_color=col["principal_hover"],
                                text_color="#0A192F",
                      command=self._guardar_template).pack(side="left", padx=(0, 8))

        # Selector de unidad para generar
        unidades = listar_maquinas_por_modelo(self._modelo_id)
        opciones = [f"{u[1]} | {u[2]}" for u in unidades]  # registro | serial

        self._unidad_data = {f"{u[1]} | {u[2]}": u for u in unidades}

        if opciones:
            self._combo_unidad = ctk.CTkComboBox(btn_row, values=opciones, width=220,
                                                  fg_color=col["tarjetas"],
                                                  button_color=col["principal"],
                                                  state="readonly")
            self._combo_unidad.pack(side="left", padx=(0, 6))
            self._combo_unidad.set(opciones[0])

            ctk.CTkButton(btn_row, text="🖨 Generar / Vista previa",
                          width=180, height=30,
                          fg_color="#1A6B3C",
                          hover_color="#145530",
                          command=self._generar_carta).pack(side="left")
        else:
            ctk.CTkLabel(btn_row, text="(Sin unidades registradas para este modelo)",
                         text_color="#5A7BAF",
                         font=self.estilos["fuentes"]["normal"]).pack(side="left")

    # ─── Enajenación ───────────────────────────────────────────────────────────
    def _cargar_enajenaciones(self):
        for w in self._frame_enaj.winfo_children():
            w.destroy()
        col = self.col
        docs = listar_enajenacion(self._modelo_id)

        if not docs:
            ctk.CTkLabel(self._frame_enaj, text="Sin cartas de enajenación adjuntas",
                         text_color="#5A7BAF",
                         font=self.estilos["fuentes"]["normal"]).pack(pady=6)
            return

        for doc_id, nombre, ruta, fecha in docs:
            fila = ctk.CTkFrame(self._frame_enaj, fg_color=col["tarjetas"],
                                corner_radius=6, height=34)
            fila.pack(fill="x", pady=2)
            fila.pack_propagate(False)

            btn_f = ctk.CTkFrame(fila, fg_color="transparent", width=76)
            btn_f.pack(side="right", fill="y")
            btn_f.pack_propagate(False)

            ctk.CTkButton(btn_f, text="📂", width=34, height=28,
                          fg_color="transparent", hover_color=col["principal"],
                          command=lambda r=ruta: _abrir_archivo(r)).pack(side="left", padx=1)
            ctk.CTkButton(btn_f, text="🗑", width=34, height=28,
                          fg_color="transparent", hover_color="#C0392B",
                          text_color="#E74C3C",
                          command=lambda did=doc_id, r=ruta: self._eliminar_enaj(did, r)).pack(side="left", padx=1)

            ctk.CTkLabel(fila, text=f"  {nombre}",
                         font=self.estilos["fuentes"]["normal"],
                         text_color=col["texto_oscuro"],
                         anchor="w").pack(side="left", fill="both", expand=True)

    def _adjuntar_enajenacion(self):
        ruta = filedialog.askopenfilename(
            title="Seleccionar carta de enajenación",
            filetypes=[("Documentos", "*.pdf *.doc *.docx *.jpg *.jpeg *.png"),
                       ("Todos", "*.*")]
        )
        if not ruta:
            return
        nombre = os.path.basename(ruta)
        ext    = os.path.splitext(nombre)[1]
        destino = os.path.join(DOCS_DIR_ENAJ,
                               f"{self._modelo_nom}_{uuid.uuid4().hex[:8]}{ext}")
        shutil.copy2(ruta, destino)
        agregar_enajenacion(self._modelo_id, nombre, destino)
        self._cargar_enajenaciones()

    def _eliminar_enaj(self, doc_id, ruta):
        if not messagebox.askyesno("Confirmar", "¿Eliminar este documento?"):
            return
        try:
            if os.path.isfile(ruta):
                os.remove(ruta)
        except Exception:
            pass
        eliminar_enajenacion(doc_id)
        self._cargar_enajenaciones()

    # ─── Template carta ────────────────────────────────────────────────────────
    def _guardar_template(self):
        contenido = self._txt_carta.get("1.0", "end").rstrip()
        guardar_carta_entrega(self._modelo_id, contenido)
        messagebox.showinfo("Guardado", "Template guardado correctamente.")

    def _generar_carta(self):
        sel = self._combo_unidad.get()
        if not sel or sel not in self._unidad_data:
            messagebox.showwarning("Atención", "Selecciona una unidad.")
            return

        u = self._unidad_data[sel]
        # (id, registro, serial, cliente, firmware)
        datos = {
            "modelo"  : self._modelo_nom,
            "registro": u[1],
            "serial"  : u[2],
            "cliente" : u[3] or "—",
            "firmware": u[4] or "—",
            "fecha"   : datetime.date.today().strftime("%d/%m/%Y"),
        }

        template = self._txt_carta.get("1.0", "end").rstrip()
        try:
            filled = template.format(**datos)
        except KeyError as e:
            messagebox.showerror("Error de placeholder",
                                 f"Placeholder desconocido: {e}\n"
                                 f"Usa: {{modelo}} {{registro}} {{serial}} "
                                 f"{{firmware}} {{cliente}} {{fecha}}")
            return

        self._mostrar_preview(filled, datos["registro"])

    def _mostrar_preview(self, texto: str, registro: str):
        col = self.col
        win = ctk.CTkToplevel(self)
        win.title(f"Carta de Entrega — {registro}")
        win.geometry("680x560")
        win.grab_set()

        ctk.CTkLabel(win, text=f"🖨 Vista Previa — {registro}",
                     font=self.estilos["fuentes"]["subtitulo"],
                     text_color=col["principal"]).pack(pady=(14, 4), padx=16, anchor="w")

        txt = ctk.CTkTextbox(win, font=("Roboto Mono", 11),
                             fg_color=col["tarjetas"],
                             text_color=col["texto_oscuro"])
        txt.pack(fill="both", expand=True, padx=14, pady=4)
        txt.insert("1.0", texto)
        txt.configure(state="disabled")

        btn_row = ctk.CTkFrame(win, fg_color="transparent")
        btn_row.pack(fill="x", padx=14, pady=(4, 14))

        def guardar_txt():
            ruta = filedialog.asksaveasfilename(
                defaultextension=".txt",
                initialfile=f"carta_entrega_{registro}.txt",
                filetypes=[("Texto", "*.txt"), ("Todos", "*.*")]
            )
            if ruta:
                with open(ruta, "w", encoding="utf-8") as f:
                    f.write(texto)
                messagebox.showinfo("Guardado", f"Carta guardada en:\n{ruta}")

        def imprimir_html():
            html = (
                "<html><head><meta charset='utf-8'>"
                "<style>body{font-family:monospace;margin:40px;white-space:pre-wrap;}</style>"
                "</head><body>" + texto.replace("&", "&amp;").replace("<", "&lt;") + "</body></html>"
            )
            tmp = tempfile.NamedTemporaryFile(
                suffix=".html", delete=False, mode="w", encoding="utf-8")
            tmp.write(html)
            tmp.close()
            _abrir_archivo(tmp.name)

        ctk.CTkButton(btn_row, text="💾 Guardar TXT",
                      width=140, fg_color=col["principal"],
                      hover_color=col["principal_hover"],
                                text_color="#0A192F",
                      command=guardar_txt).pack(side="left", padx=(0, 8))
        ctk.CTkButton(btn_row, text="🌐 Abrir / Imprimir",
                      width=160, fg_color="#1A6B3C",
                      hover_color="#145530",
                      command=imprimir_html).pack(side="left", padx=(0, 8))
        ctk.CTkButton(btn_row, text="✖ Cerrar",
                      width=100, fg_color="#555",
                      hover_color="#333",
                      command=win.destroy).pack(side="right")


# ─── Función pública ────────────────────────────────────────────────────────────
def imprimir_docs_al_registrar(modelo_id: int, modelo_nom: str,
                                registro: str, serial: str,
                                firmware: str, cliente: str):
    """
    Abre automáticamente para impresión, justo al registrar una nueva unidad:
      1. Todas las cartas de enajenación adjuntas al modelo.
      2. La carta de entrega (template) rellena con los datos reales de la unidad.
    """
    import datetime as _dt
    import tempfile as _tmp

    # 1 ── Cartas de enajenación del modelo
    enajenaciones = listar_enajenacion(modelo_id)
    for _did, _nombre, ruta, _fecha in enajenaciones:
        _abrir_archivo(ruta)

    # 2 ── Carta de entrega
    template = obtener_carta_entrega(modelo_id) or PLANTILLA_DEFAULT
    datos = {
        "modelo"  : modelo_nom,
        "registro": registro,
        "serial"  : serial,
        "cliente" : cliente or "—",
        "firmware": firmware or "—",
        "fecha"   : _dt.date.today().strftime("%d/%m/%Y"),
    }
    try:
        filled = template.format(**datos)
    except KeyError:
        filled = template  # placeholder desconocido → mostrar raw

    html = (
        "<html><head><meta charset='utf-8'>"
        "<style>"
        "  body{font-family:monospace;margin:40px;white-space:pre-wrap;font-size:13px;}"
        "  @media print{@page{margin:2cm}}"
        "</style>"
        "</head><body>" +
        filled.replace("&", "&amp;").replace("<", "&lt;") +
        "</body></html>"
    )
    tmp = _tmp.NamedTemporaryFile(
        suffix=".html", delete=False, mode="w", encoding="utf-8")
    tmp.write(html)
    tmp.close()
    _abrir_archivo(tmp.name)
