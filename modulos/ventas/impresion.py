"""
modulos/ventas/impresion.py
===========================
Generación e impresión de cotizaciones.

Arma un documento HTML autocontenido (logo embebido en base64) con los datos
de la cotización y lo abre en el navegador predeterminado, que ofrece el
diálogo de impresión (Ctrl+P) o guardado como PDF.

Uso:
    from .impresion import imprimir_cotizacion
    imprimir_cotizacion(cot_id)
"""
import os
import base64
import tempfile
import datetime
import webbrowser

# ── Datos de la empresa ─────────────────────────────────────────────────────
# Se cargan desde la BD (módulo Archivos → Empresa). Este dict es sólo el
# respaldo por defecto si la BD aún no tiene datos.
EMPRESA = {
    "nombre":    "CIGG SYSTEMS",
    "eslogan":   "Tech & Cyber Security",
    "rif":       "",
    "direccion": "",
    "telefono":  "",
    "correo":    "",
    "ciudad":    "Caracas",
    "logo_path": "",
}


def _get_empresa() -> dict:
    """Lee los datos de empresa desde la BD; usa EMPRESA como respaldo."""
    try:
        from core.database import obtener_empresa
        datos = obtener_empresa() or {}
    except Exception:
        datos = {}
    base = dict(EMPRESA)
    for k, v in datos.items():
        if v not in (None, ""):
            base[k] = v
    return base

_SIMB = {"USD": "$", "USDT": "USDT", "EUR": "EUR", "VES": "Bs", "Bs": "Bs"}

# Moneda base de cada tipo de ítem (igual que en sub_cotizaciones.py)
TIPO_MONEDA = {"Inventario": "USDT", "Máquina Fiscal": "USDT", "Sistema": "EUR"}
SIMB_ITEM   = {"USD": "$", "EUR": "€", "USDT": "₮"}
MON_SIMB    = {"USD": "$", "EUR": "€", "VES": "Bs.", "USDT": "₮", "TASA_EXT": "★"}


def _cargar_tasas():
    """Lee las tasas actuales; dict vacío si falla."""
    try:
        from modulos.monedas.db import leer_todas
        return leer_todas() or {}
    except Exception:
        return {}


def _a_usd(precio, moneda_item, tasas):
    """Convierte un precio en su moneda base (USDT/EUR/USD) a USD."""
    if moneda_item == "USD" or precio <= 0:
        return precio
    t_usd = (tasas.get("USD", {}) or {}).get("tasa", 0) or 0
    t     = (tasas.get(moneda_item, {}) or {}).get("tasa", 0) or 0
    if t_usd <= 0 or t <= 0:
        return precio
    return (precio * t) / t_usd          # nativo → Bs → USD


def _convertir(total_usd, destino, tasas):
    """USD → destino usando tasas en Bs. (tasa = Bs por unidad)."""
    t_usd = (tasas.get("USD", {}) or {}).get("tasa", 0) or 0
    total_bs = total_usd * t_usd
    if destino == "VES":
        return total_bs
    t = (tasas.get(destino, {}) or {}).get("tasa", 0) or 0
    return (total_bs / t) if t > 0 else 0.0


def _logo_base64(logo_path: str = "") -> str:
    """Devuelve el logo como data-URI base64, o cadena vacía si no existe.

    Prioriza el logo configurado por la empresa (logo_path); si no existe o
    no está definido, usa imagenes/logo_completo.png por compatibilidad.
    """
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    candidatas = []
    if logo_path:
        candidatas.append(logo_path)
        candidatas.append(os.path.join(base, "imagenes", logo_path))
    candidatas.append(os.path.join(base, "imagenes", "logo_completo.png"))

    for ruta in candidatas:
        try:
            with open(ruta, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("ascii")
            ext = os.path.splitext(ruta)[1].lower().lstrip(".") or "png"
            if ext == "jpg":
                ext = "jpeg"
            return f"data:image/{ext};base64,{b64}"
        except Exception:
            continue
    return ""


def _fmt(n, simbolo="$"):
    try:
        return f"{simbolo} {float(n):,.2f}"
    except Exception:
        return f"{simbolo} 0.00"


def construir_html(data: dict) -> str:
    """Construye el HTML de la cotización a partir de get_cotizacion_completa()."""
    if not data:
        return "<html><body><h2>Cotizacion no encontrada.</h2></body></html>"

    EMPRESA = _get_empresa()
    base    = data.get("moneda") or "USD"
    simbolo = MON_SIMB.get(base, "$")
    tasas   = _cargar_tasas()
    logo    = _logo_base64(EMPRESA.get("logo_path", ""))
    items   = data.get("items", [])

    filas = ""
    total_usd = 0.0
    for i, it in enumerate(items, 1):
        cant    = it.get("cantidad", 0)
        precio  = it.get("precio_unitario", 0)
        tipo    = it.get("tipo", "")
        mon_it  = TIPO_MONEDA.get(tipo, "USD")
        simb_it = SIMB_ITEM.get(mon_it, "$")
        sub     = cant * precio
        total_usd += cant * _a_usd(precio, mon_it, tasas)
        filas += (
            "<tr>"
            f'<td class="c">{i}</td>'
            f'<td>{it.get("descripcion","")}</td>'
            f'<td class="c">{tipo}</td>'
            f'<td class="c">{cant}</td>'
            f'<td class="r">{_fmt(precio, simb_it)}</td>'
            f'<td class="r">{_fmt(sub, simb_it)}</td>'
            "</tr>"
        )

    total = _convertir(total_usd, base, tasas)

    # Equivalencias en las demás monedas
    equiv_rows = ""
    for c in ["USD", "EUR", "VES", "USDT", "TASA_EXT"]:
        if c == base:
            continue
        val = _convertir(total_usd, c, tasas)
        if val > 0 or c == "VES":
            equiv_rows += (f'<tr class="tot-equiv"><td>≈ {c}</td>'
                           f'<td class="r">{_fmt(val, MON_SIMB.get(c, ""))}</td></tr>')

    logo_html = f'<img src="{logo}" class="logo">' if logo else ""
    emp_extra = ""
    for k, etq in (("rif", "RIF"), ("direccion", "Direccion"),
                   ("telefono", "Tel"), ("correo", "Correo")):
        if EMPRESA.get(k):
            emp_extra += f'<div class="emp-linea">{etq}: {EMPRESA[k]}</div>'

    obs = data.get("observaciones", "") or ""
    obs_html = (f'<div class="obs"><b>Observaciones:</b><br>{obs}</div>'
                if obs.strip() else "")

    generado = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")

    return f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8">
<title>Cotizacion {data.get('numero','')}</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{ font-family: 'Segoe UI', Arial, sans-serif; color: #1a2332;
          margin: 0; padding: 32px 40px; font-size: 13px; }}
  .top {{ display: flex; justify-content: space-between; align-items: flex-start;
          border-bottom: 3px solid #00B4D8; padding-bottom: 16px; }}
  .logo {{ height: 90px; }}
  .emp {{ text-align: left; }}
  .emp-nombre {{ font-size: 22px; font-weight: 700; color: #0A192F; }}
  .emp-eslogan {{ font-size: 12px; color: #00B4D8; letter-spacing: 2px;
                  text-transform: uppercase; margin-bottom: 6px; }}
  .emp-linea {{ font-size: 11px; color: #555; }}
  .doc-box {{ text-align: right; }}
  .doc-titulo {{ font-size: 20px; font-weight: 700; color: #00B4D8; }}
  .doc-num {{ font-size: 15px; font-weight: 600; margin-top: 4px; }}
  .doc-fecha {{ font-size: 12px; color: #555; margin-top: 2px; }}
  .cli {{ margin: 24px 0 12px; background: #f4f8fb; border-left: 4px solid #00B4D8;
          padding: 12px 16px; }}
  .cli h3 {{ margin: 0 0 6px; font-size: 12px; color: #00B4D8;
             text-transform: uppercase; letter-spacing: 1px; }}
  .cli-linea {{ font-size: 13px; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 12px; }}
  th {{ background: #0A192F; color: #fff; padding: 9px 8px; font-size: 12px;
        text-align: left; }}
  td {{ padding: 8px; border-bottom: 1px solid #e3e8ee; font-size: 12.5px; }}
  td.c, th.c {{ text-align: center; }}
  td.r, th.r {{ text-align: right; }}
  tr:nth-child(even) td {{ background: #f7fafc; }}
  .totales {{ margin-top: 16px; display: flex; justify-content: flex-end; }}
  .totales table {{ width: 320px; }}
  .totales td {{ border: none; padding: 6px 8px; }}
  .tot-final td {{ border-top: 2px solid #0A192F; font-size: 16px;
                   font-weight: 700; color: #0A192F; }}
  .tot-equiv td {{ border: none; font-size: 11px; color: #6b7280;
                   padding: 2px 8px; }}
  .obs {{ margin-top: 20px; background: #fffdf5; border: 1px solid #f0e6c0;
          padding: 12px 16px; font-size: 12px; }}
  .estado {{ display: inline-block; padding: 3px 12px; border-radius: 12px;
             font-size: 11px; font-weight: 600; background: #e3f6fb;
             color: #0077a3; }}
  .footer {{ margin-top: 40px; text-align: center; font-size: 10px;
             color: #999; border-top: 1px solid #e3e8ee; padding-top: 10px; }}
  @media print {{ body {{ padding: 12px 18px; }} .noprint {{ display: none; }} }}
  .btn-print {{ position: fixed; top: 12px; right: 12px; background: #00B4D8;
                color: #fff; border: none; padding: 10px 20px; font-size: 14px;
                border-radius: 6px; cursor: pointer; }}
</style></head>
<body>
  <button class="btn-print noprint" onclick="window.print()">Imprimir</button>
  <div class="top">
    <div class="emp">
      {logo_html}
      <div class="emp-nombre">{EMPRESA['nombre']}</div>
      <div class="emp-eslogan">{EMPRESA['eslogan']}</div>
      {emp_extra}
    </div>
    <div class="doc-box">
      <div class="doc-titulo">COTIZACION</div>
      <div class="doc-num">{data.get('numero','')}</div>
      <div class="doc-fecha">Fecha: {data.get('fecha','')}</div>
      <div class="doc-fecha"><span class="estado">{data.get('estado','')}</span></div>
    </div>
  </div>

  <div class="cli">
    <h3>Cliente</h3>
    <div class="cli-linea"><b>{data.get('cliente_nombre','') or '(Sin cliente)'}</b></div>
    <div class="cli-linea">RIF: {data.get('cliente_rif','')}</div>
    <div class="cli-linea">{data.get('cliente_dir','')}</div>
  </div>

  <table>
    <thead><tr>
      <th class="c" style="width:36px">#</th>
      <th>Descripcion</th>
      <th class="c" style="width:110px">Tipo</th>
      <th class="c" style="width:60px">Cant.</th>
      <th class="r" style="width:110px">P. Unit.</th>
      <th class="r" style="width:120px">Subtotal</th>
    </tr></thead>
    <tbody>{filas}</tbody>
  </table>

  <div class="totales">
    <table>
      <tr class="tot-final"><td>TOTAL ({base})</td><td class="r">{_fmt(total, simbolo)}</td></tr>
      {equiv_rows}
    </table>
  </div>

  {obs_html}

  <div class="footer">
    Documento generado el {generado} - {EMPRESA['nombre']} - Sistema Administrativo
  </div>
</body></html>"""


def imprimir_cotizacion(cot_id: int) -> bool:
    """Genera el HTML de la cotizacion y lo abre en el navegador para imprimir."""
    try:
        from core.database import get_cotizacion_completa
        data = get_cotizacion_completa(cot_id)
        html = construir_html(data)
        num  = (data.get("numero") or f"COT-{cot_id}").replace("/", "-")
        ruta = os.path.join(tempfile.gettempdir(), f"cotizacion_{num}.html")
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(html)
        webbrowser.open("file://" + os.path.abspath(ruta))
        return True
    except Exception as e:
        print(f"[impresion] Error al generar cotizacion: {e}")
        return False


# ══════════════════════════════════════════════════════════════════════
#  VENTAS  —  factura + pagos + plan de cuotas
# ══════════════════════════════════════════════════════════════════════
def _fila_item_venta(it, tasas):
    """Devuelve (html_fila, subtotal_usd) para un ítem de venta."""
    mon  = it.get("moneda_item", "USD")
    simb = SIMB_ITEM.get(mon, "$")
    cant = it.get("cantidad", 1) or 1
    pu   = it.get("precio_unitario", 0) or 0
    sub  = it.get("subtotal", cant * pu) or 0
    sub_usd = _a_usd(sub, mon, tasas)
    fila = (
        "<tr>"
        f"<td>{it.get('descripcion','')}</td>"
        f"<td style='text-align:center'>{it.get('tipo','')}</td>"
        f"<td style='text-align:center'>{_fmt(cant,'')}</td>"
        f"<td style='text-align:right'>{_fmt(pu, simb)}</td>"
        f"<td style='text-align:right'>{_fmt(sub, simb)}</td>"
        "</tr>"
    )
    return fila, sub_usd


def construir_html_venta(data: dict) -> str:
    """HTML de la factura de venta (ítems + pagos + plan de cuotas)."""
    EMPRESA = _get_empresa()
    tasas   = _cargar_tasas()
    moneda  = data.get("moneda", "USD")
    simb_m  = MON_SIMB.get(moneda, "$")
    logo    = _logo_base64(EMPRESA.get("logo_path", ""))

    filas, total_usd = [], 0.0
    for it in data.get("items", []):
        f, sub_usd = _fila_item_venta(it, tasas)
        filas.append(f)
        total_usd += sub_usd
    total_dest = _convertir(total_usd, moneda, tasas)

    # Pagos recibidos
    filas_pago = []
    for p in data.get("pagos", []):
        pm  = p.get("moneda", "USD")
        sp  = MON_SIMB.get(pm, "$")
        filas_pago.append(
            "<tr>"
            f"<td>{p.get('metodo_nombre','')}</td>"
            f"<td style='text-align:center'>{pm}</td>"
            f"<td style='text-align:right'>{_fmt(p.get('monto',0), sp)}</td>"
            "</tr>"
        )
    bloque_pagos = ""
    if filas_pago:
        bloque_pagos = (
            "<h3>Pagos recibidos</h3>"
            "<table><thead><tr>"
            "<th>Método</th><th style='text-align:center'>Moneda</th>"
            "<th style='text-align:right'>Monto</th>"
            "</tr></thead><tbody>" + "".join(filas_pago) + "</tbody></table>"
        )

    # Plan de cuotas (crédito) — en la moneda propia del crédito
    bloque_cuotas = ""
    moneda_cred = data.get("moneda_credito") or moneda
    simb_c      = MON_SIMB.get(moneda_cred, simb_m)
    if data.get("condicion", "").lower().startswith("cr") and data.get("cuotas"):
        filas_c = []
        for c in data["cuotas"]:
            filas_c.append(
                "<tr>"
                f"<td style='text-align:center'>{c.get('numero_cuota','')}</td>"
                f"<td style='text-align:center'>{c.get('fecha_venc','')}</td>"
                f"<td style='text-align:right'>{_fmt(c.get('monto',0), simb_c)}</td>"
                "</tr>"
            )
        ini = data.get("inicial", 0) or 0
        bloque_cuotas = (
            "<h3>Plan de pago (Crédito)</h3>"
            f"<p><b>Cuota inicial:</b> {_fmt(ini, simb_c)} ({moneda_cred}) &nbsp;·&nbsp; "
            f"<b>N° de cuotas:</b> {data.get('num_cuotas',0)} &nbsp;·&nbsp; "
            f"<b>Frecuencia:</b> {data.get('dias_frecuencia',0)} días &nbsp;·&nbsp; "
            f"<b>Primera cuota:</b> {data.get('fecha_primera_cuota','')}</p>"
            "<table><thead><tr>"
            "<th style='text-align:center'>Cuota</th>"
            "<th style='text-align:center'>Vencimiento</th>"
            "<th style='text-align:right'>Monto</th>"
            "</tr></thead><tbody>" + "".join(filas_c) + "</tbody></table>"
        )

    # Equivalencias del total
    eqs = []
    for m in ("USD", "EUR", "USDT", "VES"):
        if m == moneda:
            continue
        val = _convertir(total_usd, m, tasas)
        if val:
            eqs.append(f"<span>{MON_SIMB.get(m,'')} {val:,.2f}</span>")
    bloque_eq = ("<div class='equiv'><b>Equivalencias:</b> " +
                 " &nbsp;|&nbsp; ".join(eqs) + "</div>") if eqs else ""

    img = f"<img src='{logo}' style='height:70px'>" if logo else ""
    return f"""<!DOCTYPE html><html><head><meta charset='utf-8'>
<title>Venta {data.get('numero','')}</title>
<style>
 body{{font-family:Arial,Helvetica,sans-serif;color:#0A192F;margin:32px;}}
 .hd{{display:flex;justify-content:space-between;align-items:center;
      border-bottom:3px solid #00A9B5;padding-bottom:10px;margin-bottom:16px;}}
 .emp b{{font-size:20px;}} .emp span{{color:#555;font-size:12px;}}
 h2{{margin:4px 0;}} h3{{margin-top:22px;color:#0A6E78;
     border-bottom:1px solid #ccc;padding-bottom:4px;}}
 table{{width:100%;border-collapse:collapse;margin-top:8px;font-size:13px;}}
 th,td{{border:1px solid #ccc;padding:6px 8px;}}
 thead th{{background:#0A192F;color:#fff;}}
 .tot{{text-align:right;font-size:18px;font-weight:bold;margin-top:14px;}}
 .equiv{{margin-top:8px;font-size:12px;color:#333;background:#f2f7f8;
         padding:8px;border-radius:6px;}}
 .datos{{font-size:13px;color:#333;margin-bottom:10px;}}
 @media print{{button{{display:none;}}}}
</style></head><body>
<div class='hd'>
 <div class='emp'><b>{EMPRESA['nombre']}</b><br><span>{EMPRESA['eslogan']}</span>
  {('<br><span>RIF: '+EMPRESA['rif']+'</span>') if EMPRESA.get('rif') else ''}
  {('<br><span>'+EMPRESA['direccion']+'</span>') if EMPRESA.get('direccion') else ''}
  {('<br><span>Tel: '+EMPRESA['telefono']+'</span>') if EMPRESA.get('telefono') else ''}
  {('<br><span>'+EMPRESA['correo']+'</span>') if EMPRESA.get('correo') else ''}</div>
 <div style='text-align:right'>{img}<br>
  <b>NOTA DE VENTA</b><br>N° {data.get('numero','')}<br>{data.get('fecha','')}</div>
</div>
<div class='datos'>
 <b>Cliente:</b> {data.get('cliente_nombre','')} &nbsp; 
 <b>RIF:</b> {data.get('cliente_rif','')}<br>
 {('<b>Dirección:</b> '+data.get('cliente_dir','')+'<br>') if data.get('cliente_dir') else ''}
 <b>Condición:</b> {data.get('condicion','Contado')} &nbsp; 
 <b>Estado:</b> {data.get('estado','')}
</div>
<table><thead><tr>
 <th>Descripción</th><th style='text-align:center'>Tipo</th>
 <th style='text-align:center'>Cant.</th>
 <th style='text-align:right'>P. Unit.</th>
 <th style='text-align:right'>Subtotal</th>
</tr></thead><tbody>{''.join(filas)}</tbody></table>
<div class='tot'>TOTAL: {_fmt(total_dest, simb_m)} ({moneda})</div>
{bloque_eq}
{bloque_pagos}
{bloque_cuotas}
<div style='margin-top:24px'><button onclick='window.print()'>Imprimir</button></div>
</body></html>"""


def imprimir_venta(venta_id: int) -> bool:
    """Genera el HTML de la venta y lo abre en el navegador."""
    try:
        from core.database import get_venta_completa
        data = get_venta_completa(venta_id)
        if not data:
            print(f"[impresion] Venta {venta_id} no encontrada")
            return False
        html = construir_html_venta(data)
        num  = (data.get("numero") or f"VTA-{venta_id}").replace("/", "-")
        ruta = os.path.join(tempfile.gettempdir(), f"venta_{num}.html")
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(html)
        webbrowser.open("file://" + os.path.abspath(ruta))
        return True
    except Exception as e:
        print(f"[impresion] Error al generar venta: {e}")
        return False


# ══════════════════════════════════════════════════════════════════════
#  CONTRATO DE COMPROMISO DE PAGO  (plantilla editable + placeholders)
# ══════════════════════════════════════════════════════════════════════
def _plan_pagos_texto(data, simb_m):
    """Texto plano del plan de cuotas para insertar en el contrato."""
    if not data.get("cuotas"):
        return "(Sin cuotas registradas)"
    lineas = []
    for c in data["cuotas"]:
        lineas.append(
            f"  Cuota {c.get('numero_cuota','')}: "
            f"{c.get('fecha_venc','')}  -  {simb_m} {float(c.get('monto',0)):,.2f}"
        )
    return "\n".join(lineas)


def construir_html_contrato_pago(data: dict) -> str:
    """Rellena la plantilla editable del contrato con los datos de la venta."""
    from core.database import obtener_contrato_pago
    plantilla = obtener_contrato_pago()

    EMPRESA = _get_empresa()
    tasas  = _cargar_tasas()
    moneda = data.get("moneda", "USD")
    simb_m = MON_SIMB.get(moneda, "$")

    # Total en la moneda de la venta
    total_usd = 0.0
    for it in data.get("items", []):
        total_usd += _a_usd(it.get("subtotal", 0) or 0,
                            it.get("moneda_item", "USD"), tasas)
    total_dest = _convertir(total_usd, moneda, tasas)

    # Moneda propia del crédito (inicial / cuotas)
    moneda_cred = data.get("moneda_credito") or moneda
    simb_c      = MON_SIMB.get(moneda_cred, simb_m)

    repl = {
        "[EMPRESA_NOMBRE]":      EMPRESA.get("nombre", ""),
        "[EMPRESA_RIF]":         EMPRESA.get("rif", ""),
        "[CLIENTE_NOMBRE]":      data.get("cliente_nombre", ""),
        "[CLIENTE_RIF]":         data.get("cliente_rif", ""),
        "[CLIENTE_DIR]":         data.get("cliente_dir", ""),
        "[VENTA_NUMERO]":        data.get("numero", ""),
        "[VENTA_FECHA]":         data.get("fecha", ""),
        "[VENTA_TOTAL]":         f"{simb_m} {total_dest:,.2f} ({moneda})",
        "[INICIAL]":             f"{simb_c} {float(data.get('inicial',0) or 0):,.2f} ({moneda_cred})",
        "[NUM_CUOTAS]":          str(data.get("num_cuotas", 0) or 0),
        "[MONTO_CUOTA]":         f"{simb_c} {float(data.get('monto_cuota',0) or 0):,.2f} ({moneda_cred})",
        "[DIAS_FRECUENCIA]":     str(data.get("dias_frecuencia", 0) or 0),
        "[FECHA_PRIMERA_CUOTA]": data.get("fecha_primera_cuota", ""),
        "[PLAN_PAGOS]":          _plan_pagos_texto(data, simb_c),
        "[CIUDAD]":              EMPRESA.get("ciudad", "Caracas"),
    }
    texto = plantilla
    for k, v in repl.items():
        texto = texto.replace(k, str(v))

    import html as _html
    cuerpo = _html.escape(texto)
    return f"""<!DOCTYPE html><html><head><meta charset='utf-8'>
<title>Contrato de pago {data.get('numero','')}</title>
<style>
 body{{font-family:'Times New Roman',serif;color:#111;margin:48px auto;
      max-width:820px;line-height:1.6;}}
 pre{{white-space:pre-wrap;font-family:inherit;font-size:15px;}}
 @media print{{button{{display:none;}}}}
</style></head><body>
<pre>{cuerpo}</pre>
<div style='margin-top:24px'><button onclick='window.print()'>Imprimir</button></div>
</body></html>"""


def imprimir_contrato_pago(venta_id: int) -> bool:
    """Genera el contrato de compromiso de pago y lo abre en el navegador."""
    try:
        from core.database import get_venta_completa
        data = get_venta_completa(venta_id)
        if not data:
            print(f"[impresion] Venta {venta_id} no encontrada")
            return False
        html = construir_html_contrato_pago(data)
        num  = (data.get("numero") or f"VTA-{venta_id}").replace("/", "-")
        ruta = os.path.join(tempfile.gettempdir(), f"contrato_{num}.html")
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(html)
        webbrowser.open("file://" + os.path.abspath(ruta))
        return True
    except Exception as e:
        print(f"[impresion] Error al generar contrato de pago: {e}")
        return False
