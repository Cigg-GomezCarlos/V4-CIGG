import re
import time
import sqlite3
from core.database import DB_NAME, generar_hash, sanitizar_entrada

# Variables de mitigación para ataques de fuerza bruta
INTENTOS_MAXIMOS = 3
TIEMPO_BLOQUEO_SEG = 30

control_acceso = {
    "intentos_fallidos": 0,
    "bloqueado_hasta": 0.0
}

def verificar_estado_bloqueo():
    """Comprueba si la interfaz de login se encuentra en mitigación temporal."""
    tiempo_actual = time.time()
    if control_acceso["bloqueado_hasta"] > tiempo_actual:
        tiempo_restante = int(control_acceso["bloqueado_hasta"] - tiempo_actual)
        return False, f"SISTEMA BLOQUEADO. Reintente en {tiempo_restante}s."
    return True, ""

def validar_credenciales_seguras(usuario, contrasena):
    """Valida el token de acceso comparando los hashes en la base de datos física."""
    
    # 1. Sanitización de strings en el frontend
    usuario_limpio = sanitizar_entrada(usuario)
    contrasena_limpia = sanitizar_entrada(contrasena)

    if not usuario_limpio or not contrasena_limpia:
        return False, "Caracteres inválidos o campos vacíos."

    # 2. Protección perimetral contra fuerza bruta
    permitido, mensaje_bloqueo = verificar_estado_bloqueo()
    if not permitido:  # <-- Asegúrate de que diga 'permitido' y no 'permitted'
        return False, mensaje_bloqueo


    # 3. Consulta de seguridad a la base de datos persistente
    conexion = sqlite3.connect(DB_NAME)
    cursor = conexion.cursor()
    
    # Buscar al usuario utilizando sentencias preparadas (Anti-SQL Injection)
    cursor.execute("SELECT salt, password_hash FROM usuarios WHERE username = ?", (usuario_limpio,))
    registro = cursor.fetchone()
    conexion.close()

    if registro:
        salt_guardada, hash_guardado = registro
        
        # Re-generar el hash de la contraseña ingresada usando la Sal original de la DB
        _, nuevo_hash = generar_hash(contrasena_limpia, bytes.fromhex(salt_guardada))
        
        # Comparar en tiempo constante el hash calculado contra el de la base de datos
        if nuevo_hash == hash_guardado:
            control_acceso["intentos_fallidos"] = 0
            control_acceso["bloqueado_hasta"] = 0.0
            return True, "ACCESO AUTORIZADO"

    # 4. Procesamiento de intentos fallidos
    control_acceso["intentos_fallidos"] += 1
    if control_acceso["intentos_fallidos"] >= INTENTOS_MAXIMOS:
        control_acceso["bloqueado_hasta"] = time.time() + TIEMPO_BLOQUEO_SEG
        return False, f"ALERTA: Límite excedido. Bloqueado por {TIEMPO_BLOQUEO_SEG}s."
    
    intentos_restantes = INTENTOS_MAXIMOS - control_acceso["intentos_fallidos"]
    return False, f"Token o ID Inválidos. Intentos restantes: {intentos_restantes}"
