"""
core/session.py
---------------
Almacena el usuario activo en memoria para que cualquier módulo
pueda consultarlo sin necesidad de pasarlo como parámetro.
"""

_usuario_actual: str = ""


def set_usuario_actual(username: str) -> None:
    global _usuario_actual
    _usuario_actual = username or ""


def get_usuario_actual() -> str:
    return _usuario_actual


def clear_session() -> None:
    global _usuario_actual
    _usuario_actual = ""
