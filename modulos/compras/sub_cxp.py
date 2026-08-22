"""
modulos/compras/sub_cxp.py
==========================
Submódulo Cuentas por Pagar (CxP).

Lista las compras a crédito con saldo pendiente y permite registrar abonos.
A diferencia de CxC, NO hay cuotas con fechas de vencimiento —
es un saldo único que se va abonando.

Incluye pie de página con totales (filtrados / generales).
"""
import datetime
import customtkinter as ctk
from tkinter import messagebox


MONEDAS = [
    ("USD",      "USD  $  (Dólar)"),
    ("EUR",      "EUR  €  (Euro)"),
    ("USDT",     "USDT ₮  (Tether)"),
    ("VES",      "VES  Bs  (Bolívar)"),
    ("TASA_EXT", "Tasa Externa"),
]
_MON_LABEL      = {c: l for c, l in MONEDAS}
_MON_FROM_LABEL = {l: c for c, l in MONEDAS}
MON_SIMB = {"USD": "$", "EUR": "€", "VES": "Bs.", "USDT": "₮", "TASA_EXT": "★"}


def _cargar_tasas():
    try:
        from modulos.monedas.db import leer_todas
        return leer_todas() or {}
    except Exception:
        return {}


def _a_usd(monto, moneda, tasas):
    if moneda == "USD" or not monto:
        return monto
    t_usd = (tasas.get("USD", {}) or {}).get("tasa", 0) or 0
    if moneda == "VES":
        return (monto / t_usd) if t_usd > 0 else monto
    t = (tasas.get(moneda, {}) or {}).get("tasa", 0) or 0
    if t_usd <= 0 or t <= 0:
        return monto
    return (monto * t) / t_usd


def _de_usd(monto_usd, destino, tasas):
    if destino == "USD" or not monto_usd:
        return monto_usd
    t_usd = (tasas.get("USD", {}) or {}).get("tasa", 0) or 0
    bs = monto_usd * t_usd
    if destino == "VES":
        return bs
    t = (tasas.get(destino, {}) or {}).get("tasa", 0) or 0
    return (bs / t) if t > 0 else monto_usd


def _conv(monto, origen, destino, tasas):
    if origen == destino or not monto:
        return monto
    return _de_usd(_a_usd(monto, origen, tasas), destino, tasas)


def _fmt(monto, moneda):
    return f'{MON_SIMB.get(moneda, "")} {monto:,.2f}'


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
    frame.pack(side="left")
    frame.pack_propagate(False)
    lbl = ctk.CTkLabel(frame, text=disp, anchor="center",
                       text_color=text_color, font=font)
    lbl.pack(fill="both", expand=True)
    if disp != str(full_text or ""):
        _ToolTip(lbl, str(full_text))
    return frame


class SubmoduloCxP(ctk.CTkFrame):
    COLS   = ["Número", "Fecha", "Proveedor", "Saldo", "Abonado", ""]
    WIDTHS = [130, 100, 260, 120, 120, 118]

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

        ctk.CTkLabel(bar, text="💳  Cuentas por Pagar", font=fnt["titulo"],
                     text_color=col["principal"]).pack(side="left", padx=16, pady=8)

        self.busq_var = ctk.StringVar()
        ctk.CTkEntry(bar, textvariable=self.busq_var, width=260, height=32,
                     placeholder_text="🔍 Buscar por número o proveedor…"
                     ).pack(side="right", padx=12, pady=10)

        # Toggle "Solo con saldo"
        self.solo_saldo_var = ctk.StringVar(value="1")
        ctk.CTkSwitch(bar, text="Solo con saldo", variable=self.solo_saldo_var,
                      onvalue="1", offvalue="0",
                      text_color=col["texto_claro"], font=fnt["normal"],
                      command=lambda: self.cargar_datos(self.busq_var.get())
                      ).pack(side="right", padx=(0, 8))

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

        # ── Pie de página con totales ──────────────────────────────────────
        self.footer = ctk.CTkFrame(cont, height=28, corner_radius=0,
                                     fg_color="transparent")
        self.footer.pack(fill="x", pady=(4, 0))
        self.footer.pack_propagate(False)

        self.lbl_footer_totales = ctk.CTkLabel(
            self.footer, text="",
            text_color=col.get("texto_oscuro", "#94A3B8"),
            font=("Roboto Mono", 10),
        )
        self.lbl_footer_totales.pack(side="right", padx=14)

        self.busq_var.trace_add("write",
                                 lambda *_: self.cargar_datos(self.busq_var.get()))

    def cargar_datos(self, filtro: str = ""):
        from core.database import listar_cxp
        col, fnt = self.col, self.fnt

        for w in self.scroll.winfo_children():
            w.destroy()

        solo_pendientes = self.solo_saldo_var.get() == "1"

        try:
            rows = listar_cxp(filtro, solo_pendientes=solo_pendientes)
        except Exception as e:
            ctk.CTkLabel(self.scroll, text=f"Error al cargar: {e}",
                         text_color="#E63946", font=fnt["normal"]).pack(pady=20)
            self.lbl_footer_totales.configure(text="")
            return

        # ── Render filas ──
        for i, r in enumerate(rows):
            bg = col["tarjetas"] if i % 2 == 0 else col["fondo_oscuro"]
            fila = ctk.CTkFrame(self.scroll, corner_radius=0, fg_color=bg, height=34)
            fila.pack(fill="x")
            fila.pack_propagate(False)

            simb = MON_SIMB.get(r.get("moneda_credito", "USD"), "$")
            saldo  = r["saldo"]
            abonad = r["abonado"]
            vals = [
                (r["numero"],                      col["texto_claro"]),
                (r["fecha"],                       col["texto_claro"]),
                (r["proveedor_nombre"],            col["texto_claro"]),
                (f"{simb} {saldo:,.2f}",          "#E63946" if saldo > 0.01 else col["principal"]),
                (f"{simb} {abonad:,.2f}",         col["principal"]),
            ]
            for (v, tc), w in zip(vals, self.WIDTHS[:-1]):
                _cell(fila, v, w, 34, tc, fnt["normal"])

            btn_f = ctk.CTkFrame(fila, width=118, corner_radius=0,
                                 fg_color="transparent")
            btn_f.pack(side="left")
            btn_f.pack_propagate(False)

            ctk.CTkButton(btn_f, text="💵 Abonar", width=90, height=28,
                          fg_color=col["principal"],
                          hover_color=col.get("principal_hover", "#00C8D4"),
                          text_color="#0A192F",
                          command=lambda rid=r["id"]: self._abrir_abono(rid)
                          ).pack(side="right", padx=2)
            ctk.CTkButton(btn_f, text="👁", width=30, height=28,
                          fg_color="#1A3550",
                          hover_color=col["principal"],
                          text_color=col["texto_claro"],
                          command=lambda rid=r["id"]: self._ver_detalle(rid)
                          ).pack(side="right", padx=2)

        # ── Pie: totales ──
        total_deuda = sum(r["total"] for r in rows)
        total_abonado = sum(r["abonado"] for r in rows)
        total_saldo = sum(r["saldo"] for r in rows)
        n = len(rows)

        self.lbl_footer_totales.configure(
            text=f"Cuentas: {n}  │  "
                 f"Deuda: {total_deuda:,.2f}  │  "
                 f"Abonado: {total_abonado:,.2f}  │  "
                 f"Saldo: {total_saldo:,.2f} "
                 f"(montos en moneda de cada crédito)"
        )

    def _ver_detalle(self, compra_id):
        from core.database import get_cxp_detalle
        col, fnt = self.col, self.fnt
        d = get_cxp_detalle(compra_id)
        if not d:
            messagebox.showerror("Error", "No se pudo cargar el detalle.")
            return

        modal = ctk.CTkToplevel(self)
        modal.title(f"CxP — {d['numero']}")
        modal.geometry("700x520")
        modal.configure(fg_color=col["fondo_oscuro"])
        modal.transient(self.winfo_toplevel())
        modal.lift()
        modal.after(60, lambda: (modal.lift(), modal.focus_force(),
                                 modal.grab_set()))

        body = ctk.CTkScrollableFrame(modal, corner_radius=0,
                                      fg_color=col["fondo_oscuro"])
        body.pack(fill="both", expand=True, padx=16, pady=12)

        simb = MON_SIMB.get(d.get("moneda_credito", "USD"), "$")
        total = d.get("total", 0)
        abonad = d.get("abonado", 0)
        saldo  = d.get("saldo", 0)

        info = ctk.CTkFrame(body, fg_color=col["tarjetas"], corner_radius=8)
        info.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(info, text=f"Proveedor: {d.get('proveedor_nombre', '')}",
                     text_color=col["texto_claro"], font=fnt["normal"]
                     ).pack(anchor="w", padx=12, pady=(8, 2))
        ctk.CTkLabel(info, text=f"Total compra: {simb} {total:,.2f}  |  "
                                f"Abonado: {simb} {abonad:,.2f}  |  "
                                f"Saldo: {simb} {saldo:,.2f}",
                     text_color=col["principal"], font=fnt["subtitulo"]
                     ).pack(anchor="w", padx=12, pady=(2, 8))

        ctk.CTkLabel(body, text="Pagos iniciales", text_color=col["texto_claro"],
                     font=fnt["subtitulo"]).pack(anchor="w", pady=(8, 2))
        for p in d.get("pagos", []):
            ctk.CTkLabel(body,
                         text=f'  💳 {p["metodo_nombre"]} — '
                              f'{MON_SIMB.get(p["moneda"], "")} {p["monto"]:,.2f}',
                         text_color=col["texto_claro"],
                         font=fnt["normal"]).pack(anchor="w")

        ctk.CTkLabel(body, text="Abonos registrados", text_color=col["texto_claro"],
                     font=fnt["subtitulo"]).pack(anchor="w", pady=(12, 2))
        for a in d.get("abonos", []):
            line = (f'  📅 {a["fecha"]} — '
                    f'{MON_SIMB.get(a["moneda"], "")} {a["monto_credito"]:,.2f} '
                    f'({a["moneda"]})')
            if a.get("observaciones"):
                line += f'  |  {a["observaciones"]}'
            ctk.CTkLabel(body, text=line,
                         text_color=col["texto_claro"],
                         font=fnt["normal"]).pack(anchor="w")

    def _abrir_abono(self, compra_id):
        from core.database import (get_cxp_detalle, registrar_abono_cxp,
                                   eliminar_abono_cxp, listar_metodos_pago)
        from core.session import get_usuario_actual
        col, fnt = self.col, self.fnt
        tasas = _cargar_tasas()
        d = get_cxp_detalle(compra_id)
        if not d:
            messagebox.showerror("Error", "No se pudo cargar el detalle.")
            return
        if d["saldo"] <= 0.01:
            messagebox.showinfo("CxP", "Esta compra ya está totalmente pagada.")
            return

        modal = ctk.CTkToplevel(self)
        modal.title(f"Abonar — {d['numero']}")
        modal.geometry("560x480")
        modal.configure(fg_color=col["fondo_oscuro"])
        modal.transient(self.winfo_toplevel())
        modal.lift()
        modal.after(60, lambda: (modal.lift(), modal.focus_force(),
                                 modal.grab_set()))

        body = ctk.CTkScrollableFrame(modal, corner_radius=0,
                                      fg_color=col["fondo_oscuro"])
        body.pack(fill="both", expand=True, padx=16, pady=12)

        simb = MON_SIMB.get(d.get("moneda_credito", "USD"), "$")
        ctk.CTkLabel(body, text=f"Proveedor: {d.get('proveedor_nombre', '')}",
                     text_color=col["texto_claro"], font=fnt["normal"]
                     ).pack(anchor="w")
        ctk.CTkLabel(body, text=f"Saldo pendiente: {simb} {d['saldo']:,.2f}",
                     text_color="#E63946", font=fnt["subtitulo"]
                     ).pack(anchor="w", pady=(0, 12))

        # monto del abono
        row1 = ctk.CTkFrame(body, fg_color="transparent")
        row1.pack(fill="x", pady=(4, 0))
        ctk.CTkLabel(row1, text="Monto del abono:", text_color=col["texto_claro"],
                     font=fnt["normal"]).pack(side="left")
        e_monto = ctk.CTkEntry(row1, width=120, height=32)
        e_monto.pack(side="left", padx=(8, 0))
        e_monto.insert(0, f'{d["saldo"]:.2f}')

        ctk.CTkLabel(row1, text="Moneda:", text_color=col["texto_claro"],
                     font=fnt["normal"]).pack(side="left", padx=(12, 0))
        cb_mon = ctk.CTkComboBox(row1, values=[l for _, l in MONEDAS],
                                 width=180, state="readonly")
        cb_mon.pack(side="left", padx=(4, 0))
        cb_mon.set(_MON_LABEL.get(d.get("moneda_credito", "USD"),
                                  MONEDAS[0][1]))

        # método de pago
        metodos = [m for m in listar_metodos_pago() if m.get("activo", 1)]
        met_labels = [f'{m["nombre"]} ({m["moneda"]})' for m in metodos]
        _met_by_label = {f'{m["nombre"]} ({m["moneda"]})': m for m in metodos}

        row2 = ctk.CTkFrame(body, fg_color="transparent")
        row2.pack(fill="x", pady=(8, 0))
        ctk.CTkLabel(row2, text="Método de pago:", text_color=col["texto_claro"],
                     font=fnt["normal"]).pack(side="left")
        cb_met = ctk.CTkComboBox(row2, values=(met_labels or ["(Sin métodos)"]),
                                 width=260, state="readonly")
        cb_met.pack(side="left", padx=(8, 0))
        cb_met.set(met_labels[0] if met_labels else "(Sin métodos)")

        # observaciones
        ctk.CTkLabel(body, text="Observaciones:", text_color=col["texto_claro"],
                     font=fnt["normal"]).pack(anchor="w", pady=(8, 2))
        e_obs = ctk.CTkEntry(body, width=480, height=32)
        e_obs.pack(anchor="w")

        # equivalencia
        eq_var = ctk.StringVar(value="")
        eq_lbl = ctk.CTkLabel(body, textvariable=eq_var,
                              text_color=col["principal"], font=fnt["normal"])
        eq_lbl.pack(anchor="w", pady=(4, 0))

        def _calc_equiv(*_):
            try:
                m = float(e_monto.get() or 0)
            except ValueError:
                m = 0
            orig = _MON_FROM_LABEL.get(cb_mon.get(), "USD")
            dest = d.get("moneda_credito", "USD")
            val = _conv(m, orig, dest, tasas)
            eq_var.set(f"Equivalente en crédito: {MON_SIMB.get(dest, '')} {val:,.2f} {dest}")

        e_monto.bind("<KeyRelease>", _calc_equiv)
        cb_mon.configure(command=lambda v: _calc_equiv())
        _calc_equiv()

        # historial de abonos
        ctk.CTkFrame(body, height=1, fg_color=col["principal"]).pack(
            fill="x", pady=(12, 4))
        ctk.CTkLabel(body, text="Historial de abonos", text_color=col["principal"],
                     font=fnt["subtitulo"]).pack(anchor="w")

        for a in d.get("abonos", []):
            f = ctk.CTkFrame(body, fg_color=col["tarjetas"], corner_radius=4)
            f.pack(fill="x", pady=2)
            ctk.CTkLabel(f,
                         text=f'📅 {a["fecha"]} — '
                              f'{MON_SIMB.get(a["moneda"], "")} '
                              f'{a["monto_credito"]:,.2f}  |  '
                              f'{a.get("observaciones", "")}',
                         text_color=col["texto_claro"],
                         font=fnt["normal"]).pack(side="left", padx=8)
            ctk.CTkButton(f, text="🗑", width=30, height=22,
                          fg_color="transparent",
                          hover_color=col.get("error", "#E63946"),
                          text_color=col.get("error", "#E63946"),
                          command=lambda aid=a["id"]: _del_abono(aid)
                          ).pack(side="right", padx=4)

        footer = ctk.CTkFrame(modal, height=64, corner_radius=0, fg_color="#020C1B")
        footer.pack(side="bottom", fill="x")
        footer.pack_propagate(False)
        err_lbl = ctk.CTkLabel(footer, text="", text_color="#E63946",
                               font=fnt["normal"])
        err_lbl.pack(side="left", padx=20)

        def _guardar_abono():
            try:
                monto = float(e_monto.get() or 0)
            except ValueError:
                err_lbl.configure(text="Monto inválido.")
                return
            if monto <= 0:
                err_lbl.configure(text="El monto debe ser mayor a cero.")
                return
            if monto > d["saldo"] + 0.01:
                err_lbl.configure(text="El abono no puede superar el saldo.")
                return

            mon_orig = _MON_FROM_LABEL.get(cb_mon.get(), "USD")
            mon_cred = d.get("moneda_credito", "USD")
            monto_cred = round(_conv(monto, mon_orig, mon_cred, tasas), 2)

            sel = cb_met.get()
            met = _met_by_label.get(sel)
            met_nombre = met["nombre"] if met else sel

            ok = registrar_abono_cxp(
                compra_id=compra_id,
                monto=monto,
                moneda=mon_orig,
                monto_credito=monto_cred,
                metodo_nombre=met_nombre,
                usuario=get_usuario_actual() or "",
                observaciones=e_obs.get().strip(),
            )
            if ok > 0:
                modal.destroy()
                self.cargar_datos(self.busq_var.get())
            else:
                err_lbl.configure(text="Error al registrar el abono.")

        def _del_abono(aid):
            if messagebox.askyesno("Eliminar abono", "¿Eliminar este abono?"):
                eliminar_abono_cxp(aid)
                modal.destroy()
                self._abrir_abono(compra_id)

        ctk.CTkButton(footer, text="💾 Registrar Abono",
                      fg_color=col["principal"], text_color="#0A192F",
                      hover_color=col.get("principal_hover", "#00C8D4"),
                      width=200, height=40,
                      command=_guardar_abono).pack(side="right", padx=20, pady=12)
