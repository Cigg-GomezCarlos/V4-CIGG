"""
core/permisos.py
================
Helper de permisos basado en roles.

⚠️  PERMISOS DESACTIVADOS TEMPORALMENTE
    cargar_permisos_usuario() devuelve admin total para todos los usuarios.
    puede() siempre retorna True.
    Reactivar cuando el módulo de Roles esté listo para producción:
      1. Descomentar el bloque "LÓGICA REAL" en cargar_permisos_usuario().
      2. Descomentar la lógica real en puede().
      3. Eliminar los retornos de bypass.

Uso (no cambia aunque esté desactivado):
    from core.permisos import cargar_permisos_usuario, puede

    permisos = cargar_permisos_usuario("carlos")

    if puede(permisos, "Archivos.Clientes", "ver"):      # mostrar pestaña
    if puede(permisos, "Archivos.Clientes", "editar"):   # mostrar botón ➕ / ✏️
    if puede(permisos, "Archivos.Clientes", "eliminar"): # mostrar botón 🗑️
"""

import sqlite3
from core.database import DB_NAME


def cargar_permisos_usuario(username: str) -> dict:
    """
    Retorna un dict con los permisos del usuario.

    Mientras los permisos estén desactivados siempre retorna admin total.
    """
    # ── BYPASS TEMPORAL ─────────────────────────────────────────────────────
    return {"_es_admin": True}
    # ────────────────────────────────────────────────────────────────────────

    # ── LÓGICA REAL (reactivar al finalizar el proyecto) ────────────────────
    # con = sqlite3.connect(DB_NAME)
    # cur = con.cursor()
    #
    # cur.execute("""
    #     SELECT u.rol_id, r.es_admin
    #     FROM   usuarios u
    #     JOIN   roles    r ON r.id = u.rol_id
    #     WHERE  u.username = ?
    # """, (username,))
    # row = cur.fetchone()
    #
    # if not row:
    #     con.close()
    #     return {"_es_admin": False}
    #
    # rol_id, es_admin = row
    #
    # if es_admin:
    #     con.close()
    #     return {"_es_admin": True}
    #
    # cur.execute(
    #     "SELECT clave, ver, editar, eliminar FROM permisos WHERE rol_id = ?",
    #     (rol_id,),
    # )
    # filas = cur.fetchall()
    # con.close()
    #
    # perms: dict = {"_es_admin": False}
    # for clave, ver, editar, eliminar in filas:
    #     perms[clave] = {
    #         "ver":      bool(ver),
    #         "editar":   bool(editar),
    #         "eliminar": bool(eliminar),
    #     }
    # return perms


def puede(permisos: dict, clave: str, accion: str = "ver") -> bool:
    """
    True si el rol permite la acción sobre la clave indicada.

    Mientras los permisos estén desactivados siempre retorna True.
    """
    # ── BYPASS TEMPORAL ─────────────────────────────────────────────────────
    return True
    # ────────────────────────────────────────────────────────────────────────

    # ── LÓGICA REAL (reactivar al finalizar el proyecto) ────────────────────
    # if permisos.get("_es_admin"):
    #     return True
    # entry = permisos.get(clave)
    # if not entry:
    #     return False
    # return bool(entry.get(accion, False))
