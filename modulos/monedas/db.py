"""
modulos/monedas/db.py
======================
Capa de datos del módulo Monedas.

Responsabilidades:
  - Inicializar y migrar las tablas `monedas` e `historial_monedas`
  - Leer / escribir tasas en usuarios.db
  - Consultar USD/EUR desde BCV (bcv.org.ve)
  - Consultar USDT desde Binance P2P
  - Lanzar actualizaciones automáticas en un hilo de fondo (sin bloquear UI)
"""

import sqlite3
import threading
import requests

from datetime import datetime
from bs4 import BeautifulSoup

from core.database import DB_NAME


# ─────────────────────────────────────────────────────────────────────────────
# DEFINICIÓN CANÓNICA DE MONEDAS
# ─────────────────────────────────────────────────────────────────────────────

MONEDAS_CONFIG = [
    {"codigo": "USD",      "nombre": "Dólar Americano", "simbolo": "$ ",  "icono": "💵", "fuente": "BCV",     "manual": False},
    {"codigo": "EUR",      "nombre": "Euro",            "simbolo": "€ ",  "icono": "💶", "fuente": "BCV",     "manual": False},
    {"codigo": "VES",      "nombre": "Bolívar",         "simbolo": "Bs.", "icono": "🇻🇪", "fuente": "FIJO",    "manual": False},
    {"codigo": "USDT",     "nombre": "USDT / Tether",   "simbolo": "₮ ",  "icono": "🟡", "fuente": "BINANCE", "manual": False},
    {"codigo": "TASA_EXT", "nombre": "Tasa Externa",    "simbolo": "★ ",  "icono": "⚙️", "fuente": "MANUAL",  "manual": True},
]

# Códigos habilitados para el historial (excluye VES)
CODIGOS_HISTORIAL = ["TODOS"] + [m["codigo"] for m in MONEDAS_CONFIG
                                  if m["codigo"] != "VES"]


# ─────────────────────────────────────────────────────────────────────────────
# INICIALIZACIÓN DE TABLAS
# ─────────────────────────────────────────────────────────────────────────────

def inicializar_tablas():
    """
    Crea `monedas` e `historial_monedas` si no existen.
    También realiza migraciones automáticas (agrega columna `usuario` si falta).
    """
    con = sqlite3.connect(DB_NAME)
    cur = con.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS monedas (
            codigo      TEXT PRIMARY KEY,
            nombre      TEXT NOT NULL,
            tasa        REAL NOT NULL DEFAULT 0.0,
            actualizado TEXT NOT NULL DEFAULT '—',
            fuente      TEXT NOT NULL DEFAULT 'MANUAL',
            error       TEXT DEFAULT ''
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS historial_monedas (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo        TEXT NOT NULL,
            nombre        TEXT NOT NULL,
            tasa_anterior REAL NOT NULL DEFAULT 0.0,
            tasa_nueva    REAL NOT NULL DEFAULT 0.0,
            fecha         TEXT NOT NULL,
            tipo          TEXT NOT NULL DEFAULT 'AUTO',
            usuario       TEXT NOT NULL DEFAULT 'Sistema'
        )
    """)

    # Migración: agregar columna usuario si el historial ya existía sin ella
    try:
        cur.execute("ALTER TABLE historial_monedas ADD COLUMN "
                    "usuario TEXT NOT NULL DEFAULT 'Sistema'")
    except sqlite3.OperationalError:
        pass  # Ya existe

    # Poblar monedas que aún no tengan registro
    for m in MONEDAS_CONFIG:
        cur.execute("""
            INSERT OR IGNORE INTO monedas (codigo, nombre, tasa, actualizado, fuente, error)
            VALUES (?, ?, ?, '—', ?, '')
        """, (m["codigo"], m["nombre"],
              1.0 if m["codigo"] == "VES" else 0.0,
              m["fuente"]))

    con.commit()
    con.close()


# ─────────────────────────────────────────────────────────────────────────────
# LECTURA
# ─────────────────────────────────────────────────────────────────────────────

def leer_todas() -> dict:
    """Retorna {codigo: {tasa, actualizado, error}} para todas las monedas."""
    con = sqlite3.connect(DB_NAME)
    cur = con.cursor()
    cur.execute("SELECT codigo, tasa, actualizado, error FROM monedas")
    rows = cur.fetchall()
    con.close()
    return {r[0]: {"tasa": r[1], "actualizado": r[2], "error": r[3]}
            for r in rows}


def leer_historial(limite: int = 200, codigo: str = None) -> list:
    """
    Retorna registros del historial ordenados por más reciente.
    Si `codigo` es None o 'TODOS' devuelve todos.
    """
    con = sqlite3.connect(DB_NAME)
    cur = con.cursor()
    if codigo and codigo != "TODOS":
        cur.execute("""
            SELECT codigo, nombre, tasa_anterior, tasa_nueva, fecha, tipo, usuario
            FROM historial_monedas
            WHERE codigo = ?
            ORDER BY id DESC LIMIT ?
        """, (codigo, limite))
    else:
        cur.execute("""
            SELECT codigo, nombre, tasa_anterior, tasa_nueva, fecha, tipo, usuario
            FROM historial_monedas
            ORDER BY id DESC LIMIT ?
        """, (limite,))
    rows = cur.fetchall()
    con.close()
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# ESCRITURA
# ─────────────────────────────────────────────────────────────────────────────

def guardar(codigo: str, tasa: float,
            error: str = "", tipo: str = "AUTO",
            usuario: str = "Sistema"):
    """
    Persiste la tasa en la tabla `monedas` y, si cambió, registra en historial.
    """
    ahora = datetime.now().strftime("%d/%m/%Y %H:%M")
    con = sqlite3.connect(DB_NAME)
    cur = con.cursor()

    cur.execute("SELECT tasa, nombre FROM monedas WHERE codigo=?", (codigo,))
    row = cur.fetchone()
    tasa_anterior = row[0] if row else 0.0
    nombre        = row[1] if row else codigo

    cur.execute("""
        UPDATE monedas SET tasa=?, actualizado=?, error=? WHERE codigo=?
    """, (tasa, ahora, error, codigo))

    if round(tasa_anterior, 6) != round(tasa, 6):
        cur.execute("""
            INSERT INTO historial_monedas
                (codigo, nombre, tasa_anterior, tasa_nueva, fecha, tipo, usuario)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (codigo, nombre, tasa_anterior, tasa, ahora, tipo, usuario))

    con.commit()
    con.close()


# ─────────────────────────────────────────────────────────────────────────────
# CONSULTAS EXTERNAS
# ─────────────────────────────────────────────────────────────────────────────

def _consultar_bcv() -> tuple:
    """Scrape BCV → retorna (usd: float, eur: float) o lanza excepción."""
    url = "https://www.bcv.org.ve/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    r = requests.get(url, headers=headers, timeout=12, verify=False)
    soup = BeautifulSoup(r.content, "html.parser")

    def _extraer(div_id):
        bloque = soup.find("div", {"id": div_id})
        texto  = bloque.find("strong").get_text(strip=True).replace(",", ".")
        return round(float(texto), 4)

    return _extraer("dolar"), _extraer("euro")


def _consultar_binance() -> float:
    """Binance P2P → precio promedio USDT/VES (top 5 ofertas BUY)."""
    url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
    payload = {
        "asset": "USDT", "fiat": "VES", "tradeType": "BUY",
        "page": 1, "rows": 5, "payTypes": [], "publisherType": None,
    }
    r = requests.post(url, json=payload,
                      headers={"Content-Type": "application/json"},
                      timeout=12)
    data   = r.json()
    precios = [float(ad["adv"]["price"]) for ad in data["data"][:5]]
    return round(sum(precios) / len(precios), 4)


# ─────────────────────────────────────────────────────────────────────────────
# ACTUALIZACIÓN EN SEGUNDO PLANO
# ─────────────────────────────────────────────────────────────────────────────

def actualizar_en_background(callback=None, usuario: str = "Sistema"):
    """
    Inicia un hilo daemon que actualiza USD, EUR y USDT desde APIs externas.
    VES se fuerza siempre a 1. TASA_EXT no se modifica.

    Args:
        callback: función sin argumentos a ejecutar en el hilo UI tras terminar.
        usuario:  nombre del usuario que desencadenó la actualización.
    """
    def _trabajo():
        # USD + EUR desde BCV
        try:
            usd, eur = _consultar_bcv()
            guardar("USD",  usd, tipo="AUTO", usuario=usuario)
            guardar("EUR",  eur, tipo="AUTO", usuario=usuario)
        except Exception as exc:
            msg = f"BCV sin respuesta: {exc}"
            con = sqlite3.connect(DB_NAME)
            con.execute("UPDATE monedas SET error=? WHERE codigo IN ('USD','EUR')",
                        (msg,))
            con.commit()
            con.close()

        # USDT desde Binance P2P
        try:
            usdt = _consultar_binance()
            guardar("USDT", usdt, tipo="AUTO", usuario=usuario)
        except Exception as exc:
            msg = f"Binance sin respuesta: {exc}"
            con = sqlite3.connect(DB_NAME)
            con.execute("UPDATE monedas SET error=? WHERE codigo='USDT'", (msg,))
            con.commit()
            con.close()

        # VES siempre = 1
        guardar("VES", 1.0, tipo="AUTO", usuario=usuario)

        if callback:
            callback()

    threading.Thread(target=_trabajo, daemon=True).start()
