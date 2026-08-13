"""
modulos/ventas/sub_cxc.py
=========================
Submódulo Cuentas por Cobrar (CxC).

Lista las ventas a crédito con su saldo pendiente y permite registrar
abonos por cuota. Cada abono tiene su propio selector de moneda
(USD/EUR/USDT/VES/Tasa Externa), independiente de la moneda de crédito
de la venta; el monto se convierte a la moneda de crédito con las tasas
del día para llevar el saldo real.

Patrón: barra + lista scrollable + modal (igual que los demás submódulos).
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
    """Convierte un monto en <moneda> a USD usando las tasas."""
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
    """Convierte un monto en USD a <destino>."""
    if destino == "USD" or not monto_usd:
        return monto_usd
    t_usd = (tasas.get("USD", {}) or {}).get("tasa", 0) or 0
    bs = monto_usd * t_usd
    if destino == "VES":
        return bs
    t = (tasas.get(destino, {}) or {}).get("tasa", 0) or 0
    return (bs / t) if t > 0 else monto_usd


def _conv(monto, origen, destino, tasas):
    """Convierte <monto> de <origen> a <destino>."""
    if origen == destino or not monto:
        return monto
    return _de_usd(_a_usd(monto, origen, tasas), destino, tasas)


def _fmt(monto, moneda):
    return f'{MON_SIMB.get(moneda, "")} {monto:,.2f}'


def _trunc(texto, width_px):
    """Recorta el texto con '…' para que no exceda el ancho de su columna
    (evita que un nombre largo desalinee toda la tabla)."""
    s = str(texto or "")
    max_chars = max(4, int(width_px / 7.5))
    if len(s) > max_chars:
        return s[:max_chars - 1].rstrip() + "…"
    return s


class _ToolTip:
    """Muestra el texto completo en un globo al pasar el cursor."""
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
    """Celda de ancho fijo con texto truncado + tooltip del texto completo."""
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


class SubmoduloCxC(ctk.CTkFrame):
    """Submódulo de Cuentas por Cobrar — lista + modal de abonos."""

    COLS   = ["N° Venta", "Cliente", "Financiado", "Abonado", "Saldo", "Estado", ""]
    WIDTHS = [130, 300, 130, 130, 130, 120, 90]

    def __init__(self, parent, estilos, permisos=None):
        super().__init__(parent, corner_radius=0,
                         fg_color=estilos["colores"]["fondo_oscuro"])
        self.estilos  = estilos
        self.permisos = permisos or {}
        self.col      = estilos["colores"]
        self.fnt      = estilos["fuentes"]
        self._construir_ui()
        self.after(0, self.cargar_datos)

    # ─── UI ──────────────────────────────────────────────────────────────────

    def _construir_ui(self):
        col = self.col
        fnt = self.fnt

        bar = ctk.CTkFrame(self, height=52, corner_radius=0, fg_color="#020C1B")
        bar.pack(fill="x")
        bar.pack_propagate(False)

        ctk.CTkLabel(bar, text="💰  Cuentas por Cobrar",
                     font=fnt["titulo"],
                     text_color=col["principal"]).pack(side="left", padx=16, pady=8)

        self.solo_pend = ctk.BooleanVar(value=True)
        ctk.CTkSwitch(bar, text="Solo con saldo", variable=self.solo_pend,
                      font=fnt["normal"], progress_color=col["principal"],
                      command=self.cargar_datos).pack(side="right", padx=12, pady=8)

        self.busq_var = ctk.StringVar()
        ctk.CTkEntry(bar, textvariable=self.busq_var, width=240, height=32,
                     placeholder_text="🔍 Buscar por N°, cliente o RIF…"
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

        # Barra de resumen inferior
        self.resumen = ctk.CTkLabel(self, text="", font=fnt["normal"],
                                    text_color=col["texto_claro"])
        self.resumen.pack(anchor="e", padx=20, pady=(0, 6))

        self.busq_var.trace_add("write", lambda *_: self.cargar_datos())

    # ─── Datos ───────────────────────────────────────────────────────────────

    def cargar_datos(self, *_):
        from core.database import listar_cxc
        col = self.col
        fnt = self.fnt

        for w in self.scroll.winfo_children():
            w.destroy()

        try:
            rows = listar_cxc(self.busq_var.get(),
                              solo_pendientes=self.solo_pend.get())
        except Exception as e:
            ctk.CTkLabel(self.scroll, text=f"Error al cargar: {e}",
                         text_color="#E63946", font=fnt["normal"]).pack(pady=20)
            return

        if not rows:
            ctk.CTkLabel(self.scroll,
                         text="No hay ventas a crédito con saldo pendiente.",
                         text_color="#4A6FA5", font=fnt["normal"],
                         justify="center").pack(pady=30)
            self.resumen.configure(text="")
            return

        for i, r in enumerate(rows):
            bg = col["tarjetas"] if i % 2 == 0 else col["fondo_oscuro"]
            fila = ctk.CTkFrame(self.scroll, corner_radius=0, fg_color=bg, height=34)
            fila.pack(fill="x")
            fila.pack_propagate(False)

            mc = r.get("moneda_credito", "USD") or "USD"
            saldo = r["saldo"]
            if saldo <= 0.009:
                est_txt, est_col = "✅ Pagada", col["principal"]
            elif r["abonado"] > 0.009:
                est_txt, est_col = "◐ Parcial", "#F4A100"
            else:
                est_txt, est_col = "● Pendiente", "#E63946"

            vals = [
                (r["numero"],                        col["texto_claro"]),
                (r["cliente_nombre"],                col["texto_claro"]),
                (_fmt(r["total_cuotas"], mc),        "#8FA9C8"),
                (_fmt(r["abonado"], mc),             col["principal"]),
                (_fmt(saldo, mc),                    est_col),
                (est_txt,                            est_col),
            ]
            for (v, tc), w in zip(vals, self.WIDTHS[:-1]):
                _cell(fila, v, w, 34, tc, fnt["normal"])

            btn_f = ctk.CTkFrame(fila, width=90, corner_radius=0,
                                 fg_color="transparent")
            btn_f.pack(side="left")
            btn_f.pack_propagate(False)
            ctk.CTkButton(btn_f, text="💵 Abonar", width=82, height=28,
                          fg_color=col["principal"], text_color="#0A192F",
                          hover_color=col.get("principal_hover", "#00C8D4"),
                          command=lambda vid=r["id"]: self._abrir_detalle(vid)
                          ).pack(side="right", padx=4)

        tot_fin = sum(r["total_cuotas"] for r in rows)
        tot_ab  = sum(r["abonado"] for r in rows)
        tot_sal = sum(r["saldo"] for r in rows)
        self.resumen.configure(
            text=f"Cuentas: {len(rows)}   |   Financiado: {tot_fin:,.2f}   "
                 f"Abonado: {tot_ab:,.2f}   Saldo: {tot_sal:,.2f}   "
                 f"(montos en moneda de cada crédito)")

    # ─── MODAL DETALLE / ABONO ─────────────────────────────────────────────────

    def _abrir_detalle(self, venta_id):
        from core.database import get_cxc_detalle
        col = self.col
        fnt = self.fnt

        det = get_cxc_detalle(venta_id)
        if not det:
            messagebox.showerror("Error", "No se encontró la venta.")
            return
        mc = det.get("moneda_credito", "USD") or "USD"

        win = ctk.CTkToplevel(self)
        win.title(f"Cuenta por Cobrar — {det.get('numero','')}")
        win.geometry("760x680")
        win.configure(fg_color=col["fondo_oscuro"])
        win.transient(self.winfo_toplevel())
        win.lift()
        win.after(80, lambda: (win.lift(), win.focus_force(), win.grab_set()))

        # Encabezado
        head = ctk.CTkFrame(win, corner_radius=0, fg_color="#020C1B")
        head.pack(fill="x")
        ctk.CTkLabel(head,
                     text=f"💰  {det.get('numero','')}   ·   "
                          f"{det.get('cliente_nombre','') or '(Sin cliente)'}",
                     font=fnt["subtitulo"], text_color=col["principal"]
                     ).pack(anchor="w", padx=16, pady=(12, 2))
        ctk.CTkLabel(head,
                     text=f"Financiado: {_fmt(det['total_cuotas'], mc)}    "
                          f"Abonado: {_fmt(det['abonado'], mc)}    "
                          f"Saldo: {_fmt(det['saldo'], mc)}    "
                          f"Moneda crédito: {mc}",
                     font=fnt["normal"], text_color=col["texto_claro"]
                     ).pack(anchor="w", padx=16, pady=(0, 12))

        body = ctk.CTkScrollableFrame(win, corner_radius=0,
                                      fg_color=col["fondo_oscuro"])
        body.pack(fill="both", expand=True, padx=12, pady=(8, 4))

        # ── Cuotas ──
        ctk.CTkLabel(body, text="Plan de cuotas", font=fnt["normal"],
                     text_color=col["principal"]).pack(anchor="w", pady=(4, 2))
        ch = ctk.CTkFrame(body, corner_radius=0, fg_color="#0A192F", height=30)
        ch.pack(fill="x")
        ch.pack_propagate(False)
        for c, w in zip(["#", "Vencimiento", "Monto", "Abonado", "Saldo", "Estado"],
                        [50, 150, 130, 130, 130, 120]):
            ctk.CTkLabel(ch, text=c, width=w, anchor="center",
                         text_color=col["texto_claro"], font=fnt["normal"]
                         ).pack(side="left")

        est_colores = {"Pagada": col["principal"], "Parcial": "#F4A100",
                       "Vencida": "#E63946", "Pendiente": "#8FA9C8"}
        for i, c in enumerate(det["cuotas"]):
            bg = col["tarjetas"] if i % 2 == 0 else col["fondo_oscuro"]
            f = ctk.CTkFrame(body, corner_radius=0, fg_color=bg, height=30)
            f.pack(fill="x")
            f.pack_propagate(False)
            ec = est_colores.get(c["estado"], "#8FA9C8")
            vals = [
                (str(c["numero_cuota"]),      col["texto_claro"], 50),
                (c.get("fecha_venc", "") or "—", col["texto_claro"], 150),
                (_fmt(c["monto"], mc),        "#8FA9C8", 130),
                (_fmt(c["abonado"], mc),      col["principal"], 130),
                (_fmt(c["saldo"], mc),        ec, 130),
                (c["estado"],                 ec, 120),
            ]
            for (v, tc, w) in vals:
                ctk.CTkLabel(f, text=v, width=w, anchor="center",
                             text_color=tc, font=fnt["normal"]).pack(side="left")

        # ── Historial de abonos ──
        ctk.CTkLabel(body, text="Historial de abonos", font=fnt["normal"],
                     text_color=col["principal"]).pack(anchor="w", pady=(14, 2))
        if not det["abonos"]:
            ctk.CTkLabel(body, text="Aún no hay abonos registrados.",
                         text_color="#4A6FA5", font=fnt["normal"]).pack(anchor="w")
        else:
            for a in det["abonos"]:
                cuota_txt = (f'Cuota {self._cuota_num(det, a["cuota_id"])}'
                             if a.get("cuota_id") else "General")
                orig = (f'{_fmt(a["monto"], a["moneda"])} '
                        f'→ {_fmt(a["monto_credito"], mc)}'
                        if a["moneda"] != mc else _fmt(a["monto"], mc))
                fa = ctk.CTkFrame(body, corner_radius=6, fg_color=col["tarjetas"])
                fa.pack(fill="x", pady=2)
                ctk.CTkLabel(
                    fa,
                    text=f'{a.get("fecha","")}  ·  {cuota_txt}  ·  {orig}  ·  '
                         f'{a.get("metodo_nombre","") or "—"}  ·  '
                         f'{a.get("usuario","") or ""}',
                    font=fnt["normal"], text_color=col["texto_claro"],
                    anchor="w").pack(side="left", padx=8, pady=4)
                ctk.CTkButton(fa, text="🗑", width=34, height=26,
                              fg_color="#1A3550",
                              hover_color=col.get("error", "#E63946"),
                              text_color=col.get("error", "#E63946"),
                              command=lambda aid=a["id"]:
                                  self._eliminar_abono(aid, win, venta_id)
                              ).pack(side="right", padx=6, pady=3)

        # ── Formulario de abono (footer fijo) ──
        if det["saldo"] > 0.009:
            self._form_abono(win, det, mc)
        else:
            fin = ctk.CTkFrame(win, height=52, corner_radius=0, fg_color="#020C1B")
            fin.pack(fill="x", side="bottom")
            fin.pack_propagate(False)
            ctk.CTkLabel(fin, text="✅ Esta cuenta está totalmente pagada.",
                         font=fnt["normal"], text_color=col["principal"]
                         ).pack(side="left", padx=16, pady=14)
            ctk.CTkButton(fin, text="Cerrar", width=110, height=34,
                          fg_color="#1A3550", hover_color="#24476B",
                          text_color=col["texto_claro"],
                          command=win.destroy).pack(side="right", padx=16, pady=9)

    def _cuota_num(self, det, cuota_id):
        for c in det["cuotas"]:
            if c["id"] == cuota_id:
                return c["numero_cuota"]
        return "?"

    def _form_abono(self, win, det, mc):
        col = self.col
        fnt = self.fnt
        from core.database import listar_metodos_pago

        footer = ctk.CTkFrame(win, corner_radius=0, fg_color="#020C1B")
        footer.pack(fill="x", side="bottom")

        row1 = ctk.CTkFrame(footer, fg_color="transparent")
        row1.pack(fill="x", padx=14, pady=(10, 2))

        # Cuota destino
        ctk.CTkLabel(row1, text="Cuota", font=fnt["normal"],
                     text_color=col["texto_claro"]).pack(side="left")
        pend = [c for c in det["cuotas"] if c["saldo"] > 0.009]
        cuota_opts = ["(Distribuir automáticamente)"] + [
            f'#{c["numero_cuota"]} — saldo {_fmt(c["saldo"], mc)}' for c in pend]
        cuota_var = ctk.StringVar(value=cuota_opts[0])
        ctk.CTkOptionMenu(row1, variable=cuota_var, values=cuota_opts,
                          width=230, height=32, fg_color=col["tarjetas"],
                          button_color=col["tarjetas"]).pack(side="left", padx=(6, 16))

        # Método de pago
        ctk.CTkLabel(row1, text="Método", font=fnt["normal"],
                     text_color=col["texto_claro"]).pack(side="left")
        try:
            metodos = [m["nombre"] for m in listar_metodos_pago("", "")]
        except Exception:
            metodos = []
        met_opts = ["(Ninguno)"] + metodos
        met_var = ctk.StringVar(value=met_opts[0])
        ctk.CTkOptionMenu(row1, variable=met_var, values=met_opts,
                          width=180, height=32, fg_color=col["tarjetas"],
                          button_color=col["tarjetas"]).pack(side="left", padx=6)

        row2 = ctk.CTkFrame(footer, fg_color="transparent")
        row2.pack(fill="x", padx=14, pady=(4, 12))

        # Monto
        ctk.CTkLabel(row2, text="Monto", font=fnt["normal"],
                     text_color=col["texto_claro"]).pack(side="left")
        e_monto = ctk.CTkEntry(row2, width=130, height=34,
                               placeholder_text="0.00")
        e_monto.pack(side="left", padx=(6, 6))

        # Moneda del abono (propio selector, independiente del crédito)
        mon_var = ctk.StringVar(value=_MON_LABEL.get(mc, MONEDAS[0][1]))
        ctk.CTkOptionMenu(row2, variable=mon_var,
                          values=[l for _, l in MONEDAS],
                          width=170, height=34, fg_color=col["tarjetas"],
                          button_color=col["tarjetas"]).pack(side="left", padx=6)

        # Equivalencia en la moneda de crédito
        equiv_lbl = ctk.CTkLabel(row2, text="", font=fnt["normal"],
                                 text_color=col["principal"])
        equiv_lbl.pack(side="left", padx=10)

        tasas = _cargar_tasas()

        def _monto_credito():
            try:
                monto = float(e_monto.get().replace(",", "").strip() or 0)
            except ValueError:
                return None, None
            moneda = _MON_FROM_LABEL.get(mon_var.get(), "USD")
            return monto, round(_conv(monto, moneda, mc, tasas), 2)

        def _refrescar_equiv(*_):
            monto, mcred = _monto_credito()
            if monto is None:
                equiv_lbl.configure(text="⚠ monto inválido")
                return
            moneda = _MON_FROM_LABEL.get(mon_var.get(), "USD")
            if moneda == mc:
                equiv_lbl.configure(text="")
            else:
                equiv_lbl.configure(text=f"≈ {_fmt(mcred, mc)}")

        e_monto.bind("<KeyRelease>", _refrescar_equiv)
        mon_var.trace_add("write", _refrescar_equiv)

        def _registrar():
            from core.database import registrar_abono
            monto, mcred = _monto_credito()
            if monto is None or monto <= 0:
                messagebox.showwarning("Monto inválido",
                                       "Indica un monto mayor a cero.", parent=win)
                return
            moneda = _MON_FROM_LABEL.get(mon_var.get(), "USD")
            # Cuota destino
            sel = cuota_var.get()
            cuota_id = None
            if sel != cuota_opts[0]:
                idx = cuota_opts.index(sel) - 1
                cuota_id = pend[idx]["id"]
            metodo = "" if met_var.get() == met_opts[0] else met_var.get()
            usuario = getattr(self, "usuario_actual", "") or \
                self.permisos.get("_usuario", "") if isinstance(self.permisos, dict) else ""
            r = registrar_abono(det["id"], cuota_id, monto, moneda, mcred,
                                metodo, usuario, "")
            if r == -1:
                messagebox.showerror("Error", "No se pudo registrar el abono.",
                                     parent=win)
                return
            win.destroy()
            self.cargar_datos()
            self._abrir_detalle(det["id"])

        ctk.CTkButton(row2, text="💾 Registrar abono", width=180, height=36,
                      fg_color=col["principal"], text_color="#0A192F",
                      hover_color=col.get("principal_hover", "#00C8D4"),
                      command=_registrar).pack(side="right", padx=6)
        ctk.CTkButton(row2, text="Cerrar", width=100, height=36,
                      fg_color="#1A3550", hover_color="#24476B",
                      text_color=col["texto_claro"],
                      command=win.destroy).pack(side="right", padx=6)

    def _eliminar_abono(self, abono_id, win, venta_id):
        from core.database import eliminar_abono
        if messagebox.askyesno("Eliminar abono",
                               "¿Eliminar este abono? El saldo se recalculará.",
                               parent=win):
            eliminar_abono(abono_id)
            win.destroy()
            self.cargar_datos()
            self._abrir_detalle(venta_id)
