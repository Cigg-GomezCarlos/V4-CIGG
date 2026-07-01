"""
modulos/monedas/__init__.py
============================
Punto de entrada del módulo Monedas.

Re-exporta los símbolos públicos necesarios para main.py:
  - ModuloMonedas         → clase UI principal
  - inicializar_tablas    → llamar al arranque de la app
  - actualizar_en_background → actualización automática al iniciar
"""

from .ui import ModuloMonedas
from .db import inicializar_tablas, actualizar_en_background

__all__ = ["ModuloMonedas", "inicializar_tablas", "actualizar_en_background"]
