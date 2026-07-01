"""
modulos/archivos/sub_usuarios.py
=================================
Submódulo de gestión de usuarios del sistema CIGG.
Patrón idéntico a sub_proveedores / sub_clientes:
  – Lista con cabecera fija + área scrollable
  – Botón ➕ Nuevo Usuario abre modal
  – Modal incluye selector de Rol
  – Botones ✏️ editar y 🗑️ eliminar en cada fila
  – Búsqueda en tiempo real por nombre de usuario
"""

import sqlite3
import customtkinter as ctk
from core.permisos import puede
from tkinter import messagebox

from core.database import (
    DB_NAME, generar_hash, sanitizar_entrada, obtener_lista_roles_simple,
)


# ── helpers BD ────────────────────────────────────────────────────────────────

def _obtener_usuarios(filtro: str = "") -> list[dict]:
    con = sqlite3.connect(DB_NAME)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    q = """
        SELECT u.id, u.username,
               COALESCE(u.nombre_completo, '') AS nombre_completo,
               COALESCE(u.telefono, '')        AS telefono,
               COALESCE(u.correo,   '')        AS correo,
               COALESCE(r.nombre, 'Sin rol')   AS rol_nombre,
               COALESCE(u.rol_id, 1)           AS rol_id
        FROM   usuarios u
        LEFT JOIN roles r ON r.id = u.rol_id
    """
    if filtro:
        cur.execute(
            q + " WHERE u.username LIKE ? OR u.nombre_completo LIKE ? ORDER BY u.username ASC",
            (f"%{filtro}%", f"%{filtro}%"),
        )
    else:
        cur.execute(q + " ORDER BY u.username ASC")
    rows = [dict(r) for r in cur.fetchall()]
    con.close()
    return rows


def _guardar_usuario(username: str, password: str, rol_id: int = 1,
                     uid: int | None = None,
                     nombre_completo: str = "",
                     telefono: str = "",
                     correo: str = "") -> str:
    """Devuelve '' si ok, o mensaje de error."""
    con = sqlite3.connect(DB_NAME)
    cur = con.cursor()
    try:
        if uid is None:                          # crear
            if not password:
                return "La contraseña es obligatoria para un usuario nuevo."
            salt, p_hash = generar_hash(password)
            cur.execute(
                """INSERT INTO usuarios
                       (username, salt, password_hash, rol_id,
                        nombre_completo, telefono, correo)
                   VALUES (?,?,?,?,?,?,?)""",
                (username, salt, p_hash, rol_id,
                 nombre_completo, telefono, correo),
            )
        else:                                    # editar
            if password:
                salt, p_hash = generar_hash(password)
                cur.execute(
                    """UPDATE usuarios
                       SET username=?, salt=?, password_hash=?, rol_id=?,
                           nombre_completo=?, telefono=?, correo=?
                       WHERE id=?""",
                    (username, salt, p_hash, rol_id,
                     nombre_completo, telefono, correo, uid),
                )
            else:
                cur.execute(
                    """UPDATE usuarios
                       SET username=?, rol_id=?,
                           nombre_completo=?, telefono=?, correo=?
                       WHERE id=?""",
                    (username, rol_id,
                     nombre_completo, telefono, correo, uid),
                )
        con.commit()
        return ""
    except sqlite3.IntegrityError:
        return "Ya existe un usuario con ese nombre."
    finally:
        con.close()


def _eliminar_usuario(uid: int):
    con = sqlite3.connect(DB_NAME)
    cur = con.cursor()
    cur.execute("DELETE FROM usuarios WHERE id=?", (uid,))
    con.commit()
    con.close()


# ── módulo principal ──────────────────────────────────────────────────────────

class SubmoduloUsuarios(ctk.CTkFrame):
    """Panel de administración de usuarios del sistema CIGG."""

    def __init__(self, parent, estilos, permisos=None):
        super().__init__(parent, fg_color="transparent")
        self.estilos  = estilos
        self.permisos = permisos or {}
        self._puede_editar   = puede(self.permisos, "Archivos.Usuarios", "editar")
        self._puede_eliminar = puede(self.permisos, "Archivos.Usuarios", "eliminar")
        self.col = estilos["colores"]
        self.fnt = estilos["fuentes"]

        self.pack_propagate(False)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=0)
        self.rowconfigure(1, weight=0)
        self.rowconfigure(2, weight=1)

        self._construir_barra_superior()
        self._construir_cabecera()
        self._construir_lista()
        self._cargar_lista()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _construir_barra_superior(self):
        col, fnt = self.col, self.fnt
        barra = ctk.CTkFrame(self, fg_color="#020C1B", corner_radius=8)
        barra.grid(row=0, column=0, padx=10, pady=(10, 4), sticky="ew")
        barra.columnconfigure(1, weight=1)

        if self._puede_editar:
            ctk.CTkButton(
                barra, text="➕  Nuevo Usuario",
                fg_color=col["principal"], text_color="#0A192F",
                hover_color=col["principal_hover"],
                font=fnt["normal"], width=170,
                command=self._abrir_modal,
            ).grid(row=0, column=0, padx=12, pady=10)

        self.entry_busqueda = ctk.CTkEntry(
            barra, placeholder_text="🔍  Buscar por nombre…",
            font=fnt["normal"], border_color=col["principal"],
        )
        self.entry_busqueda.grid(row=0, column=1, padx=12, pady=10, sticky="ew")
        self.entry_busqueda.bind("<KeyRelease>", lambda _e: self._cargar_lista())

    def _construir_cabecera(self):
        col, fnt = self.col, self.fnt
        cab = ctk.CTkFrame(self, fg_color="#0A192F", corner_radius=0)
        cab.grid(row=1, column=0, padx=10, pady=0, sticky="ew")
        cab.columnconfigure(0, weight=3)
        cab.columnconfigure(1, weight=2)
        cab.columnconfigure(2, weight=1)

        for ci, txt in enumerate(["Usuario", "Rol", "Acciones"]):
            ctk.CTkLabel(
                cab, text=txt,
                font=(fnt["normal"][0], 12, "bold"),
                text_color=col["principal"], anchor="w",
            ).grid(row=0, column=ci, padx=14, pady=6, sticky="w")

    def _construir_lista(self):
        self.scroll = ctk.CTkScrollableFrame(
            self, fg_color="#020C1B", corner_radius=8
        )
        self.scroll.grid(row=2, column=0, padx=10, pady=(0, 10), sticky="nsew")
        self.scroll.columnconfigure(0, weight=3)
        self.scroll.columnconfigure(1, weight=2)
        self.scroll.columnconfigure(2, weight=1)

    # ── datos ─────────────────────────────────────────────────────────────────

    def _cargar_lista(self):
        for w in self.scroll.winfo_children():
            w.destroy()

        filtro = self.entry_busqueda.get().strip()
        usuarios = _obtener_usuarios(filtro)

        if not usuarios:
            ctk.CTkLabel(
                self.scroll, text="No hay usuarios registrados.",
                font=self.fnt["normal"], text_color="#64748B",
            ).grid(row=0, column=0, columnspan=3, pady=30)
            return

        for idx, u in enumerate(usuarios):
            bg = "#0A192F" if idx % 2 == 0 else "#071527"

            nombre_display = u["nombre_completo"] if u["nombre_completo"] \
                             else u["username"]
            ctk.CTkLabel(
                self.scroll,
                text=f"  👤  {nombre_display}",
                font=self.fnt["normal"], text_color="#E2E8F0",
                fg_color=bg, anchor="w", corner_radius=0,
            ).grid(row=idx, column=0, padx=0, pady=1, sticky="ew")

            ctk.CTkLabel(
                self.scroll,
                text=u["rol_nombre"],
                font=self.fnt["normal"], text_color="#94A3B8",
                fg_color=bg, anchor="w", corner_radius=0,
            ).grid(row=idx, column=1, padx=8, pady=1, sticky="ew")

            acciones = ctk.CTkFrame(self.scroll, fg_color=bg, corner_radius=0)
            acciones.grid(row=idx, column=2, padx=0, pady=1, sticky="ew")

            if self._puede_editar:
                ctk.CTkButton(
                    acciones, text="✏️", width=34, height=28,
                    fg_color="#1E3A5F", hover_color="#2A5080",
                    font=self.fnt["normal"],
                    command=lambda usr=u: self._abrir_modal(usr),
                ).pack(side="left", padx=3, pady=2)

            if u["id"] == 1:
                ctk.CTkLabel(
                    acciones, text="🔒", font=self.fnt["normal"],
                    text_color="#64748B", fg_color=bg,
                ).pack(side="left", padx=8, pady=2)
            elif self._puede_eliminar:
                ctk.CTkButton(
                    acciones, text="🗑️", width=34, height=28,
                    fg_color="#5F1E1E", hover_color="#802A2A",
                    font=self.fnt["normal"],
                    command=lambda uid=u["id"], un=u["username"]: self._confirmar_eliminar(uid, un),
                ).pack(side="left", padx=3, pady=2)

    # ── modal ─────────────────────────────────────────────────────────────────

    def _abrir_modal(self, usuario: dict | None = None):
        col, fnt = self.col, self.fnt
        editando = usuario is not None

        # Cargar roles disponibles
        roles_raw = obtener_lista_roles_simple()   # [(id, nombre), ...]
        roles_nombres = [r[1] for r in roles_raw]
        roles_ids     = [r[0] for r in roles_raw]

        modal = ctk.CTkToplevel(self)
        modal.title("Editar Usuario" if editando else "Nuevo Usuario")
        modal.geometry("460x580")
        modal.resizable(False, False)
        modal.grab_set()
        modal.configure(fg_color="#020C1B")

        ctk.CTkLabel(
            modal,
            text="Editar Usuario" if editando else "Nuevo Usuario",
            font=fnt["subtitulo"], text_color=col["principal"],
        ).pack(pady=(20, 10), padx=20)

        # ── campos ────────────────────────────────────────────────────────────
        campos_frame = ctk.CTkFrame(modal, fg_color="transparent")
        campos_frame.pack(fill="x", padx=24, pady=4)
        campos_frame.columnconfigure(1, weight=1)

        def sep(row, texto):
            """Separador visual de sección."""
            ctk.CTkLabel(
                campos_frame, text=texto,
                font=(fnt["normal"][0], 10, "bold"),
                text_color="#475569", anchor="w",
            ).grid(row=row, column=0, columnspan=2,
                   padx=0, pady=(10, 2), sticky="ew")

        def fila_entry(label, row, show=""):
            ctk.CTkLabel(
                campos_frame, text=label,
                font=fnt["normal"], text_color="#94A3B8", anchor="e",
            ).grid(row=row, column=0, padx=(0, 10), pady=5, sticky="e")
            e = ctk.CTkEntry(
                campos_frame, font=fnt["normal"],
                border_color=col["principal"], show=show,
            )
            e.grid(row=row, column=1, pady=5, sticky="ew")
            return e

        # ── Datos de acceso ───────────────────────────────────────────────────
        sep(0, "  ─── Datos de acceso")
        e_user = fila_entry("Usuario:",     1)
        e_pass = fila_entry("Contraseña:",  2, show="*")
        e_conf = fila_entry("Confirmar:",   3, show="*")

        # Selector de rol
        ctk.CTkLabel(
            campos_frame, text="Rol:", font=fnt["normal"],
            text_color="#94A3B8", anchor="e",
        ).grid(row=4, column=0, padx=(0, 10), pady=5, sticky="e")
        combo_rol = ctk.CTkComboBox(
            campos_frame, values=roles_nombres if roles_nombres else ["Sin roles"],
            font=fnt["normal"], border_color=col["principal"],
            button_color=col["principal"], dropdown_fg_color="#0A192F",
            state="readonly",
        )
        combo_rol.grid(row=4, column=1, pady=5, sticky="ew")

        # ── Datos personales ──────────────────────────────────────────────────
        sep(5, "  ─── Datos personales")
        e_nombre = fila_entry("Nombre completo:", 6)
        e_tel    = fila_entry("Teléfono:",        7)
        e_correo = fila_entry("Correo:",          8)

        # Precargar valores al editar
        if editando:
            e_user.insert(0, usuario["username"])
            e_nombre.insert(0, usuario.get("nombre_completo", ""))
            e_tel.insert(0,    usuario.get("telefono", ""))
            e_correo.insert(0, usuario.get("correo", ""))
            if usuario["rol_id"] in roles_ids:
                combo_rol.set(roles_nombres[roles_ids.index(usuario["rol_id"])])
            elif roles_nombres:
                combo_rol.set(roles_nombres[0])
            ctk.CTkLabel(
                campos_frame,
                text="Deja la contraseña en blanco para no cambiarla",
                font=(fnt["normal"][0], 10), text_color="#64748B",
            ).grid(row=9, column=0, columnspan=2, pady=(0, 2))
        else:
            if roles_nombres:
                combo_rol.set(roles_nombres[0])

        lbl_err = ctk.CTkLabel(modal, text="", font=fnt["normal"],
                               text_color=col["error"])
        lbl_err.pack(pady=(4, 0))

        # ── guardar ───────────────────────────────────────────────────────────
        def guardar():
            user    = sanitizar_entrada(e_user.get())
            pw      = e_pass.get()
            pw2     = e_conf.get()
            nombre  = sanitizar_entrada(e_nombre.get())
            tel     = sanitizar_entrada(e_tel.get())
            correo  = e_correo.get().strip()

            if not user:
                lbl_err.configure(text="El nombre de usuario es obligatorio.")
                return
            if pw and pw != pw2:
                lbl_err.configure(text="Las contraseñas no coinciden.")
                return

            sel_nombre = combo_rol.get()
            sel_rol_id = roles_ids[roles_nombres.index(sel_nombre)] \
                         if sel_nombre in roles_nombres else 1

            uid = usuario["id"] if editando else None
            err = _guardar_usuario(user, pw, sel_rol_id, uid,
                                   nombre_completo=nombre,
                                   telefono=tel,
                                   correo=correo)
            if err:
                lbl_err.configure(text=err)
                return

            modal.destroy()
            self._cargar_lista()

        ctk.CTkButton(
            modal, text="💾  Guardar",
            fg_color=col["principal"], text_color="#0A192F",
            hover_color=col["principal_hover"],
            font=fnt["normal"], command=guardar,
        ).pack(pady=14, padx=24, fill="x")

    # ── eliminar ──────────────────────────────────────────────────────────────

    def _confirmar_eliminar(self, uid: int, username: str):
        ok = messagebox.askyesno(
            "Eliminar usuario",
            f"¿Eliminar al usuario «{username}»?\nEsta acción no se puede deshacer.",
        )
        if ok:
            _eliminar_usuario(uid)
            self._cargar_lista()
