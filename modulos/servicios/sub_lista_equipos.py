"""
modulos/servicios/sub_lista_equipos.py
======================================
Submódulo Lista de Equipos.

  • Lista TODAS las máquinas registradas
  • Ordenadas por días restantes para inspección (vencidos primero)
  • Muestra fecha de vencimiento de inspección
  • Botón para ver historial completo de cada equipo
"""
import customtkinter as ctk
from tkinter import messagebox


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


class SubmoduloListaEquipos(ctk.CTkFrame):
    COLS   = ["Registro", "Serial", "Cliente", "Modelo", "Fabricante",
              "Días Rest.", "Vencimiento", ""]
    WIDTHS = [130, 140, 200, 140, 140, 100, 120, 100]

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

        ctk.CTkLabel(bar, text="📋  Lista de Equipos", font=fnt["titulo"],
                     text_color=col["principal"]).pack(side="left", padx=16, pady=8)

        self.busq_var = ctk.StringVar()
        ctk.CTkEntry(bar, textvariable=self.busq_var, width=260, height=32,
                     placeholder_text="🔍 Buscar por registro, serial, cliente…"
                     ).pack(side="right", padx=12, pady=10)

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
        from core.database import listar_todas_maquinas_con_vencimiento
        col, fnt = self.col, self.fnt

        for w in self.scroll.winfo_children():
            w.destroy()

        try:
            rows = listar_todas_maquinas_con_vencimiento()
        except Exception as e:
            ctk.CTkLabel(self.scroll, text=f"Error al cargar: {e}",
                         text_color="#E63946", font=fnt["normal"]).pack(pady=20)
            return

        if filtro:
            f = filtro.lower()
            rows = [r for r in rows
                    if f in str(r.get("numero_registro","")).lower()
                    or f in str(r.get("numero_serial","")).lower()
                    or f in str(r.get("cliente","")).lower()
                    or f in str(r.get("modelo_nombre","")).lower()]

        if not rows:
            ctk.CTkLabel(self.scroll, text="📭  No hay equipos registrados",
                         text_color=col["principal"],
                         font=fnt["subtitulo"]).pack(pady=40)
            return

        for i, r in enumerate(rows):
            bg = col["tarjetas"] if i % 2 == 0 else col["fondo_oscuro"]
            fila = ctk.CTkFrame(self.scroll, corner_radius=0, fg_color=bg, height=34)
            fila.pack(fill="x")
            fila.pack_propagate(False)

            dias = r.get("dias_restantes", -9999)
            vencida = r.get("vencida", False)
            if vencida:
                dias_color = "#E63946"
                dias_txt = f"🔴 {abs(dias)}d venc."
            elif dias <= 30:
                dias_color = "#F4A261"
                dias_txt = f"🟡 {dias}d"
            else:
                dias_color = "#2EC4B6"
                dias_txt = f"🟢 {dias}d"

            vals = [
                (r["numero_registro"],       col["texto_claro"]),
                (r["numero_serial"],         col["texto_claro"]),
                (r["cliente"] or "—",        col["texto_claro"]),
                (r["modelo_nombre"],         col["texto_claro"]),
                (r["fabricante"],            col["texto_claro"]),
                (dias_txt,                    dias_color),
                (r.get("fecha_vencimiento","—"), col["texto_claro"]),
            ]
            for (v, tc), w in zip(vals, self.WIDTHS[:-1]):
                _cell(fila, v, w, 34, tc, fnt["normal"])

            btn_f = ctk.CTkFrame(fila, width=self.WIDTHS[-1], corner_radius=0,
                                 fg_color="transparent")
            btn_f.pack(side="left", fill="x", expand=True)
            btn_f.pack_propagate(False)

            ctk.CTkButton(btn_f, text="📜 Historial", width=90, height=28,
                          fg_color="#1A3550",
                          hover_color=col["principal"],
                          text_color=col["texto_claro"],
                          font=("Segoe UI", 10),
                          command=lambda rid=r["id"]: self._ver_historial(rid)
                          ).pack(side="right", padx=4)

    def _ver_historial(self, maquina_id):
        from core.database import (get_maquina_con_historial,
                                   calcular_dias_inspeccion,
                                   DB_NAME)
        import sqlite3
        import datetime
        import tempfile
        import webbrowser
        import os
        col, fnt = self.col, self.fnt

        m = get_maquina_con_historial(maquina_id)
        if not m:
            messagebox.showerror("Error", "No se pudo cargar el historial.")
            return

        info_insp = calcular_dias_inspeccion(m)

        modal = ctk.CTkToplevel(self)
        modal.title(f"Historial - {m['numero_registro']}")
        modal.geometry("900x750")
        modal.configure(fg_color=col["fondo_oscuro"])
        modal.transient(self.winfo_toplevel())
        modal.lift()
        modal.after(60, lambda: (modal.lift(), modal.focus_force(),
                                 modal.grab_set()))

        body = ctk.CTkScrollableFrame(modal, corner_radius=0,
                                      fg_color=col["fondo_oscuro"])
        body.pack(side="top", fill="both", expand=True, padx=16, pady=12)

        # Info general
        info = ctk.CTkFrame(body, fg_color=col["tarjetas"], corner_radius=8)
        info.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(info,
                     text=f'{m["numero_registro"]}  |  {m["numero_serial"]}',
                     text_color=col["principal"], font=fnt["subtitulo"]
                     ).pack(anchor="w", padx=12, pady=(8, 2))
        ctk.CTkLabel(info,
                     text=f'Modelo: {m["modelo_nombre"]}  |  '
                          f'Fabricante: {m["fabricante"]}  |  '
                          f'Cliente: {m.get("cliente") or "Sin asignar"}',
                     text_color=col["texto_claro"], font=fnt["normal"]
                     ).pack(anchor="w", padx=12, pady=(2, 2))
        ctk.CTkLabel(info,
                     text=f'{info_insp["mensaje"]}  |  '
                          f'Vencimiento: {info_insp["fecha_vencimiento"]}',
                     text_color=col["principal"], font=fnt["normal"]
                     ).pack(anchor="w", padx=12, pady=(2, 8))

        # Consulta BD
        try:
            con = sqlite3.connect(DB_NAME)
            con.row_factory = sqlite3.Row
            insps = con.execute(
                "SELECT * FROM servicios_inspecciones WHERE maquina_id=? ORDER BY fecha_inspeccion DESC",
                (maquina_id,)).fetchall()
            entradas = con.execute("""
                SELECT se.*, ss.fecha_salida, ss.precinto_salida, ss.ultimo_z
                FROM servicios_entrada se
                LEFT JOIN servicios_salida ss ON ss.entrada_id = se.id
                WHERE se.maquina_id = ? ORDER BY se.fecha_entrada DESC
            """, (maquina_id,)).fetchall()
            procesos = con.execute("""
                SELECT sp.*, se.fecha_entrada
                FROM servicios_procesos sp
                JOIN servicios_entrada se ON se.id = sp.entrada_id
                WHERE se.maquina_id = ?
                ORDER BY sp.fecha DESC
            """, (maquina_id,)).fetchall()
            con.close()
        except Exception as e:
            ctk.CTkLabel(body, text=f"Error BD: {e}",
                         text_color="#E63946", font=fnt["normal"]
                         ).pack(anchor="w", pady=8)
            return

        # Inspecciones
        ctk.CTkLabel(body, text="Inspecciones registradas",
                     text_color=col["principal"],
                     font=fnt["subtitulo"]).pack(anchor="w", pady=(8, 4))

        if insps:
            for ins in insps:
                f = ctk.CTkFrame(body, fg_color=col["tarjetas"], corner_radius=4)
                f.pack(fill="x", pady=2)
                ctk.CTkLabel(f,
                             text=f'📅 {ins["fecha_inspeccion"]} - '
                                  f'{ins["tipo"]} - {ins["usuario"] or ""}',
                             text_color=col["texto_claro"],
                             font=fnt["normal"]).pack(side="left", padx=8)
        else:
            ctk.CTkLabel(body, text="Sin inspecciones registradas.",
                         text_color=col.get("texto_oscuro", "#94A3B8"),
                         font=fnt["normal"]).pack(anchor="w")

        # Entradas en servicio
        ctk.CTkLabel(body, text="Entradas en Servicio",
                     text_color=col["principal"],
                     font=fnt["subtitulo"]).pack(anchor="w", pady=(12, 4))

        if entradas:
            for ent in entradas:
                f = ctk.CTkFrame(body, fg_color=col["tarjetas"], corner_radius=4)
                f.pack(fill="x", pady=2)
                estado = "Completado" if ent["fecha_salida"] else "En Servicio"
                txt = (f'{estado}  |  {ent["fecha_entrada"]}  |  '
                       f'Motivo: {ent["motivo_servicio"] or "-"}  |  '
                       f'Usuario: {ent["usuario_entrada"] or ""}')
                ctk.CTkLabel(f, text=txt,
                             text_color=col["texto_claro"],
                             font=fnt["normal"]).pack(anchor="w", padx=8)
                if ent["fecha_salida"]:
                    ctk.CTkLabel(f,
                                 text=f'   Salida: {ent["fecha_salida"]}  |  '
                                      f'Precinto: {ent["precinto_salida"] or "-"}  |  '
                                      f'Z: {ent["ultimo_z"] or "-"}',
                                 text_color=col.get("texto_oscuro", "#94A3B8"),
                                 font=("Segoe UI", 9)).pack(anchor="w", padx=20)
        else:
            ctk.CTkLabel(body, text="Sin entradas en servicio.",
                         text_color=col.get("texto_oscuro", "#94A3B8"),
                         font=fnt["normal"]).pack(anchor="w")

        # Procesos realizados
        ctk.CTkLabel(body, text="Procesos realizados",
                     text_color=col["principal"],
                     font=fnt["subtitulo"]).pack(anchor="w", pady=(12, 4))

        if procesos:
            for pr in procesos:
                f = ctk.CTkFrame(body, fg_color=col["tarjetas"], corner_radius=4)
                f.pack(fill="x", pady=2)
                ctk.CTkLabel(f,
                             text=f'⚙️ {pr["tipo_proceso"]} - {pr["fecha"]} - '
                                  f'{pr["usuario"] or ""}',
                             text_color=col["texto_claro"],
                             font=fnt["normal"]).pack(anchor="w", padx=8)
                if pr.get("descripcion"):
                    desc_lbl = ctk.CTkLabel(f, text=f'📝 {pr["descripcion"]}',
                                 text_color=col.get("texto_oscuro", "#94A3B8"),
                                 font=("Segoe UI", 9),
                                 wraplength=800, justify="left")
                    desc_lbl.pack(anchor="w", padx=20)
        else:
            ctk.CTkLabel(body, text="Sin procesos registrados.",
                         text_color=col.get("texto_oscuro", "#94A3B8"),
                         font=fnt["normal"]).pack(anchor="w")

        # Footer con boton Imprimir
        footer = ctk.CTkFrame(modal, height=64, corner_radius=0, fg_color="#020C1B")
        footer.pack(side="bottom", fill="x")
        footer.pack_propagate(False)

        def _imprimir_historial():
            now = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
            html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>
  body {{ font-family: Arial, sans-serif; margin: 40px; color: #333; }}
  h1 {{ color: #0A192F; border-bottom: 3px solid #00E5FF; padding-bottom: 10px; }}
  h2 {{ color: #0A192F; margin-top: 24px; }}
  .section {{ margin: 16px 0; padding: 12px; background: #f8f9fa; border-radius: 6px; }}
  .label {{ font-weight: bold; color: #0A192F; }}
  .item {{ padding: 8px; margin: 4px 0; background: white; border-radius: 4px; border-left: 4px solid #00E5FF; }}
  .desc {{ color: #666; font-size: 13px; margin-left: 20px; }}
  .footer {{ margin-top: 40px; text-align: center; color: #999; font-size: 12px; }}
</style></head><body>
<h1>HISTORIAL DEL EQUIPO</h1>
<div class="section">
  <p><span class="label">Fecha de emision:</span> {now}</p>
  <p><span class="label">Registro:</span> {m.get("numero_registro","-")}</p>
  <p><span class="label">Serial:</span> {m.get("numero_serial","-")}</p>
  <p><span class="label">Modelo:</span> {m.get("modelo_nombre","-")}</p>
  <p><span class="label">Fabricante:</span> {m.get("fabricante","-")}</p>
  <p><span class="label">Cliente:</span> {m.get("cliente") or "Sin asignar"}</p>
  <p><span class="label">Inspeccion:</span> {info_insp["mensaje"]}</p>
  <p><span class="label">Vencimiento:</span> {info_insp["fecha_vencimiento"]}</p>
</div>
<h2>Entradas en Servicio</h2>
"""
            if entradas:
                for ent in entradas:
                    estado = "Completado" if ent["fecha_salida"] else "En Servicio"
                    html += f'<div class="item"><span class="label">{estado}</span> - {ent["fecha_entrada"]} - Motivo: {ent["motivo_servicio"] or "-"} - Usuario: {ent["usuario_entrada"] or ""}</div>'
                    if ent["fecha_salida"]:
                        html += f'<div class="desc">Salida: {ent["fecha_salida"]} | Precinto: {ent["precinto_salida"] or "-"} | Z: {ent["ultimo_z"] or "-"}</div>'
            else:
                html += '<p>Sin entradas en servicio.</p>'

            html += '<h2>Procesos Realizados</h2>'
            if procesos:
                for pr in procesos:
                    html += f'<div class="item"><span class="label">{pr["tipo_proceso"]}</span> - {pr["fecha"]} - {pr["usuario"] or ""}</div>'
                    if pr.get("descripcion"):
                        html += f'<div class="desc">{pr["descripcion"]}</div>'
            else:
                html += '<p>Sin procesos registrados.</p>'

            html += '<h2>Inspecciones</h2>'
            if insps:
                for ins in insps:
                    html += f'<div class="item">{ins["fecha_inspeccion"]} - {ins["tipo"]} - {ins["usuario"] or ""}</div>'
            else:
                html += '<p>Sin inspecciones registradas.</p>'

            html += '<div class="footer">Generado por CIGG SYSTEMS - Historial de Equipo</div></body></html>'

            tmp = tempfile.NamedTemporaryFile("w", suffix=".html",
                                               delete=False, encoding="utf-8")
            tmp.write(html)
            tmp.close()
            webbrowser.open(f"file://{tmp.name}")

        ctk.CTkButton(footer, text="Imprimir Historial",
                      fg_color=col["principal"], text_color="#0A192F",
                      hover_color=col.get("principal_hover", "#00C8D4"),
                      width=200, height=40,
                      command=_imprimir_historial).pack(side="right", padx=20, pady=12)
