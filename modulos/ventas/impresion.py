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

# ── Datos de la empresa (edítalos aquí si cambian) ──────────────────────────
EMPRESA = {
    "nombre":    "CIGG SYSTEMS",
    "eslogan":   "Tech & Cyber Security",
    "rif":       "",
    "direccion": "",
    "telefono":  "",
    "correo":    "",
}

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


def _logo_base64() -> str:
    """Devuelve el logo como data-URI base64, o cadena vacía si no existe."""
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ruta = os.path.join(base, "imagenes", "logo_completo.png")
    try:
        with open(ruta, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        return f"data:image/png;base64,{b64}"
    except Exception:
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

    base    = data.get("moneda") or "USD"
    simbolo = MON_SIMB.get(base, "$")
    tasas   = _cargar_tasas()
    logo    = _logo_base64()
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
