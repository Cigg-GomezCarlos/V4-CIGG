"""
modulos/monedas/ui.py
======================
Interfaz gráfica del módulo Monedas.

Contiene:
  ModuloMonedas — frame principal con tarjetas por moneda e historial
"""

import sqlite3
from datetime import datetime

import customtkinter as ctk

from core.database import DB_NAME
from .db import (
    MONEDAS_CONFIG, CODIGOS_HISTORIAL,
    inicializar_tablas, leer_todas, leer_historial,
    guardar, actualizar_en_background,
    _consultar_bcv, _consultar_binance,
)


class ModuloMonedas(ctk.CTkFrame):
    """
    Módulo principal de gestión de monedas.

    Muestra una tarjeta por moneda con:
      - Tasa actual (editable manualmente si aplica)
      - Fuente de datos
      - Fecha de última actualización
      - Botones Actualizar / Editar (o Guardar en modo edición)

    Incluye panel de historial de cambios filtrable por moneda.
    """

    def __init__(self, parent, estilos, usuario: str = "Sistema"):
        super().__init__(parent,
                         fg_color=estilos["colores"]["fondo_oscuro"],
                         corner_radius=0)
        self.estilos  = estilos
        self.usuario  = usuario
        self.tarjetas = {}          # {codigo: {entry, lbl_fecha, lbl_estado, frame_btns, cfg}}
        self._historial_visible = False
        self._tab_activo = "TODOS"

        inicializar_tablas()
        self._construir_ui()
        self._actualizar_auto()

    # ─── Construcción de UI ───────────────────────────────────────────────────

    def _construir_ui(self):
        col = self.estilos["colores"]

        # ── Encabezado ────────────────────────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=30, pady=(25, 10))

        ctk.CTkLabel(
            header, text="💱  GESTIÓN DE MONEDAS",
            font=("Roboto Mono", 18, "bold"),
            text_color=col["texto_oscuro"],
        ).pack(side="left")

        ctk.CTkButton(
            header, text="📋  Historial",
            fg_color="#1A3550", hover_color=col["tarjetas"],
            text_color=col["texto_oscuro"], font=("Roboto Mono", 11),
            width=130, height=34,
            command=self._toggle_historial,
        ).pack(side="right", padx=(8, 0))

        ctk.CTkButton(
            header, text="🔄  Actualizar todas",
            fg_color=col["principal"], hover_color=col["principal_hover"],
            text_color="#0A192F", font=("Roboto Mono", 11),
            width=160, height=34,
            command=self._actualizar_auto,
        ).pack(side="right")

        # ── Separador ─────────────────────────────────────────────────────────
        ctk.CTkFrame(self, height=2, fg_color=col["tarjetas"]).pack(
            fill="x", padx=30, pady=(0, 20))

        # ── Grid de tarjetas ──────────────────────────────────────────────────
        self._grid = ctk.CTkFrame(self, fg_color="transparent")
        self._grid.pack(fill="x", padx=30)
        for i in range(5):
            self._grid.columnconfigure(i, weight=1)

        datos_bd = leer_todas()
        for idx, cfg in enumerate(MONEDAS_CONFIG):
            fila, col_idx = divmod(idx, 5)
            datos = datos_bd.get(cfg["codigo"],
                                 {"tasa": 0.0, "actualizado": "—", "error": ""})
            self._crear_tarjeta(cfg, datos, fila, col_idx)

        # ── Panel de historial (oculto por defecto) ───────────────────────────
        self._sep_hist = ctk.CTkFrame(self, height=2,
                                      fg_color=self.estilos["colores"]["tarjetas"])
        self._panel_hist = ctk.CTkFrame(self, fg_color="transparent")

    # ─── Tarjeta ──────────────────────────────────────────────────────────────

    def _crear_tarjeta(self, cfg: dict, datos: dict, fila: int, columna: int):
        col    = self.estilos["colores"]
        codigo = cfg["codigo"]

        card = ctk.CTkFrame(self._grid, fg_color=col["tarjetas"], corner_radius=12)
        card.grid(row=fila, column=columna, padx=10, pady=10, sticky="nsew")
        card.columnconfigure(0, weight=1)

        ctk.CTkLabel(card,
                     text=f"{cfg['icono']}  {cfg['nombre']}",
                     font=("Roboto Mono", 13, "bold"),
                     text_color=col["texto_oscuro"]).pack(pady=(18, 4), padx=15)

        ctk.CTkLabel(card,
                     text=f"Fuente: {cfg['fuente']}",
                     font=("Roboto Mono", 10),
                     text_color="#6B8BAE").pack()

        entry = ctk.CTkEntry(
            card,
            font=("Roboto Mono", 22, "bold"),
            text_color=col["principal"],
            fg_color="#0A192F",
            border_color=col["principal"],
            justify="center",
            width=200, height=46,
        )
        entry.insert(0, f"{datos['tasa']:.4f}")
        entry.pack(pady=(14, 6), padx=15)

        # Bloquear si es automática y sin error
        if not cfg["manual"] and cfg["fuente"] != "MANUAL":
            if not datos.get("error"):
                entry.configure(state="disabled")

        lbl_fecha = ctk.CTkLabel(card,
                                 text=f"🕐 {datos['actualizado']}",
                                 font=("Roboto Mono", 10),
                                 text_color="#4A6FA5")
        lbl_fecha.pack(pady=(0, 4))

        lbl_estado = ctk.CTkLabel(card, text="",
                                  font=("Roboto Mono", 9),
                                  text_color=col["error"],
                                  wraplength=190)
        lbl_estado.pack(pady=(0, 6), padx=10)
        if datos.get("error"):
            lbl_estado.configure(text=f"⚠ {datos['error']}")

        frame_btns = ctk.CTkFrame(card, fg_color="transparent")
        frame_btns.pack(fill="x", padx=15, pady=(4, 16))

        self._botones_normales(frame_btns, cfg, entry, lbl_fecha, lbl_estado)

        self.tarjetas[codigo] = {
            "entry":      entry,
            "lbl_fecha":  lbl_fecha,
            "lbl_estado": lbl_estado,
            "frame_btns": frame_btns,
            "cfg":        cfg,
        }

    # ─── Botones de tarjeta ───────────────────────────────────────────────────

    def _botones_normales(self, frame, cfg, entry, lbl_fecha, lbl_estado):
        """Renderiza los botones estándar (estado inicial o tras guardar)."""
        col    = self.estilos["colores"]
        codigo = cfg["codigo"]

        for w in frame.winfo_children():
            w.destroy()

        if cfg["manual"]:
            entry.configure(state="normal")
            ctk.CTkButton(
                frame, text="💾 Guardar",
                fg_color=col["principal"], hover_color=col["principal_hover"],
                text_color="#0A192F", font=("Roboto Mono", 11),
                command=lambda: self._guardar_manual(
                    codigo, entry, lbl_fecha, lbl_estado, frame, cfg),
            ).pack(fill="x")

        elif cfg["fuente"] == "FIJO":
            ctk.CTkLabel(frame, text="Valor fijo del sistema",
                         font=("Roboto Mono", 9), text_color="#4A6FA5").pack()

        else:
            ctk.CTkButton(
                frame, text="🔄 Actualizar",
                fg_color="#1A3550", hover_color=col["tarjetas"],
                text_color=col["texto_oscuro"], font=("Roboto Mono", 11),
                command=lambda: self._actualizar_individual(
                    codigo, entry, lbl_fecha, lbl_estado),
            ).pack(fill="x", pady=(0, 4))

            ctk.CTkButton(
                frame, text="✏️ Editar",
                fg_color="#1A3550", hover_color=col["tarjetas"],
                text_color=col["texto_oscuro"], font=("Roboto Mono", 11),
                command=lambda: self._activar_edicion(
                    entry, codigo, lbl_fecha, lbl_estado, frame, cfg),
            ).pack(fill="x", pady=(4, 0))

    # ─── Acciones ─────────────────────────────────────────────────────────────

    def _actualizar_auto(self):
        self._estado_global("⏳ Consultando fuentes externas…")
        actualizar_en_background(
            callback=lambda: self.after(0, self._refrescar_desde_bd),
            usuario=self.usuario,
        )

    def _actualizar_individual(self, codigo, entry, lbl_fecha, lbl_estado):
        import threading
        lbl_estado.configure(text="⏳ Consultando…", text_color="#4A6FA5")

        def _tarea():
            try:
                if codigo == "USD":
                    usd, _ = _consultar_bcv()
                    guardar("USD", usd, tipo="AUTO", usuario=self.usuario)
                elif codigo == "EUR":
                    _, eur = _consultar_bcv()
                    guardar("EUR", eur, tipo="AUTO", usuario=self.usuario)
                elif codigo == "USDT":
                    usdt = _consultar_binance()
                    guardar("USDT", usdt, tipo="AUTO", usuario=self.usuario)
                self.after(0, lambda: self._refrescar_tarjeta(
                    codigo, entry, lbl_fecha, lbl_estado))
            except Exception as exc:
                msg = str(exc)
                con = sqlite3.connect(DB_NAME)
                con.execute("UPDATE monedas SET error=? WHERE codigo=?",
                            (msg, codigo))
                con.commit()
                con.close()
                self.after(0, lambda: (
                    lbl_estado.configure(
                        text=f"⚠ {msg}",
                        text_color=self.estilos["colores"]["error"]),
                    entry.configure(state="normal"),
                ))

        threading.Thread(target=_tarea, daemon=True).start()

    def _guardar_manual(self, codigo, entry, lbl_fecha, lbl_estado, frame, cfg):
        texto = entry.get().strip().replace(",", ".")
        try:
            valor = float(texto)
            guardar(codigo, valor, tipo="MANUAL", usuario=self.usuario)
            ahora = datetime.now().strftime("%d/%m/%Y %H:%M")
            lbl_fecha.configure(text=f"🕐 {ahora}")
            lbl_estado.configure(text="✅ Guardado", text_color="#00C896")
            if not cfg["manual"]:
                entry.configure(state="disabled")
            self._botones_normales(frame, cfg, entry, lbl_fecha, lbl_estado)
            if self._historial_visible:
                self._cargar_historial()
        except ValueError:
            lbl_estado.configure(text="⚠ Ingresa un número válido",
                                  text_color=self.estilos["colores"]["error"])

    def _activar_edicion(self, entry, codigo, lbl_fecha, lbl_estado, frame, cfg):
        col = self.estilos["colores"]
        entry.configure(state="normal")
        lbl_estado.configure(text="✏️ Edición manual activada",
                              text_color="#F0A500")

        for w in frame.winfo_children():
            w.destroy()

        ctk.CTkButton(
            frame, text="💾 Guardar",
            fg_color=col["principal"], hover_color=col["principal_hover"],
            text_color="#0A192F", font=("Roboto Mono", 11),
            command=lambda: self._guardar_manual(
                codigo, entry, lbl_fecha, lbl_estado, frame, cfg),
        ).pack(fill="x")

    def _refrescar_tarjeta(self, codigo, entry, lbl_fecha, lbl_estado):
        datos = leer_todas().get(codigo, {})
        entry.configure(state="normal")
        entry.delete(0, "end")
        entry.insert(0, f"{datos.get('tasa', 0.0):.4f}")
        entry.configure(state="disabled")
        lbl_fecha.configure(text=f"🕐 {datos.get('actualizado', '—')}")
        error = datos.get("error", "")
        if error:
            lbl_estado.configure(text=f"⚠ {error}",
                                  text_color=self.estilos["colores"]["error"])
        else:
            lbl_estado.configure(text="✅ Actualizado", text_color="#00C896")

    def _refrescar_desde_bd(self):
        datos_bd = leer_todas()
        for cfg in MONEDAS_CONFIG:
            codigo = cfg["codigo"]
            if cfg["manual"]:
                continue
            t = self.tarjetas.get(codigo)
            if not t:
                continue
            datos = datos_bd.get(codigo, {})
            t["entry"].configure(state="normal")
            t["entry"].delete(0, "end")
            t["entry"].insert(0, f"{datos.get('tasa', 0.0):.4f}")
            error = datos.get("error", "")
            if error:
                t["entry"].configure(state="normal")
                t["lbl_estado"].configure(
                    text=f"⚠ {error}",
                    text_color=self.estilos["colores"]["error"])
            else:
                t["entry"].configure(state="disabled")
                t["lbl_estado"].configure(text="✅ Actualizado",
                                           text_color="#00C896")
            t["lbl_fecha"].configure(
                text=f"🕐 {datos.get('actualizado', '—')}")
            self._botones_normales(
                t["frame_btns"], cfg,
                t["entry"], t["lbl_fecha"], t["lbl_estado"])

        if self._historial_visible:
            self._cargar_historial()

    def _estado_global(self, mensaje: str):
        for cfg in MONEDAS_CONFIG:
            if cfg["manual"]:
                continue
            t = self.tarjetas.get(cfg["codigo"])
            if t:
                t["lbl_estado"].configure(text=mensaje, text_color="#4A6FA5")

    # ─── Historial ────────────────────────────────────────────────────────────

    def _toggle_historial(self):
        if self._historial_visible:
            self._sep_hist.pack_forget()
            self._panel_hist.pack_forget()
            for w in self._panel_hist.winfo_children():
                w.destroy()
            self._historial_visible = False
        else:
            self._sep_hist.pack(fill="x", padx=30, pady=(20, 0))
            self._panel_hist.pack(fill="both", expand=True, padx=30, pady=(0, 20))
            self._historial_visible = True
            self._cargar_historial()

    def _cargar_historial(self):
        col = self.estilos["colores"]

        for w in self._panel_hist.winfo_children():
            w.destroy()

        # Título
        top = ctk.CTkFrame(self._panel_hist, fg_color="transparent")
        top.pack(fill="x", pady=(15, 8))
        ctk.CTkLabel(top, text="📋  Historial de Actualizaciones",
                     font=("Roboto Mono", 14, "bold"),
                     text_color=col["texto_oscuro"]).pack(side="left")

        # Tabs
        tabs = ctk.CTkFrame(self._panel_hist,
                             fg_color=col["tarjetas"], corner_radius=8)
        tabs.pack(fill="x", pady=(0, 8))

        etiquetas = {
            "TODOS": "🌐 Todos", "USD": "💵 USD", "EUR": "💶 EUR",
            "USDT": "🟡 USDT", "TASA_EXT": "⚙️ Tasa Ext.",
        }
        for codigo in CODIGOS_HISTORIAL:
            activo = (codigo == self._tab_activo)
            ctk.CTkButton(
                tabs,
                text=etiquetas.get(codigo, codigo),
                fg_color=col["principal"] if activo else "transparent",
                hover_color=col["principal_hover"] if activo else "#1A3550",
                text_color="#0A192F" if activo else col["texto_oscuro"],
                font=("Roboto Mono", 11, "bold" if activo else "normal"),
                width=110, height=30, corner_radius=6,
                command=lambda c=codigo: self._cambiar_tab(c),
            ).pack(side="left", padx=6, pady=6)

        # Cabecera de columnas
        cab = ctk.CTkFrame(self._panel_hist, fg_color="#0D2137", corner_radius=6)
        cab.pack(fill="x", pady=(0, 2))
        for i, t in enumerate(["Moneda", "Anterior", "Nueva", "Fecha",
                                "Tipo", "Usuario"]):
            peso = 3 if i == 3 else 2
            cab.columnconfigure(i, weight=peso)
            ctk.CTkLabel(cab, text=t,
                         font=("Roboto Mono", 11, "bold"),
                         text_color=col["principal"]).grid(
                row=0, column=i, sticky="ew", padx=10, pady=6)

        # Filas con scroll
        scroll = ctk.CTkScrollableFrame(self._panel_hist,
                                        fg_color="#0A192F",
                                        corner_radius=8, height=200)
        scroll.pack(fill="both", expand=True)
        for i in range(6):
            scroll.columnconfigure(i, weight=1)

        registros = leer_historial(200, codigo=self._tab_activo)
        if not registros:
            ctk.CTkLabel(scroll,
                         text="Sin registros para esta moneda aún.",
                         font=("Roboto Mono", 11),
                         text_color="#4A6FA5").grid(
                row=0, column=0, columnspan=6, pady=20)
            return

        for i, (cod, nombre, t_ant, t_nue, fecha, tipo, usuario) in \
                enumerate(registros):
            bg        = col["tarjetas"] if i % 2 == 0 else "#0D2137"
            variacion = t_nue - t_ant
            color_var = "#00C896" if variacion >= 0 else "#FF6B6B"
            flecha    = "▲" if variacion >= 0 else "▼"
            icono_t   = "🤖" if tipo == "AUTO" else "✋"
            color_t   = "#4A6FA5" if tipo == "AUTO" else "#F0A500"

            celdas = [
                (f"{nombre} ({cod})",   col["texto_oscuro"]),
                (f"{t_ant:.4f}",        "#6B8BAE"),
                (f"{flecha} {t_nue:.4f}", color_var),
                (fecha,                 "#6B8BAE"),
                (f"{icono_t} {tipo}",   color_t),
                (usuario,               "#C0C0C0"),
            ]
            for j, (texto, color) in enumerate(celdas):
                ctk.CTkLabel(scroll, text=texto,
                             font=("Roboto Mono", 10),
                             text_color=color,
                             fg_color=bg, corner_radius=0).grid(
                    row=i, column=j, sticky="ew", padx=8, pady=4)

    def _cambiar_tab(self, codigo: str):
        self._tab_activo = codigo
        self._cargar_historial()
