"""
modulos/servicios/sub_entrada_servicio.py
=========================================
Submódulo Entrada en Servicio.

  • Lista máquinas actualmente en servicio
  • Nueva entrada: buscar por registro/serial, validar precinto,
    verificar inspección, registrar accesorios y motivo
  • Imprimir carta de entrada
  • Registrar procesos realizados
  • Completar servicio (salida)
"""
import customtkinter as ctk
import datetime
import tempfile
import webbrowser
import os
from tkinter import messagebox

from modulos.ventas.sub_cotizaciones import AutocompleteEntry


TIPOS_PROCESO = [
    "Inspección Anual",
    "Reparación",
    "Adaptación",
    "Actualización",
    "Cambio de Datos del Contribuyente",
    "Sustitución de Memoria Fiscal",
    "Sustitución de Memoria de Auditoría",
    "Alteración o Remoción de Dispositivo de Seguridad",
    "Otros",
]


def _trunc(texto, width_px):
    s = str(texto or "")
    max_chars = max(4, int(width_px / 7.5))
    if len(s) > max_chars:
        return s[:max_chars - 1].rstrip() + "…"
    return s


class _ToolTip:
    _tip = None

    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        widget.bind("<Enter>", self._show, add="+")
        widget.bind("<Leave>", self._hide, add="+")

    def _show(self, _=None):
        import tkinter as tk
        if _ToolTip._tip is not None:
            return
        try:
            x = self.widget.winfo_rootx() + 12
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
            tip = tk.Toplevel(self.widget)
            tip.wm_overrideredirect(True)
            tip.wm_geometry(f"+{x}+{y}")
            tk.Label(tip, text=self.text, justify="left",
                     bg="#0A192F", fg="#E2E8F0", relief="solid", borderwidth=1,
                     font=("Segoe UI", 9), padx=6, pady=3).pack()
            _ToolTip._tip = tip
        except Exception:
            pass

    def _hide(self, _=None):
        if _ToolTip._tip is not None:
            try:
                _ToolTip._tip.destroy()
            except Exception:
                pass
            _ToolTip._tip = None


def _cell(parent, full_text, width, height, text_color, font):
    disp = _trunc(full_text, width)
    frame = ctk.CTkFrame(parent, width=width, height=height, corner_radius=0,
                         fg_color="transparent")
    frame.pack(side="left", fill="x", expand=True)
    frame.pack_propagate(False)
    lbl = ctk.CTkLabel(frame, text=disp, anchor="center",
                       text_color=text_color, font=font)
    lbl.pack(fill="both", expand=True)
    if disp != str(full_text or ""):
        _ToolTip(lbl, str(full_text))
    return frame


class SubmoduloEntradaServicio(ctk.CTkFrame):
    COLS   = ["Registro", "Serial", "Cliente", "Modelo", "Fecha Entrada", ""]
    WIDTHS = [140, 150, 220, 160, 140, 130]

    def __init__(self, parent, estilos, permisos=None):
        super().__init__(parent, corner_radius=0,
                         fg_color=estilos["colores"]["fondo_oscuro"])
        self.estilos  = estilos
        self.permisos = permisos or {}
        self.col      = estilos["colores"]
        self.fnt      = estilos["fuentes"]
        self._construir_ui()
        self.after(0, self.cargar_datos)

    def _construir_ui(self):
        col, fnt = self.col, self.fnt

        bar = ctk.CTkFrame(self, height=52, corner_radius=0, fg_color="#020C1B")
        bar.pack(fill="x")
        bar.pack_propagate(False)

        ctk.CTkLabel(bar, text="🔧  Entrada en Servicio", font=fnt["titulo"],
                     text_color=col["principal"]).pack(side="left", padx=16, pady=8)

        ctk.CTkButton(bar, text="➕ Nueva Entrada",
                      fg_color=col["principal"], text_color="#0A192F",
                      hover_color=col.get("principal_hover", "#00C8D4"),
                      width=160, height=34,
                      command=self._nueva_entrada).pack(side="right", padx=12, pady=8)

        self.busq_var = ctk.StringVar()
        ctk.CTkEntry(bar, textvariable=self.busq_var, width=260, height=32,
                     placeholder_text="🔍 Buscar por registro, serial, cliente…"
                     ).pack(side="right", padx=4, pady=10)

        cont = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        cont.pack(fill="both", expand=True, padx=12, pady=8)

        hdr = ctk.CTkFrame(cont, corner_radius=0, fg_color="#0A192F", height=34)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        for c, w in zip(self.COLS, self.WIDTHS):
            ctk.CTkLabel(hdr, text=c, width=w, anchor="center",
                         text_color=col["texto_claro"],
                         font=fnt["normal"]).pack(side="left")

        self.scroll = ctk.CTkScrollableFrame(cont, corner_radius=0,
                                             fg_color=col["fondo_oscuro"])
        self.scroll.pack(fill="both", expand=True)

        self.busq_var.trace_add("write",
                                 lambda *_: self.cargar_datos(self.busq_var.get()))

    def cargar_datos(self, filtro: str = ""):
        from core.database import listar_entradas_servicio
        col, fnt = self.col, self.fnt

        for w in self.scroll.winfo_children():
            w.destroy()

        try:
            rows = listar_entradas_servicio("En Servicio", filtro)
        except Exception as e:
            ctk.CTkLabel(self.scroll, text=f"Error al cargar: {e}",
                         text_color="#E63946", font=fnt["normal"]).pack(pady=20)
            return

        if not rows:
            ctk.CTkLabel(self.scroll,
                         text="📭  No hay equipos actualmente en servicio",
                         text_color=col["principal"],
                         font=fnt["subtitulo"]).pack(pady=40)
            return

        for i, r in enumerate(rows):
            bg = col["tarjetas"] if i % 2 == 0 else col["fondo_oscuro"]
            fila = ctk.CTkFrame(self.scroll, corner_radius=0, fg_color=bg, height=34)
            fila.pack(fill="x")
            fila.pack_propagate(False)

            vals = [
                (r["numero_registro"],  col["texto_claro"]),
                (r["numero_serial"],    col["texto_claro"]),
                (r["cliente"] or "—",   col["texto_claro"]),
                (r["modelo_nombre"],    col["texto_claro"]),
                (r["fecha_entrada"] or "—", col["texto_claro"]),
            ]
            for (v, tc), w in zip(vals, self.WIDTHS[:-1]):
                _cell(fila, v, w, 34, tc, fnt["normal"])

            btn_f = ctk.CTkFrame(fila, width=self.WIDTHS[-1], corner_radius=0,
                                 fg_color="transparent")
            btn_f.pack(side="left", fill="x", expand=True)
            btn_f.pack_propagate(False)

            ctk.CTkButton(btn_f, text="⚙️ Procesos", width=100, height=28,
                          fg_color=col["principal"],
                          hover_color=col.get("principal_hover", "#00C8D4"),
                          text_color="#0A192F",
                          font=("Segoe UI", 10),
                          command=lambda rid=r["id"]: self._abrir_procesos(rid)
                          ).pack(side="right", padx=4)

    # ═══════════════════════════════════════════════════════════════════════
    # NUEVA ENTRADA
    # ═══════════════════════════════════════════════════════════════════════
    def _nueva_entrada(self):
        from core.database import (buscar_maquina_por_registro_serial,
                                   get_maquina_con_historial,
                                   calcular_dias_inspeccion,
                                   registrar_entrada_servicio)
        from core.session import get_usuario_actual
        col, fnt = self.col, self.fnt

        modal = ctk.CTkToplevel(self)
        modal.title("Nueva Entrada en Servicio")
        modal.geometry("720x780")
        modal.configure(fg_color=col["fondo_oscuro"])
        modal.transient(self.winfo_toplevel())
        modal.lift()
        modal.after(60, lambda: (modal.lift(), modal.focus_force(),
                                 modal.grab_set()))

        body = ctk.CTkScrollableFrame(modal, corner_radius=0,
                                      fg_color=col["fondo_oscuro"])
        body.pack(side="top", fill="both", expand=True)

        footer = ctk.CTkFrame(modal, height=64, corner_radius=0, fg_color="#020C1B")
        footer.pack(side="bottom", fill="x")
        footer.pack_propagate(False)
        err_lbl = ctk.CTkLabel(footer, text="", text_color="#E63946",
                               font=fnt["normal"])
        err_lbl.pack(side="left", padx=20)

        # ── Paso 1: Buscar máquina ──
        ctk.CTkLabel(body, text="Buscar máquina (Registro o Serial)",
                     text_color=col["texto_claro"],
                     font=fnt["normal"]).pack(anchor="w", padx=20, pady=(12, 4))

        busq_frame = ctk.CTkFrame(body, fg_color="transparent")
        busq_frame.pack(fill="x", padx=20)
        e_busq = ctk.CTkEntry(busq_frame, width=400, height=32,
                              placeholder_text="Ej: X9C123456789 o V2502123456789")
        e_busq.pack(side="left")
        ctk.CTkButton(busq_frame, text="🔍 Buscar", width=100, height=32,
                      fg_color=col["principal"], text_color="#0A192F",
                      command=lambda: _buscar()).pack(side="left", padx=8)

        result_frame = ctk.CTkFrame(body, fg_color=col["tarjetas"], corner_radius=8)
        result_frame.pack(fill="x", padx=20, pady=(8, 0))

        _maquina_sel = {"id": None, "data": None}

        def _buscar():
            for w in result_frame.winfo_children():
                w.destroy()
            txt = e_busq.get().strip()
            if len(txt) < 3:
                err_lbl.configure(text="Escriba al menos 3 caracteres.")
                return
            resultados = buscar_maquina_por_registro_serial(txt)
            if not resultados:
                ctk.CTkLabel(result_frame, text="No se encontraron máquinas.",
                             text_color=col["texto_claro"],
                             font=fnt["normal"]).pack(pady=10)
                return
            for r in resultados:
                f = ctk.CTkFrame(result_frame, fg_color="transparent")
                f.pack(fill="x", padx=8, pady=2)
                lbl_txt = (f'{r["numero_registro"]}  |  {r["numero_serial"]}  |  '
                           f'{r["modelo_nombre"]}  |  {r["fabricante"]}  |  '
                           f'Cliente: {r["cliente"] or "Sin asignar"}')
                ctk.CTkLabel(f, text=lbl_txt,
                             text_color=col["texto_claro"],
                             font=fnt["normal"]).pack(side="left")
                ctk.CTkButton(f, text="Seleccionar", width=90, height=24,
                              fg_color=col["principal"], text_color="#0A192F",
                              command=lambda m=r: _seleccionar(m)
                              ).pack(side="right")

        # ── Info de máquina seleccionada ──
        info_frame = ctk.CTkFrame(body, fg_color=col["tarjetas"], corner_radius=8)
        info_frame.pack(fill="x", padx=20, pady=(8, 0))
        info_lbl = ctk.CTkLabel(info_frame, text="Seleccione una máquina arriba…",
                                text_color=col["principal"], font=fnt["subtitulo"])
        info_lbl.pack(padx=12, pady=12)

        # ── Precinto ──
        prec_frame = ctk.CTkFrame(body, fg_color="transparent")
        prec_frame.pack(fill="x", padx=20, pady=(8, 0))
        ctk.CTkLabel(prec_frame, text="Número de Precinto:",
                     text_color=col["texto_claro"],
                     font=fnt["normal"]).pack(side="left")
        e_precinto = ctk.CTkEntry(prec_frame, width=200, height=32)
        e_precinto.pack(side="left", padx=8)
        precinto_ok = ctk.CTkLabel(prec_frame, text="", font=fnt["normal"])
        precinto_ok.pack(side="left")

        def _validar_precinto():
            if not _maquina_sel["data"]:
                return
            ingresado = e_precinto.get().strip()
            esperado = _maquina_sel["data"].get("numero_precinto", "")
            if not esperado:
                precinto_ok.configure(text="⚠️ Máquina sin precinto registrado",
                                      text_color="#F4A261")
            elif ingresado == esperado:
                precinto_ok.configure(text="✅ Precinto válido",
                                      text_color="#2EC4B6")
            else:
                precinto_ok.configure(text="❌ Precinto NO coincide",
                                      text_color="#E63946")

        e_precinto.bind("<KeyRelease>", lambda e: _validar_precinto())

        # ── Inspección ──
        insp_frame = ctk.CTkFrame(body, fg_color=col["tarjetas"], corner_radius=8)
        insp_frame.pack(fill="x", padx=20, pady=(8, 0))
        insp_lbl = ctk.CTkLabel(insp_frame, text="",
                                text_color=col["texto_claro"], font=fnt["normal"])
        insp_lbl.pack(padx=12, pady=12)

        # ── Accesorios ──
        ctk.CTkFrame(body, height=2, fg_color=col["principal"]).pack(
            fill="x", padx=20, pady=(12, 4))
        ctk.CTkLabel(body, text="  Accesorios recibidos", text_color=col["principal"],
                     font=fnt["subtitulo"]).pack(anchor="w", padx=20)

        acc_frame = ctk.CTkFrame(body, fg_color="transparent")
        acc_frame.pack(fill="x", padx=20, pady=(4, 0))

        var_caja   = ctk.StringVar(value="0")
        var_libro  = ctk.StringVar(value="0")
        var_calim  = ctk.StringVar(value="0")
        var_ccom   = ctk.StringVar(value="0")

        ctk.CTkCheckBox(acc_frame, text="Caja", variable=var_caja,
                        onvalue="1", offvalue="0",
                        text_color=col["texto_claro"],
                        font=fnt["normal"]).pack(side="left", padx=8)
        ctk.CTkCheckBox(acc_frame, text="Libro", variable=var_libro,
                        onvalue="1", offvalue="0",
                        text_color=col["texto_claro"],
                        font=fnt["normal"]).pack(side="left", padx=8)
        ctk.CTkCheckBox(acc_frame, text="Cable Alimentación", variable=var_calim,
                        onvalue="1", offvalue="0",
                        text_color=col["texto_claro"],
                        font=fnt["normal"]).pack(side="left", padx=8)
        ctk.CTkCheckBox(acc_frame, text="Cable Comunicación", variable=var_ccom,
                        onvalue="1", offvalue="0",
                        text_color=col["texto_claro"],
                        font=fnt["normal"]).pack(side="left", padx=8)

        # ── Reporte Z y Motivo ──
        ctk.CTkLabel(body, text="Último Reporte Z:", text_color=col["texto_claro"],
                     font=fnt["normal"]).pack(anchor="w", padx=20, pady=(8, 2))
        e_reporte_z = ctk.CTkEntry(body, width=400, height=32)
        e_reporte_z.pack(anchor="w", padx=20)

        ctk.CTkLabel(body, text="Motivo del Servicio:", text_color=col["texto_claro"],
                     font=fnt["normal"]).pack(anchor="w", padx=20, pady=(8, 2))
        e_motivo = ctk.CTkTextbox(body, width=660, height=60)
        e_motivo.pack(anchor="w", padx=20)

        def _seleccionar(m):
            _maquina_sel["id"] = m["id"]
            _maquina_sel["data"] = get_maquina_con_historial(m["id"])
            d = _maquina_sel["data"]
            info_lbl.configure(
                text=f'✅ {d["numero_registro"]}  |  {d["numero_serial"]}  |  '
                     f'{d["modelo_nombre"]}  |  {d["fabricante"]}  |  '
                     f'Cliente: {d.get("cliente") or "Sin asignar"}'
            )
            # Validar precinto si ya hay texto
            _validar_precinto()
            # Calcular inspección
            info_insp = calcular_dias_inspeccion(d)
            insp_lbl.configure(
                text=f'{info_insp["mensaje"]}\n'
                     f'Fecha de vencimiento: {info_insp["fecha_vencimiento"]}'
            )

        def _guardar():
            if not _maquina_sel["id"]:
                err_lbl.configure(text="Seleccione una máquina.")
                return
            data = {
                "maquina_id": _maquina_sel["id"],
                "precinto_validado": e_precinto.get().strip(),
                "caja": var_caja.get(),
                "libro": var_libro.get(),
                "cable_alimentacion": var_calim.get(),
                "cable_comunicacion": var_ccom.get(),
                "ultimo_reporte_z": e_reporte_z.get().strip(),
                "motivo_servicio": e_motivo.get("1.0", "end").strip(),
                "usuario": get_usuario_actual() or "",
            }
            eid = registrar_entrada_servicio(data)
            if eid > 0:
                modal.destroy()
                self.cargar_datos(self.busq_var.get())
            else:
                err_lbl.configure(text="Error al registrar entrada.")

        def _imprimir_carta():
            if not _maquina_sel["data"]:
                err_lbl.configure(text="Seleccione una máquina primero.")
                return
            d = _maquina_sel["data"]
            info_insp = calcular_dias_inspeccion(d)
            html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>
  body {{ font-family: Arial, sans-serif; margin: 40px; color: #333; }}
  h1 {{ color: #0A192F; border-bottom: 3px solid #00E5FF; padding-bottom: 10px; }}
  .section {{ margin: 20px 0; padding: 15px; background: #f8f9fa; border-radius: 8px; }}
  .label {{ font-weight: bold; color: #0A192F; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
  td, th {{ border: 1px solid #ddd; padding: 10px; text-align: left; }}
  th {{ background: #0A192F; color: white; }}
  .alert {{ color: #E63946; font-weight: bold; }}
  .ok {{ color: #2EC4B6; font-weight: bold; }}
</style></head><body>
<h1>📝 CARTA DE ENTRADA EN SERVICIO</h1>
<div class="section">
  <p><span class="label">Fecha:</span> {datetime.datetime.now().strftime("%d/%m/%Y %H:%M")}</p>
  <p><span class="label">Registro:</span> {d.get("numero_registro","—")}</p>
  <p><span class="label">Serial:</span> {d.get("numero_serial","—")}</p>
  <p><span class="label">Modelo:</span> {d.get("modelo_nombre","—")}</p>
  <p><span class="label">Fabricante:</span> {d.get("fabricante","—")}</p>
  <p><span class="label">Cliente:</span> {d.get("cliente") or "Sin asignar"}</p>
</div>
<div class="section">
  <p><span class="label">Precinto validado:</span> {e_precinto.get().strip() or "—"}</p>
  <p><span class="label">Estado de Inspección:</span> {info_insp["mensaje"]}</p>
  <p><span class="label">Fecha vencimiento inspección:</span> {info_insp["fecha_vencimiento"]}</p>
</div>
<div class="section">
  <p><span class="label">Accesorios recibidos:</span></p>
  <table>
    <tr><th>Ítem</th><th>Recibido</th></tr>
    <tr><td>Caja</td><td>{"✅ Sí" if var_caja.get()=="1" else "❌ No"}</td></tr>
    <tr><td>Libro</td><td>{"✅ Sí" if var_libro.get()=="1" else "❌ No"}</td></tr>
    <tr><td>Cable de Alimentación</td><td>{"✅ Sí" if var_calim.get()=="1" else "❌ No"}</td></tr>
    <tr><td>Cable de Comunicación</td><td>{"✅ Sí" if var_ccom.get()=="1" else "❌ No"}</td></tr>
  </table>
</div>
<div class="section">
  <p><span class="label">Último Reporte Z:</span> {e_reporte_z.get().strip() or "—"}</p>
  <p><span class="label">Motivo del Servicio:</span></p>
  <p>{e_motivo.get("1.0","end").strip().replace(chr(10),"<br>") or "—"}</p>
</div>
</body></html>"""
            tmp = tempfile.NamedTemporaryFile("w", suffix=".html",
                                               delete=False, encoding="utf-8")
            tmp.write(html)
            tmp.close()
            webbrowser.open(f"file://{tmp.name}")

        ctk.CTkButton(footer, text="🖨 Imprimir Carta",
                      fg_color="#1A3550", text_color=col["texto_claro"],
                      hover_color="#2A4560",
                      width=160, height=40,
                      command=_imprimir_carta).pack(side="right", padx=(0, 8), pady=12)
        ctk.CTkButton(footer, text="💾 Registrar Entrada",
                      fg_color=col["principal"], text_color="#0A192F",
                      hover_color=col.get("principal_hover", "#00C8D4"),
                      width=200, height=40,
                      command=_guardar).pack(side="right", padx=20, pady=12)

    # ═══════════════════════════════════════════════════════════════════════
    # PROCESOS / COMPLETAR SERVICIO
    # ═══════════════════════════════════════════════════════════════════════
    def _abrir_procesos(self, entrada_id):
        from core.database import (get_entrada_completa, registrar_proceso,
                                   registrar_salida)
        from core.session import get_usuario_actual
        col, fnt = self.col, self.fnt

        d = get_entrada_completa(entrada_id)
        if not d:
            messagebox.showerror("Error", "No se pudo cargar la entrada.")
            return

        modal = ctk.CTkToplevel(self)
        modal.title(f"Servicio — {d['numero_registro']}")
        modal.geometry("700x720")
        modal.configure(fg_color=col["fondo_oscuro"])
        modal.transient(self.winfo_toplevel())
        modal.lift()
        modal.after(60, lambda: (modal.lift(), modal.focus_force(),
                                 modal.grab_set()))

        body = ctk.CTkScrollableFrame(modal, corner_radius=0,
                                      fg_color=col["fondo_oscuro"])
        body.pack(side="top", fill="both", expand=True)

        footer = ctk.CTkFrame(modal, height=64, corner_radius=0, fg_color="#020C1B")
        footer.pack(side="bottom", fill="x")
        footer.pack_propagate(False)
        err_lbl = ctk.CTkLabel(footer, text="", text_color="#E63946",
                               font=fnt["normal"])
        err_lbl.pack(side="left", padx=20)

        # ── Info de la entrada ──
        info = ctk.CTkFrame(body, fg_color=col["tarjetas"], corner_radius=8)
        info.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(info,
                     text=f'{d["numero_registro"]}  |  {d["numero_serial"]}  |  '
                          f'{d["modelo_nombre"]}  |  Cliente: {d.get("cliente") or "—"}',
                     text_color=col["principal"], font=fnt["subtitulo"]
                     ).pack(anchor="w", padx=12, pady=(8, 2))
        ctk.CTkLabel(info,
                     text=f'Fecha entrada: {d["fecha_entrada"]}  |  '
                          f'Motivo: {d["motivo_servicio"] or "—"}',
                     text_color=col["texto_claro"], font=fnt["normal"]
                     ).pack(anchor="w", padx=12, pady=(2, 8))

        # ── Procesos ya registrados ──
        ctk.CTkLabel(body, text="Procesos realizados", text_color=col["principal"],
                     font=fnt["subtitulo"]).pack(anchor="w", pady=(8, 4))

        proc_box = ctk.CTkFrame(body, fg_color=col["tarjetas"], corner_radius=8)
        proc_box.pack(fill="x", pady=(0, 8))

        if d.get("procesos"):
            for p in d["procesos"]:
                f = ctk.CTkFrame(proc_box, fg_color="transparent")
                f.pack(fill="x", padx=8, pady=2)
                ctk.CTkLabel(f,
                             text=f'📌 {p["tipo_proceso"]} — {p["fecha"]} — '
                                  f'{p["usuario"] or ""}',
                             text_color=col["texto_claro"],
                             font=fnt["normal"]).pack(side="left")
                if p.get("descripcion"):
                    ctk.CTkLabel(f, text=f'📝 {p["descripcion"]}',
                                 text_color=col.get("texto_oscuro", "#94A3B8"),
                                 font=("Segoe UI", 9)).pack(anchor="w", padx=20)
        else:
            ctk.CTkLabel(proc_box, text="Sin procesos registrados.",
                         text_color=col.get("texto_oscuro", "#94A3B8"),
                         font=fnt["normal"]).pack(pady=8)

        # ── Agregar nuevo proceso ──
        ctk.CTkFrame(body, height=2, fg_color=col["principal"]).pack(
            fill="x", pady=(8, 4))
        ctk.CTkLabel(body, text="  Registrar nuevo proceso",
                     text_color=col["principal"],
                     font=fnt["subtitulo"]).pack(anchor="w")

        ctk.CTkLabel(body, text="Tipo de proceso:", text_color=col["texto_claro"],
                     font=fnt["normal"]).pack(anchor="w", pady=(4, 2))
        cb_tipo_proc = ctk.CTkComboBox(body, values=TIPOS_PROCESO, width=400,
                                       state="readonly")
        cb_tipo_proc.pack(anchor="w")
        cb_tipo_proc.set(TIPOS_PROCESO[0])

        ctk.CTkLabel(body, text="Descripción / Detalle del procedimiento:",
                     text_color=col["texto_claro"],
                     font=fnt["normal"]).pack(anchor="w", pady=(8, 2))
        e_desc = ctk.CTkTextbox(body, width=640, height=80)
        e_desc.pack(anchor="w")

        def _guardar_proceso():
            tipo = cb_tipo_proc.get()
            desc = e_desc.get("1.0", "end").strip()
            ok = registrar_proceso(entrada_id, tipo, desc,
                                   get_usuario_actual() or "")
            if ok > 0:
                e_desc.delete("1.0", "end")
                # Recargar modal
                modal.destroy()
                self._abrir_procesos(entrada_id)
            else:
                err_lbl.configure(text="Error al registrar proceso.")

        ctk.CTkButton(body, text="➕ Agregar Proceso",
                      fg_color=col["principal"], text_color="#0A192F",
                      hover_color=col.get("principal_hover", "#00C8D4"),
                      width=180, height=34,
                      command=_guardar_proceso).pack(anchor="w", pady=(8, 0))

        # ── Completar servicio ──
        ctk.CTkFrame(body, height=2, fg_color=col["principal"]).pack(
            fill="x", pady=(16, 4))
        ctk.CTkLabel(body, text="  Completar Servicio",
                     text_color=col["principal"],
                     font=fnt["subtitulo"]).pack(anchor="w")

        sal_frame = ctk.CTkFrame(body, fg_color=col["tarjetas"], corner_radius=8)
        sal_frame.pack(fill="x", pady=(4, 0))

        ctk.CTkLabel(sal_frame, text="Precinto de salida:",
                     text_color=col["texto_claro"],
                     font=fnt["normal"]).grid(row=0, column=0, sticky="w",
                                              padx=10, pady=(8, 2))
        e_prec_sal = ctk.CTkEntry(sal_frame, width=200, height=32)
        e_prec_sal.grid(row=1, column=0, padx=10, pady=(0, 8))

        ctk.CTkLabel(sal_frame, text="Último Z generado:",
                     text_color=col["texto_claro"],
                     font=fnt["normal"]).grid(row=0, column=1, sticky="w",
                                              padx=10, pady=(8, 2))
        e_z_sal = ctk.CTkEntry(sal_frame, width=200, height=32)
        e_z_sal.grid(row=1, column=1, padx=10, pady=(0, 8))

        def _completar():
            prec = e_prec_sal.get().strip()
            z_val = e_z_sal.get().strip()
            if not prec or not z_val:
                err_lbl.configure(text="Precinto y último Z son obligatorios.")
                return
            ok = registrar_salida(entrada_id, prec, z_val,
                                  get_usuario_actual() or "")
            if ok:
                modal.destroy()
                self.cargar_datos(self.busq_var.get())
            else:
                err_lbl.configure(text="Error al completar servicio.")

        ctk.CTkButton(footer, text="✅ Terminar Servicio",
                      fg_color="#2EC4B6", text_color="#0A192F",
                      hover_color="#1DB5A6",
                      width=200, height=40,
                      command=_completar).pack(side="right", padx=20, pady=12)
