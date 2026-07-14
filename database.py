"""
core/database.py
================
Módulo central de persistencia del sistema CIGG.

Responsabilidades:
  - Ruta absoluta de usuarios.db (funciona en desarrollo y empaquetado)
  - Inicialización de TODAS las tablas del sistema en un único punto
  - Helpers de seguridad: hash PBKDF2 y sanitización de entradas
  - CRUD completo de proveedores (consolidado, elimina db_proveedores.py)

Uso desde cualquier módulo:
    from core.database import DB_NAME, inicializar_todo
    from core.database import obtener_proveedores, guardar_proveedor
"""

import os
import sys
import sqlite3
import hashlib
import re

# ─────────────────────────────────────────────────────────────────────────────
# RUTA ABSOLUTA DE LA BASE DE DATOS
# Funciona tanto en ejecución directa como empaquetado con PyInstaller.
# ─────────────────────────────────────────────────────────────────────────────
if getattr(sys, 'frozen', False):
    _BASE = os.path.dirname(sys.executable)
else:
    _BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DB_NAME = os.path.join(_BASE, "usuarios.db")


# ─────────────────────────────────────────────────────────────────────────────
# SEGURIDAD
# ─────────────────────────────────────────────────────────────────────────────

def sanitizar_entrada(texto: str) -> str:
    """Elimina caracteres peligrosos para prevenir inyección SQL o XSS."""
    if not texto:
        return ""
    return re.sub(r"[^\w\s@\.\-]", "", texto).strip()


def generar_hash(contrasena: str, salt: bytes = None):
    """
    Hash seguro PBKDF2-HMAC-SHA256 (100 000 iteraciones).

    Returns:
        (salt_hex: str, hash_hex: str)
    """
    if salt is None:
        salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac("sha256", contrasena.encode("utf-8"), salt, 100_000)
    return salt.hex(), key.hex()


# ─────────────────────────────────────────────────────────────────────────────
# INICIALIZACIÓN INTERNA DE TABLAS
# ─────────────────────────────────────────────────────────────────────────────

def _init_usuarios(cur: sqlite3.Cursor):
    """Tabla de usuarios del sistema con hash de contraseña segura."""
    cur.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            username        TEXT UNIQUE NOT NULL,
            salt            TEXT NOT NULL,
            password_hash   TEXT NOT NULL,
            nombre_completo TEXT DEFAULT '',
            telefono        TEXT DEFAULT '',
            correo          TEXT DEFAULT '',
            rol_id          INTEGER DEFAULT 1
        )
    """)
    # Migración: agregar columnas si no existen (BD ya creada anteriormente)
    cur.execute("PRAGMA table_info(usuarios)")
    cols = {r[1] for r in cur.fetchall()}
    for col, ddl in [
        ("nombre_completo", "TEXT DEFAULT ''"),
        ("telefono",        "TEXT DEFAULT ''"),
        ("correo",          "TEXT DEFAULT ''"),
        ("rol_id",          "INTEGER DEFAULT 1"),
    ]:
        if col not in cols:
            cur.execute(f"ALTER TABLE usuarios ADD COLUMN {col} {ddl}")

    cur.execute("SELECT id FROM usuarios WHERE username = 'admin'")
    if not cur.fetchone():
        salt, p_hash = generar_hash("1234")
        cur.execute(
            "INSERT INTO usuarios (username, salt, password_hash) VALUES (?, ?, ?)",
            ("admin", salt, p_hash),
        )


def _init_maquinas(cur: sqlite3.Cursor):
    """
    Tablas de modelos y unidades de máquinas fiscales.
    Incluye migración automática desde el esquema anterior (fabricante_id FK).
    """
    # Verificar si la tabla ya existe
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='modelos_maquinas'")
    tabla_existe = cur.fetchone() is not None

    if not tabla_existe:
        cur.execute("""
            CREATE TABLE modelos_maquinas (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre        TEXT UNIQUE NOT NULL,
                fabricante    TEXT NOT NULL DEFAULT '',
                nombre_imagen TEXT DEFAULT ''
            )
        """)
    else:
        # Migración: agregar columnas si faltaban en versión anterior
        cur.execute("PRAGMA table_info(modelos_maquinas)")
        cols = {row[1] for row in cur.fetchall()}

        if "fabricante" not in cols:
            cur.execute("ALTER TABLE modelos_maquinas ADD COLUMN fabricante TEXT DEFAULT ''")
            # Si existía fabricante_id, intentar copiar el nombre
            if "fabricante_id" in cols:
                try:
                    cur.execute("""
                        UPDATE modelos_maquinas SET fabricante = COALESCE(
                            (SELECT razon_social FROM proveedores
                             WHERE id = modelos_maquinas.fabricante_id),
                            (SELECT nombre FROM fabricantes_maquinas
                             WHERE id = modelos_maquinas.fabricante_id),
                            'Desconocido'
                        )
                    """)
                except Exception:
                    pass

        if "nombre_imagen" not in cols:
            cur.execute("ALTER TABLE modelos_maquinas ADD COLUMN nombre_imagen TEXT DEFAULT ''")
            # Migrar columna 'imagen' si existía
            if "imagen" in cols:
                try:
                    cur.execute("UPDATE modelos_maquinas SET nombre_imagen = imagen")
                except Exception:
                    pass

    # Tabla de unidades individuales
    cur.execute("""
        CREATE TABLE IF NOT EXISTS maquinas_fiscales (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            modelo_id        INTEGER NOT NULL,
            numero_registro  TEXT UNIQUE NOT NULL,
            numero_serial    TEXT UNIQUE NOT NULL,
            firmware         TEXT NOT NULL,
            numero_precinto  TEXT,
            cliente          TEXT DEFAULT 'DISPONIBLE EN STOCK',
            inspeccion_anual INTEGER DEFAULT 0,
            fecha_registro   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (modelo_id) REFERENCES modelos_maquinas(id) ON DELETE CASCADE
        )
    """)


def _init_clientes(cur: sqlite3.Cursor):
    """Crea la tabla de clientes si no existe."""
    cur.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            rif                 TEXT    NOT NULL UNIQUE,
            razon_social        TEXT    NOT NULL,
            direccion_fiscal    TEXT    DEFAULT '',
            correo              TEXT    DEFAULT '',
            tipo_contribuyente  TEXT    DEFAULT 'Ordinario',
            telefono            TEXT    DEFAULT ''
        )
    """)


def _init_sistemas(cur: sqlite3.Cursor):
    """Crea las tablas de sistemas y licencias si no existen."""
    cur.execute("""
        CREATE TABLE IF NOT EXISTS modelos_sistemas (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre         TEXT    NOT NULL UNIQUE,
            proveedor      TEXT    DEFAULT '',
            nombre_imagen  TEXT    DEFAULT ''
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sistemas_licencias (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            modelo_id       INTEGER NOT NULL,
            licencia        TEXT    NOT NULL UNIQUE,
            version         TEXT    NOT NULL,
            fecha_licencia  TEXT,
            cliente         TEXT,
            ruta_contrato   TEXT,
            FOREIGN KEY (modelo_id) REFERENCES modelos_sistemas(id) ON DELETE CASCADE
        )
    """)
    # ── Migración: agregar columnas nuevas a DBs existentes ──────────────────
    cur.execute("PRAGMA table_info(sistemas_licencias)")
    cols_lic = {r[1] for r in cur.fetchall()}
    for col, ddl in [("cliente", "TEXT DEFAULT ''"),
                     ("ruta_contrato", "TEXT DEFAULT ''")]:
        if col not in cols_lic:
            cur.execute(f"ALTER TABLE sistemas_licencias ADD COLUMN {col} {ddl}")


def _init_proveedores(cur: sqlite3.Cursor):
    """Tablas normalizadas del módulo Proveedores con catálogos precargados."""
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tipos_contribuyente (
            id     INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS porcentajes_retencion (
            id    INTEGER PRIMARY KEY AUTOINCREMENT,
            valor INTEGER NOT NULL UNIQUE
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tipos_proveedor (
            id     INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS proveedores (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            razon_social      TEXT NOT NULL,
            rif               TEXT NOT NULL UNIQUE,
            direccion         TEXT NOT NULL,
            contribuyente_id  INTEGER NOT NULL,
            retencion_id      INTEGER NOT NULL,
            telefono          TEXT,
            correo            TEXT,
            tipo_proveedor_id INTEGER NOT NULL,
            FOREIGN KEY (contribuyente_id)  REFERENCES tipos_contribuyente(id),
            FOREIGN KEY (retencion_id)      REFERENCES porcentajes_retencion(id),
            FOREIGN KEY (tipo_proveedor_id) REFERENCES tipos_proveedor(id)
        )
    """)
    # Datos maestros de catálogo
    cur.executemany(
        "INSERT OR IGNORE INTO tipos_contribuyente (nombre) VALUES (?)",
        [("Especial",), ("Ordinario",)],
    )
    cur.executemany(
        "INSERT OR IGNORE INTO porcentajes_retencion (valor) VALUES (?)",
        [(0,), (75,), (100,)],
    )
    cur.executemany(
        "INSERT OR IGNORE INTO tipos_proveedor (nombre) VALUES (?)",
        [("Máquinas Fiscales",), ("Sistemas",), ("Otros",)],
    )


# ─────────────────────────────────────────────────────────────────────────────
# PUNTO DE ENTRADA ÚNICO
# ─────────────────────────────────────────────────────────────────────────────

def _init_roles(cur: sqlite3.Cursor):
    """
    Tablas de roles y permisos.
    También migra la columna rol_id en usuarios si no existe.
    """
    # ── roles ────────────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS roles (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre      TEXT    NOT NULL UNIQUE,
            descripcion TEXT    DEFAULT '',
            es_admin    INTEGER DEFAULT 0
        )
    """)

    # ── permisos por rol ─────────────────────────────────────────────────────
    # clave: "Archivos", "Archivos.Usuarios", "Ventas", etc.
    # módulos padre con submódulos sólo usan 'ver';
    # submódulos y módulos hoja usan ver + editar + eliminar.
    cur.execute("""
        CREATE TABLE IF NOT EXISTS permisos (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            rol_id   INTEGER NOT NULL,
            clave    TEXT    NOT NULL,
            ver      INTEGER DEFAULT 0,
            editar   INTEGER DEFAULT 0,
            eliminar INTEGER DEFAULT 0,
            UNIQUE(rol_id, clave),
            FOREIGN KEY(rol_id) REFERENCES roles(id) ON DELETE CASCADE
        )
    """)

    # ── seed / migrar rol admin ───────────────────────────────────────────────
    # Crea el rol si no existe; si ya existe lo garantiza con es_admin=1
    cur.execute("SELECT id FROM roles WHERE nombre='admin'")
    row_admin = cur.fetchone()
    if not row_admin:
        cur.execute(
            "INSERT INTO roles (nombre, descripcion, es_admin) VALUES ('admin','Administrador del sistema — acceso total',1)"
        )
        cur.execute("SELECT id FROM roles WHERE nombre='admin'")
        admin_id = cur.fetchone()[0]
    else:
        admin_id = row_admin[0]
        # Migración: garantizar es_admin=1 aunque la fila ya existiera
        cur.execute("UPDATE roles SET es_admin=1 WHERE id=?", (admin_id,))

    # Garantizar todos los permisos del admin (INSERT OR REPLACE para actualizar)
    claves_admin = [
        "Archivos",
        "Archivos.Usuarios", "Archivos.Máquinas", "Archivos.Proveedores",
        "Archivos.Clientes", "Archivos.Sistemas", "Archivos.Roles",
        "Ventas", "Inventario", "Monedas",
        "Servicios", "Documentos", "Informes",
    ]
    for clave in claves_admin:
        cur.execute(
            "INSERT OR IGNORE INTO permisos (rol_id,clave,ver,editar,eliminar) VALUES (?,?,1,1,1)",
            (admin_id, clave),
        )
        # Asegurar que los existentes también tengan todos los permisos
        cur.execute(
            "UPDATE permisos SET ver=1,editar=1,eliminar=1 WHERE rol_id=? AND clave=?",
            (admin_id, clave),
        )

    # ── migrar columna rol_id en usuarios ────────────────────────────────────
    cur.execute("PRAGMA table_info(usuarios)")
    cols = {r[1] for r in cur.fetchall()}
    if "rol_id" not in cols:
        cur.execute("ALTER TABLE usuarios ADD COLUMN rol_id INTEGER DEFAULT 1")
        # El admin (id=1) usa siempre el rol admin (id=1)
        cur.execute("UPDATE usuarios SET rol_id=1 WHERE id=1")


def _init_documentos(cur: sqlite3.Cursor):
    """Crea las tablas del módulo Documentos."""
    cur.execute("""
        CREATE TABLE IF NOT EXISTS doc_homologaciones (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            modelo_sistema_id INTEGER NOT NULL,
            nombre            TEXT    NOT NULL,
            ruta              TEXT    NOT NULL,
            fecha_subida      TEXT    DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS doc_enajenacion (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            modelo_maquina_id INTEGER NOT NULL,
            nombre            TEXT    NOT NULL,
            ruta              TEXT    NOT NULL,
            fecha_subida      TEXT    DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS doc_carta_entrega (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            modelo_maquina_id INTEGER NOT NULL UNIQUE,
            contenido         TEXT    DEFAULT '',
            fecha_mod         TEXT    DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS doc_providencias (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre            TEXT    NOT NULL,
            descripcion       TEXT    DEFAULT '',
            ruta              TEXT    NOT NULL,
            fecha_publicacion TEXT    DEFAULT '',
            fecha_subida      TEXT    DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS doc_carpetas (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre         TEXT    NOT NULL UNIQUE,
            fecha_creacion TEXT    DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS doc_varios (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            carpeta_id   INTEGER NOT NULL,
            nombre       TEXT    NOT NULL,
            descripcion  TEXT    DEFAULT '',
            ruta         TEXT    NOT NULL,
            fecha_subida TEXT    DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (carpeta_id) REFERENCES doc_carpetas(id) ON DELETE CASCADE
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS marcas (
            id     INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT    NOT NULL UNIQUE
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS departamentos (
            id     INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT    NOT NULL UNIQUE
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS grupos (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre           TEXT    NOT NULL UNIQUE,
            departamento_id  INTEGER NOT NULL,
            FOREIGN KEY (departamento_id) REFERENCES departamentos(id)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS items_inventario (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo          TEXT    UNIQUE NOT NULL,
            nombre          TEXT    NOT NULL,
            descripcion     TEXT    DEFAULT '',
            marca_id        INTEGER,
            departamento_id INTEGER,
            grupo_id        INTEGER,
            unidad_medida   TEXT    DEFAULT 'Unidad',
            stock           REAL    DEFAULT 0,
            stock_minimo    REAL    DEFAULT 0,
            precio_costo    REAL    DEFAULT 0,
            precio_venta    REAL    DEFAULT 0
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS carga_inventario (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id         INTEGER NOT NULL,
            cantidad        REAL    NOT NULL,
            precio_unitario REAL    DEFAULT 0,
            proveedor       TEXT    DEFAULT '',
            referencia      TEXT    DEFAULT '',
            observaciones   TEXT    DEFAULT '',
            fecha           TEXT    DEFAULT '',
            usuario         TEXT    DEFAULT '',
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (item_id) REFERENCES items_inventario(id)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS descarga_inventario (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id         INTEGER NOT NULL,
            cantidad        REAL    NOT NULL,
            precio_unitario REAL    DEFAULT 0,
            motivo          TEXT    DEFAULT '',
            destino         TEXT    DEFAULT '',
            referencia      TEXT    DEFAULT '',
            observaciones   TEXT    DEFAULT '',
            fecha           TEXT    DEFAULT '',
            usuario         TEXT    DEFAULT '',
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (item_id) REFERENCES items_inventario(id)
        )
    """)



# ── Cotizaciones ──────────────────────────────────────────────────────────────
def _init_cotizaciones(cur: sqlite3.Cursor):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS cotizaciones (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            numero        TEXT    UNIQUE NOT NULL,
            fecha         TEXT    NOT NULL,
            cliente_id    INTEGER,
            observaciones TEXT    DEFAULT \'\',
            estado        TEXT    DEFAULT \'Pendiente\',
            usuario       TEXT    DEFAULT \'\',
            total         REAL    DEFAULT 0
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS cotizacion_items (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            cotizacion_id   INTEGER NOT NULL REFERENCES cotizaciones(id) ON DELETE CASCADE,
            tipo            TEXT    NOT NULL,
            item_ref_id     INTEGER,
            descripcion     TEXT    NOT NULL,
            cantidad        REAL    NOT NULL DEFAULT 1,
            precio_unitario REAL    NOT NULL DEFAULT 0,
            subtotal        REAL    NOT NULL DEFAULT 0
        )
    """)

def inicializar_todo():
    """
    Inicializa toda la base de datos del sistema.
    Debe llamarse UNA SOLA VEZ al arrancar la aplicación (main.py).
    """
    con = sqlite3.connect(DB_NAME)
    cur = con.cursor()
    cur.execute("PRAGMA foreign_keys = ON")
    _init_usuarios(cur)
    _init_maquinas(cur)
    _init_sistemas(cur)
    _init_clientes(cur)
    _init_proveedores(cur)
    _init_roles(cur)
    _init_documentos(cur)
    _init_cotizaciones(cur)
    con.commit()
    con.close()


# Alias de compatibilidad para módulos que aún usen los nombres anteriores
def inicializar_base_datos():
    inicializar_todo()

def inicializar_base_datos_maquinas_dinamica():
    con = sqlite3.connect(DB_NAME)
    cur = con.cursor()
    cur.execute("PRAGMA foreign_keys = ON")
    _init_maquinas(cur)
    con.commit()
    con.close()


# ─────────────────────────────────────────────────────────────────────────────
# CRUD — PROVEEDORES
# ─────────────────────────────────────────────────────────────────────────────

def obtener_tablas_auxiliares():
    """Retorna dicts (nombre → id) para poblar ComboBoxes del formulario."""
    con = sqlite3.connect(DB_NAME)
    cur = con.cursor()
    cur.execute("SELECT nombre, id FROM tipos_contribuyente")
    contribuyentes = dict(cur.fetchall())
    cur.execute("SELECT CAST(valor AS TEXT) || '%', id FROM porcentajes_retencion")
    retenciones = dict(cur.fetchall())
    cur.execute("SELECT nombre, id FROM tipos_proveedor")
    tipos = dict(cur.fetchall())
    con.close()
    return contribuyentes, retenciones, tipos


def obtener_proveedores(filtro: str = "", tipo: str = "") -> list:
    """
    Retorna lista de dicts con todos los proveedores (joins resueltos).
    - filtro: busca por razón social o RIF (case-insensitive).
    - tipo:   filtra por nombre de tipo_proveedor (vacío = todos).
    """
    con = sqlite3.connect(DB_NAME)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute("""
        SELECT
            p.id, p.razon_social, p.rif, p.direccion, p.telefono, p.correo,
            c.nombre                          AS tipo_contribuyente,
            (CAST(r.valor AS TEXT) || '%')    AS porcentaje_retencion,
            t.nombre                          AS tipo_proveedor
        FROM proveedores p
        JOIN tipos_contribuyente c ON p.contribuyente_id  = c.id
        JOIN porcentajes_retencion r ON p.retencion_id    = r.id
        JOIN tipos_proveedor t       ON p.tipo_proveedor_id = t.id
        ORDER BY p.razon_social ASC
    """)
    rows = [dict(r) for r in cur.fetchall()]
    con.close()
    if filtro:
        f = filtro.lower()
        rows = [r for r in rows
                if f in r["razon_social"].lower() or f in r["rif"].lower()]
    if tipo:
        rows = [r for r in rows if r["tipo_proveedor"].lower() == tipo.lower()]
    return rows


def obtener_proveedores_sistemas() -> list:
    """
    Retorna lista de nombres de proveedores con tipo 'Sistemas'.
    Usado para poblar el ComboBox en el módulo Sistemas.
    """
    con = sqlite3.connect(DB_NAME)
    cur = con.cursor()
    cur.execute("""
        SELECT p.razon_social
        FROM proveedores p
        JOIN tipos_proveedor t ON p.tipo_proveedor_id = t.id
        WHERE t.nombre = 'Sistemas'
        ORDER BY p.razon_social ASC
    """)
    rows = [r[0] for r in cur.fetchall()]
    con.close()
    return rows


def obtener_proveedores_fiscales() -> list:
    """
    Retorna lista de nombres de proveedores con tipo 'Máquinas Fiscales'.
    Usado para poblar el ComboBox de fabricantes en el módulo Máquinas.
    """
    con = sqlite3.connect(DB_NAME)
    cur = con.cursor()
    cur.execute("""
        SELECT p.razon_social
        FROM proveedores p
        JOIN tipos_proveedor t ON p.tipo_proveedor_id = t.id
        WHERE t.nombre = 'Máquinas Fiscales'
        ORDER BY p.razon_social ASC
    """)
    rows = [r[0] for r in cur.fetchall()]
    con.close()
    return rows


def guardar_proveedor(datos: tuple, prov_id: int = None):
    """
    Inserta o actualiza un proveedor.

    Args:
        datos: tuple de 8 valores (razon_social, rif, direccion,
               contribuyente_id, retencion_id, telefono, correo,
               tipo_proveedor_id)
        prov_id: ID del proveedor a actualizar (None = nuevo)
    """
    con = sqlite3.connect(DB_NAME)
    cur = con.cursor()
    if prov_id:
        cur.execute("""
            UPDATE proveedores SET
                razon_social=?, rif=?, direccion=?, contribuyente_id=?,
                retencion_id=?, telefono=?, correo=?, tipo_proveedor_id=?
            WHERE id=?
        """, (*datos, prov_id))
    else:
        cur.execute("""
            INSERT INTO proveedores
                (razon_social, rif, direccion, contribuyente_id,
                 retencion_id, telefono, correo, tipo_proveedor_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, datos)
    con.commit()
    con.close()


def eliminar_proveedor(prov_id: int):
    """Elimina un proveedor por su ID."""
    con = sqlite3.connect(DB_NAME)
    cur = con.cursor()
    cur.execute("DELETE FROM proveedores WHERE id=?", (prov_id,))
    con.commit()
    con.close()


# ---------------------------------------------------------------------------
# CLIENTES
# ---------------------------------------------------------------------------

def obtener_clientes(filtro: str = "") -> list:
    """
    Retorna lista de clientes como dicts.
    Si filtro != '', filtra por RIF o razón social (LIKE).
    Claves: id, rif, razon_social, direccion, correo,
            tipo_contribuyente, telefono
    """
    con = sqlite3.connect(DB_NAME)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    if filtro:
        f = f"%{filtro}%"
        cur.execute("""
            SELECT id, rif, razon_social,
                   direccion_fiscal AS direccion,
                   correo, tipo_contribuyente, telefono
            FROM clientes
            WHERE rif LIKE ? OR razon_social LIKE ?
            ORDER BY razon_social ASC
        """, (f, f))
    else:
        cur.execute("""
            SELECT id, rif, razon_social,
                   direccion_fiscal AS direccion,
                   correo, tipo_contribuyente, telefono
            FROM clientes
            ORDER BY razon_social ASC
        """)
    rows = [dict(r) for r in cur.fetchall()]
    con.close()
    return rows


def guardar_cliente(datos: tuple, cliente_id: int = None):
    """
    Inserta o actualiza un cliente.
    datos: (rif, razon_social, direccion_fiscal,
             correo, tipo_contribuyente, telefono)
    """
    con = sqlite3.connect(DB_NAME)
    cur = con.cursor()
    if cliente_id:
        cur.execute("""
            UPDATE clientes SET
                rif=?, razon_social=?, direccion_fiscal=?,
                correo=?, tipo_contribuyente=?, telefono=?
            WHERE id=?
        """, (*datos, cliente_id))
    else:
        cur.execute("""
            INSERT INTO clientes
                (rif, razon_social, direccion_fiscal,
                 correo, tipo_contribuyente, telefono)
            VALUES (?, ?, ?, ?, ?, ?)
        """, datos)
    con.commit()
    con.close()


def eliminar_cliente(cliente_id: int):
    """Elimina un cliente por su ID."""
    con = sqlite3.connect(DB_NAME)
    cur = con.cursor()
    cur.execute("DELETE FROM clientes WHERE id=?", (cliente_id,))
    con.commit()
    con.close()


# ---------------------------------------------------------------------------
# ROLES
# ---------------------------------------------------------------------------

def obtener_roles(filtro: str = "") -> list:
    """Retorna lista de roles como dicts: id, nombre, descripcion, es_admin."""
    con = sqlite3.connect(DB_NAME)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    if filtro:
        f = f"%{filtro}%"
        cur.execute(
            "SELECT id,nombre,descripcion,es_admin FROM roles WHERE nombre LIKE ? ORDER BY es_admin DESC, nombre ASC",
            (f,),
        )
    else:
        cur.execute(
            "SELECT id,nombre,descripcion,es_admin FROM roles ORDER BY es_admin DESC, nombre ASC"
        )
    rows = [dict(r) for r in cur.fetchall()]
    con.close()
    return rows


def obtener_permisos_rol(rol_id: int) -> dict:
    """
    Retorna dict: {clave: {"ver": 0/1, "editar": 0/1, "eliminar": 0/1}}
    """
    con = sqlite3.connect(DB_NAME)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute(
        "SELECT clave,ver,editar,eliminar FROM permisos WHERE rol_id=?",
        (rol_id,),
    )
    result = {r["clave"]: {"ver": r["ver"], "editar": r["editar"], "eliminar": r["eliminar"]}
              for r in cur.fetchall()}
    con.close()
    return result


def guardar_rol(nombre: str, descripcion: str, permisos: dict,
                rol_id: int = None) -> str:
    """
    Crea o actualiza un rol junto con sus permisos.
    permisos: {clave: {"ver": 0/1, "editar": 0/1, "eliminar": 0/1}}
    Retorna '' si ok, mensaje de error si falla.
    """
    con = sqlite3.connect(DB_NAME)
    cur = con.cursor()
    cur.execute("PRAGMA foreign_keys = ON")
    try:
        if rol_id is None:
            cur.execute(
                "INSERT INTO roles (nombre,descripcion,es_admin) VALUES (?,?,0)",
                (nombre, descripcion),
            )
            rol_id = cur.lastrowid
        else:
            cur.execute(
                "UPDATE roles SET nombre=?,descripcion=? WHERE id=?",
                (nombre, descripcion, rol_id),
            )
            cur.execute("DELETE FROM permisos WHERE rol_id=?", (rol_id,))

        for clave, p in permisos.items():
            cur.execute(
                "INSERT INTO permisos (rol_id,clave,ver,editar,eliminar) VALUES (?,?,?,?,?)",
                (rol_id, clave, int(p.get("ver", 0)),
                 int(p.get("editar", 0)), int(p.get("eliminar", 0))),
            )
        con.commit()
        return ""
    except sqlite3.IntegrityError:
        return "Ya existe un rol con ese nombre."
    finally:
        con.close()


def eliminar_rol(rol_id: int):
    """Elimina un rol y sus permisos (CASCADE)."""
    con = sqlite3.connect(DB_NAME)
    cur = con.cursor()
    cur.execute("PRAGMA foreign_keys = ON")
    cur.execute("DELETE FROM roles WHERE id=?", (rol_id,))
    con.commit()
    con.close()


def obtener_lista_roles_simple() -> list:
    """Retorna lista de (id, nombre) para ComboBoxes."""
    con = sqlite3.connect(DB_NAME)
    cur = con.cursor()
    cur.execute("SELECT id, nombre FROM roles ORDER BY es_admin DESC, nombre ASC")
    rows = cur.fetchall()
    con.close()
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# CRUD — DOCUMENTOS
# ─────────────────────────────────────────────────────────────────────────────

# ── Modelos (helpers para listas) ────────────────────────────────────────────
def listar_modelos_sistemas() -> list:
    """Retorna [(id, nombre)] de modelos de sistemas."""
    con = sqlite3.connect(DB_NAME)
    rows = con.execute("SELECT id, nombre FROM modelos_sistemas ORDER BY nombre").fetchall()
    con.close()
    return rows


def listar_modelos_maquinas() -> list:
    """Retorna [(id, nombre)] de modelos de máquinas."""
    con = sqlite3.connect(DB_NAME)
    rows = con.execute("SELECT id, nombre FROM modelos_maquinas ORDER BY nombre").fetchall()
    con.close()
    return rows


def listar_maquinas_por_modelo(modelo_id: int) -> list:
    """Retorna [(id, numero_registro, numero_serial, cliente, firmware)] para un modelo."""
    con = sqlite3.connect(DB_NAME)
    rows = con.execute(
        "SELECT id, numero_registro, numero_serial, cliente, firmware "
        "FROM maquinas_fiscales WHERE modelo_id=? ORDER BY numero_registro",
        (modelo_id,)
    ).fetchall()
    con.close()
    return rows


def listar_licencias_con_contrato(modelo_id: int) -> list:
    """Retorna licencias de un modelo de sistema que tengan contrato adjunto."""
    con = sqlite3.connect(DB_NAME)
    rows = con.execute(
        "SELECT id, licencia, version, cliente, ruta_contrato "
        "FROM sistemas_licencias "
        "WHERE modelo_id=? AND ruta_contrato IS NOT NULL AND ruta_contrato != '' "
        "ORDER BY licencia",
        (modelo_id,)
    ).fetchall()
    con.close()
    return rows


# ── Homologaciones ────────────────────────────────────────────────────────────
def listar_homologaciones(modelo_sistema_id: int) -> list:
    con = sqlite3.connect(DB_NAME)
    rows = con.execute(
        "SELECT id, nombre, ruta, fecha_subida FROM doc_homologaciones "
        "WHERE modelo_sistema_id=? ORDER BY fecha_subida DESC",
        (modelo_sistema_id,)
    ).fetchall()
    con.close()
    return rows


def agregar_homologacion(modelo_sistema_id: int, nombre: str, ruta: str) -> int:
    con = sqlite3.connect(DB_NAME)
    cur = con.execute(
        "INSERT INTO doc_homologaciones (modelo_sistema_id, nombre, ruta) VALUES (?,?,?)",
        (modelo_sistema_id, nombre, ruta)
    )
    new_id = cur.lastrowid
    con.commit()
    con.close()
    return new_id


def eliminar_homologacion(doc_id: int):
    con = sqlite3.connect(DB_NAME)
    con.execute("DELETE FROM doc_homologaciones WHERE id=?", (doc_id,))
    con.commit()
    con.close()


# ── Cartas de Enajenación ─────────────────────────────────────────────────────
def listar_enajenacion(modelo_maquina_id: int) -> list:
    con = sqlite3.connect(DB_NAME)
    rows = con.execute(
        "SELECT id, nombre, ruta, fecha_subida FROM doc_enajenacion "
        "WHERE modelo_maquina_id=? ORDER BY fecha_subida DESC",
        (modelo_maquina_id,)
    ).fetchall()
    con.close()
    return rows


def agregar_enajenacion(modelo_maquina_id: int, nombre: str, ruta: str) -> int:
    con = sqlite3.connect(DB_NAME)
    cur = con.execute(
        "INSERT INTO doc_enajenacion (modelo_maquina_id, nombre, ruta) VALUES (?,?,?)",
        (modelo_maquina_id, nombre, ruta)
    )
    new_id = cur.lastrowid
    con.commit()
    con.close()
    return new_id


def eliminar_enajenacion(doc_id: int):
    con = sqlite3.connect(DB_NAME)
    con.execute("DELETE FROM doc_enajenacion WHERE id=?", (doc_id,))
    con.commit()
    con.close()


# ── Carta de Entrega (template editable) ──────────────────────────────────────
def obtener_carta_entrega(modelo_maquina_id: int) -> str:
    con = sqlite3.connect(DB_NAME)
    row = con.execute(
        "SELECT contenido FROM doc_carta_entrega WHERE modelo_maquina_id=?",
        (modelo_maquina_id,)
    ).fetchone()
    con.close()
    return row[0] if row else ""


def guardar_carta_entrega(modelo_maquina_id: int, contenido: str):
    con = sqlite3.connect(DB_NAME)
    con.execute("""
        INSERT INTO doc_carta_entrega (modelo_maquina_id, contenido, fecha_mod)
        VALUES (?,?,CURRENT_TIMESTAMP)
        ON CONFLICT(modelo_maquina_id)
        DO UPDATE SET contenido=excluded.contenido, fecha_mod=excluded.fecha_mod
    """, (modelo_maquina_id, contenido))
    con.commit()
    con.close()


# ── Providencias ──────────────────────────────────────────────────────────────
def listar_providencias(filtro: str = "") -> list:
    con = sqlite3.connect(DB_NAME)
    q = f"%{filtro}%"
    rows = con.execute(
        "SELECT id, nombre, descripcion, ruta, fecha_publicacion, fecha_subida "
        "FROM doc_providencias WHERE nombre LIKE ? OR descripcion LIKE ? "
        "ORDER BY fecha_publicacion DESC, fecha_subida DESC",
        (q, q)
    ).fetchall()
    con.close()
    return rows


def agregar_providencia(nombre: str, descripcion: str, ruta: str, fecha_pub: str) -> int:
    con = sqlite3.connect(DB_NAME)
    cur = con.execute(
        "INSERT INTO doc_providencias (nombre, descripcion, ruta, fecha_publicacion) VALUES (?,?,?,?)",
        (nombre, descripcion, ruta, fecha_pub)
    )
    new_id = cur.lastrowid
    con.commit()
    con.close()
    return new_id


def eliminar_providencia(doc_id: int):
    con = sqlite3.connect(DB_NAME)
    con.execute("DELETE FROM doc_providencias WHERE id=?", (doc_id,))
    con.commit()
    con.close()


# ── Carpetas y Documentos Varios ──────────────────────────────────────────────
def listar_carpetas() -> list:
    con = sqlite3.connect(DB_NAME)
    rows = con.execute("SELECT id, nombre FROM doc_carpetas ORDER BY nombre").fetchall()
    con.close()
    return rows


def crear_carpeta(nombre: str) -> int:
    con = sqlite3.connect(DB_NAME)
    try:
        cur = con.execute("INSERT INTO doc_carpetas (nombre) VALUES (?)", (nombre,))
        new_id = cur.lastrowid
        con.commit()
        return new_id
    except sqlite3.IntegrityError:
        return -1
    finally:
        con.close()


def eliminar_carpeta(carpeta_id: int):
    con = sqlite3.connect(DB_NAME)
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("DELETE FROM doc_carpetas WHERE id=?", (carpeta_id,))
    con.commit()
    con.close()


def listar_doc_varios(carpeta_id: int) -> list:
    con = sqlite3.connect(DB_NAME)
    rows = con.execute(
        "SELECT id, nombre, descripcion, ruta, fecha_subida FROM doc_varios "
        "WHERE carpeta_id=? ORDER BY fecha_subida DESC",
        (carpeta_id,)
    ).fetchall()
    con.close()
    return rows


def agregar_doc_varios(carpeta_id: int, nombre: str, descripcion: str, ruta: str) -> int:
    con = sqlite3.connect(DB_NAME)
    cur = con.execute(
        "INSERT INTO doc_varios (carpeta_id, nombre, descripcion, ruta) VALUES (?,?,?,?)",
        (carpeta_id, nombre, descripcion, ruta)
    )
    new_id = cur.lastrowid
    con.commit()
    con.close()
    return new_id


def eliminar_doc_varios(doc_id: int):
    con = sqlite3.connect(DB_NAME)
    con.execute("DELETE FROM doc_varios WHERE id=?", (doc_id,))
    con.commit()
    con.close()


# ── Departamentos ──────────────────────────────────────────────────────────────
def listar_departamentos() -> list:
    con = sqlite3.connect(DB_NAME)
    rows = con.execute("SELECT id, nombre FROM departamentos ORDER BY nombre").fetchall()
    con.close()
    return rows


def crear_departamento(nombre: str) -> int:
    """Retorna nuevo id, o -1 si el nombre ya existe."""
    con = sqlite3.connect(DB_NAME)
    try:
        cur = con.execute("INSERT INTO departamentos (nombre) VALUES (?)", (nombre,))
        new_id = cur.lastrowid
        con.commit()
        return new_id
    except sqlite3.IntegrityError:
        return -1
    finally:
        con.close()


def actualizar_departamento(dep_id: int, nombre: str) -> bool:
    con = sqlite3.connect(DB_NAME)
    try:
        con.execute("UPDATE departamentos SET nombre=? WHERE id=?", (nombre, dep_id))
        con.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        con.close()


def eliminar_departamento(dep_id: int):
    con = sqlite3.connect(DB_NAME)
    con.execute("DELETE FROM departamentos WHERE id=?", (dep_id,))
    con.commit()
    con.close()


# ── Grupos ─────────────────────────────────────────────────────────────────────
def listar_grupos() -> list:
    """Retorna (id, nombre, departamento_id, departamento_nombre)."""
    con = sqlite3.connect(DB_NAME)
    rows = con.execute(
        "SELECT g.id, g.nombre, g.departamento_id, d.nombre "
        "FROM grupos g JOIN departamentos d ON d.id = g.departamento_id "
        "ORDER BY g.nombre"
    ).fetchall()
    con.close()
    return rows


def crear_grupo(nombre: str, departamento_id: int) -> int:
    con = sqlite3.connect(DB_NAME)
    try:
        cur = con.execute(
            "INSERT INTO grupos (nombre, departamento_id) VALUES (?,?)",
            (nombre, departamento_id)
        )
        new_id = cur.lastrowid
        con.commit()
        return new_id
    except sqlite3.IntegrityError:
        return -1
    finally:
        con.close()


def actualizar_grupo(grupo_id: int, nombre: str, departamento_id: int) -> bool:
    con = sqlite3.connect(DB_NAME)
    try:
        con.execute(
            "UPDATE grupos SET nombre=?, departamento_id=? WHERE id=?",
            (nombre, departamento_id, grupo_id)
        )
        con.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        con.close()


def eliminar_grupo(grupo_id: int):
    con = sqlite3.connect(DB_NAME)
    con.execute("DELETE FROM grupos WHERE id=?", (grupo_id,))
    con.commit()
    con.close()


# ── Marcas ─────────────────────────────────────────────────────────────────────
def get_marcas(filtro: str = "") -> list[dict]:
    con = sqlite3.connect(DB_NAME)
    con.row_factory = sqlite3.Row
    q = "SELECT * FROM marcas"
    params = ()
    if filtro:
        q += " WHERE nombre LIKE ?"
        params = (f"%{filtro}%",)
    q += " ORDER BY nombre"
    rows = [dict(r) for r in con.execute(q, params).fetchall()]
    con.close()
    return rows

def add_marca(nombre: str) -> bool:
    try:
        con = sqlite3.connect(DB_NAME)
        con.execute("INSERT INTO marcas (nombre) VALUES (?)", (nombre.strip(),))
        con.commit()
        con.close()
        return True
    except sqlite3.IntegrityError:
        return False

def update_marca(marca_id: int, nombre: str) -> bool:
    try:
        con = sqlite3.connect(DB_NAME)
        con.execute("UPDATE marcas SET nombre=? WHERE id=?", (nombre.strip(), marca_id))
        con.commit()
        con.close()
        return True
    except sqlite3.IntegrityError:
        return False

def eliminar_marca(marca_id: int):
    con = sqlite3.connect(DB_NAME)
    con.execute("DELETE FROM marcas WHERE id=?", (marca_id,))
    con.commit()
    con.close()


# ── Ítems de Inventario ────────────────────────────────────────────────────────
def get_items_inventario(filtro: str = "") -> list:
    con = sqlite3.connect(DB_NAME)
    con.row_factory = sqlite3.Row
    q = """
        SELECT i.*,
               m.nombre  AS marca_nombre,
               d.nombre  AS departamento_nombre,
               g.nombre  AS grupo_nombre
        FROM items_inventario i
        LEFT JOIN marcas       m ON m.id = i.marca_id
        LEFT JOIN departamentos d ON d.id = i.departamento_id
        LEFT JOIN grupos        g ON g.id = i.grupo_id
    """
    params = ()
    if filtro:
        q += " WHERE i.codigo LIKE ? OR i.nombre LIKE ?"
        params = (f"%{filtro}%", f"%{filtro}%")
    q += " ORDER BY i.nombre"
    rows = [dict(r) for r in con.execute(q, params).fetchall()]
    con.close()
    return rows

def add_item_inventario(codigo, nombre, descripcion, marca_id, departamento_id,
                        grupo_id, unidad_medida, stock, stock_minimo,
                        precio_costo, precio_venta) -> bool:
    try:
        con = sqlite3.connect(DB_NAME)
        con.execute("""
            INSERT INTO items_inventario
            (codigo,nombre,descripcion,marca_id,departamento_id,grupo_id,
             unidad_medida,stock,stock_minimo,precio_costo,precio_venta)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (codigo, nombre, descripcion, marca_id or None, departamento_id or None,
              grupo_id or None, unidad_medida, stock, stock_minimo,
              precio_costo, precio_venta))
        con.commit()
        con.close()
        return True
    except sqlite3.IntegrityError:
        return False

def update_item_inventario(item_id, codigo, nombre, descripcion, marca_id,
                           departamento_id, grupo_id, unidad_medida,
                           stock_minimo, precio_costo, precio_venta) -> bool:
    try:
        con = sqlite3.connect(DB_NAME)
        con.execute("""
            UPDATE items_inventario
            SET codigo=?,nombre=?,descripcion=?,marca_id=?,departamento_id=?,
                grupo_id=?,unidad_medida=?,stock_minimo=?,precio_costo=?,precio_venta=?
            WHERE id=?
        """, (codigo, nombre, descripcion, marca_id or None, departamento_id or None,
              grupo_id or None, unidad_medida, stock_minimo,
              precio_costo, precio_venta, item_id))
        con.commit()
        con.close()
        return True
    except sqlite3.IntegrityError:
        return False

def eliminar_item_inventario(item_id: int):
    con = sqlite3.connect(DB_NAME)
    con.execute("DELETE FROM items_inventario WHERE id=?", (item_id,))
    con.commit()
    con.close()


# ── Carga de Inventario ────────────────────────────────────────────────────────
def get_cargas_inventario(filtro: str = "") -> list:
    con = sqlite3.connect(DB_NAME)
    con.row_factory = sqlite3.Row
    q = """
        SELECT c.*, i.nombre AS item_nombre, i.codigo AS item_codigo
        FROM carga_inventario c
        JOIN items_inventario i ON i.id = c.item_id
    """
    params = ()
    if filtro:
        q += " WHERE i.nombre LIKE ? OR i.codigo LIKE ? OR c.proveedor LIKE ?"
        params = (f"%{filtro}%", f"%{filtro}%", f"%{filtro}%")
    q += " ORDER BY c.created_at DESC"
    rows = [dict(r) for r in con.execute(q, params).fetchall()]
    con.close()
    return rows

def add_carga_inventario(item_id, cantidad, precio_unitario, proveedor,
                         referencia, observaciones, fecha, usuario) -> bool:
    try:
        con = sqlite3.connect(DB_NAME)
        con.execute("""
            INSERT INTO carga_inventario
            (item_id,cantidad,precio_unitario,proveedor,referencia,observaciones,fecha,usuario)
            VALUES (?,?,?,?,?,?,?,?)
        """, (item_id, cantidad, precio_unitario, proveedor,
              referencia, observaciones, fecha, usuario))
        con.execute("UPDATE items_inventario SET stock=stock+? WHERE id=?",
                    (cantidad, item_id))
        # Actualizar precio_costo con el precio de la carga (si viene > 0)
        if precio_unitario and precio_unitario > 0:
            con.execute("UPDATE items_inventario SET precio_costo=? WHERE id=?",
                        (precio_unitario, item_id))
        con.commit()
        con.close()
        return True
    except Exception:
        return False

def eliminar_carga_inventario(carga_id: int):
    con = sqlite3.connect(DB_NAME)
    row = con.execute("SELECT item_id, cantidad FROM carga_inventario WHERE id=?",
                      (carga_id,)).fetchone()
    if row:
        con.execute("UPDATE items_inventario SET stock=MAX(0,stock-?) WHERE id=?",
                    (row[1], row[0]))
        con.execute("DELETE FROM carga_inventario WHERE id=?", (carga_id,))
        con.commit()
    con.close()


# ── Descarga de Inventario ─────────────────────────────────────────────────────
def get_descargas_inventario(filtro: str = "") -> list:
    con = sqlite3.connect(DB_NAME)
    con.row_factory = sqlite3.Row
    q = """
        SELECT d.*, i.nombre AS item_nombre, i.codigo AS item_codigo
        FROM descarga_inventario d
        JOIN items_inventario i ON i.id = d.item_id
    """
    params = ()
    if filtro:
        q += " WHERE i.nombre LIKE ? OR i.codigo LIKE ? OR d.motivo LIKE ?"
        params = (f"%{filtro}%", f"%{filtro}%", f"%{filtro}%")
    q += " ORDER BY d.created_at DESC"
    rows = [dict(r) for r in con.execute(q, params).fetchall()]
    con.close()
    return rows

def add_descarga_inventario(item_id, cantidad, precio_unitario, motivo,
                            destino, referencia, observaciones, fecha, usuario) -> bool:
    try:
        con = sqlite3.connect(DB_NAME)
        con.execute("""
            INSERT INTO descarga_inventario
            (item_id,cantidad,precio_unitario,motivo,destino,referencia,observaciones,fecha,usuario)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (item_id, cantidad, precio_unitario, motivo, destino,
              referencia, observaciones, fecha, usuario))
        con.execute("UPDATE items_inventario SET stock=MAX(0,stock-?) WHERE id=?",
                    (cantidad, item_id))
        con.commit()
        con.close()
        return True
    except Exception:
        return False

def eliminar_descarga_inventario(descarga_id: int):
    con = sqlite3.connect(DB_NAME)
    row = con.execute("SELECT item_id, cantidad FROM descarga_inventario WHERE id=?",
                      (descarga_id,)).fetchone()
    if row:
        con.execute("UPDATE items_inventario SET stock=stock+? WHERE id=?",
                    (row[1], row[0]))
        con.execute("DELETE FROM descarga_inventario WHERE id=?", (descarga_id,))
        con.commit()
    con.close()


# ── Cotizaciones CRUD ─────────────────────────────────────────────────────────
def get_next_cotizacion_numero() -> str:
    import datetime
    con = sqlite3.connect(DB_NAME)
    year = datetime.date.today().year
    row = con.execute(
        "SELECT COUNT(*) FROM cotizaciones WHERE numero LIKE ?",
        (f"COT-{year}-%",)
    ).fetchone()
    con.close()
    n = (row[0] if row else 0) + 1
    return f"COT-{year}-{n:04d}"


def listar_cotizaciones(filtro: str = "") -> list:
    con = sqlite3.connect(DB_NAME)
    con.row_factory = sqlite3.Row
    q = """
        SELECT c.id, c.numero, c.fecha, c.estado, c.total, c.usuario,
               COALESCE(cl.razon_social, '(Sin cliente)') AS cliente_nombre,
               COALESCE(cl.rif, '') AS cliente_rif
        FROM cotizaciones c
        LEFT JOIN clientes cl ON cl.id = c.cliente_id
    """
    params = ()
    if filtro:
        q += " WHERE c.numero LIKE ? OR cl.razon_social LIKE ? OR cl.rif LIKE ?"
        f = f"%{filtro}%"
        params = (f, f, f)
    q += " ORDER BY c.id DESC"
    rows = [dict(r) for r in con.execute(q, params).fetchall()]
    con.close()
    return rows


def get_cotizacion_completa(cot_id: int) -> dict:
    con = sqlite3.connect(DB_NAME)
    con.row_factory = sqlite3.Row
    row = con.execute("""
        SELECT c.*, COALESCE(cl.razon_social,'') AS cliente_nombre,
               COALESCE(cl.rif,'') AS cliente_rif,
               COALESCE(cl.direccion_fiscal,'') AS cliente_dir
        FROM cotizaciones c
        LEFT JOIN clientes cl ON cl.id = c.cliente_id
        WHERE c.id = ?
    """, (cot_id,)).fetchone()
    if not row:
        con.close()
        return {}
    data = dict(row)
    data["items"] = [dict(r) for r in con.execute(
        "SELECT * FROM cotizacion_items WHERE cotizacion_id=? ORDER BY id",
        (cot_id,)
    ).fetchall()]
    con.close()
    return data


def add_cotizacion(numero, fecha, cliente_id, observaciones,
                   estado, usuario, items: list) -> int:
    total = sum(it["cantidad"] * it["precio_unitario"] for it in items)
    try:
        con = sqlite3.connect(DB_NAME)
        cur = con.cursor()
        cur.execute("""
            INSERT INTO cotizaciones(numero,fecha,cliente_id,observaciones,estado,usuario,total)
            VALUES (?,?,?,?,?,?,?)
        """, (numero, fecha, cliente_id, observaciones, estado, usuario, total))
        cot_id = cur.lastrowid
        for it in items:
            sub = round(it["cantidad"] * it["precio_unitario"], 4)
            cur.execute("""
                INSERT INTO cotizacion_items
                    (cotizacion_id,tipo,item_ref_id,descripcion,cantidad,precio_unitario,subtotal)
                VALUES (?,?,?,?,?,?,?)
            """, (cot_id, it["tipo"], it.get("item_ref_id"),
                  it["descripcion"], it["cantidad"], it["precio_unitario"], sub))
            # El precio de la cotización actualiza el precio de venta del producto
            if it.get("tipo") == "Inventario" and it.get("item_ref_id") \
                    and it.get("precio_unitario", 0) > 0:
                cur.execute(
                    "UPDATE items_inventario SET precio_venta=? WHERE id=?",
                    (it["precio_unitario"], it["item_ref_id"]))
        con.commit()
        con.close()
        return cot_id
    except Exception:
        return -1


def update_cotizacion(cot_id, numero, fecha, cliente_id,
                      observaciones, estado, items: list) -> bool:
    total = sum(it["cantidad"] * it["precio_unitario"] for it in items)
    try:
        con = sqlite3.connect(DB_NAME)
        con.execute("""
            UPDATE cotizaciones
               SET numero=?,fecha=?,cliente_id=?,observaciones=?,estado=?,total=?
             WHERE id=?
        """, (numero, fecha, cliente_id, observaciones, estado, total, cot_id))
        con.execute("DELETE FROM cotizacion_items WHERE cotizacion_id=?", (cot_id,))
        for it in items:
            sub = round(it["cantidad"] * it["precio_unitario"], 4)
            con.execute("""
                INSERT INTO cotizacion_items
                    (cotizacion_id,tipo,item_ref_id,descripcion,cantidad,precio_unitario,subtotal)
                VALUES (?,?,?,?,?,?,?)
            """, (cot_id, it["tipo"], it.get("item_ref_id"),
                  it["descripcion"], it["cantidad"], it["precio_unitario"], sub))
            # El precio de la cotización actualiza el precio de venta del producto
            if it.get("tipo") == "Inventario" and it.get("item_ref_id") \
                    and it.get("precio_unitario", 0) > 0:
                con.execute(
                    "UPDATE items_inventario SET precio_venta=? WHERE id=?",
                    (it["precio_unitario"], it["item_ref_id"]))
        con.commit()
        con.close()
        return True
    except Exception:
        return False


def eliminar_cotizacion(cot_id: int) -> bool:
    try:
        con = sqlite3.connect(DB_NAME)
        con.execute("DELETE FROM cotizacion_items WHERE cotizacion_id=?", (cot_id,))
        con.execute("DELETE FROM cotizaciones WHERE id=?", (cot_id,))
        con.commit()
        con.close()
        return True
    except Exception:
        return False
