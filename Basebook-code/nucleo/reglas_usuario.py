"""Validaciones puras relacionadas con usuarios."""

import re
from collections.abc import Mapping
from typing import Any

from nucleo.tipos import ROL_ADMINISTRADOR, ROLES, Resultado


_PATRON_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validar_registro(
    nombre: str,
    correo: str,
    contrasena: str,
    confirmacion: str,
    documento: str | None,
    telefono: str | None,
) -> list[str]:
    """Devuelve todos los errores del formulario de registro."""
    errores = []
    if not isinstance(nombre, str) or not nombre.strip():
        errores.append("El nombre es obligatorio.")
    if not isinstance(correo, str) or not _PATRON_CORREO.fullmatch(correo.strip()):
        errores.append("Ingresa un correo electrónico válido.")
    if not isinstance(contrasena, str) or len(contrasena) < 8:
        errores.append("La contraseña debe tener al menos 8 caracteres.")
    if contrasena != confirmacion:
        errores.append("Las contraseñas no coinciden.")
    documento = documento.strip() if isinstance(documento, str) else documento
    telefono = telefono.strip() if isinstance(telefono, str) else telefono
    if documento and not (isinstance(documento, str) and documento.isdigit()):
        errores.append("El documento solo debe contener dígitos.")
    if telefono and not (isinstance(telefono, str) and telefono.isdigit()):
        errores.append("El teléfono solo debe contener dígitos.")
    return errores


def normalizar_correo(correo: str) -> str:
    """Quita espacios exteriores y convierte el correo a minúsculas."""
    return correo.strip().lower()


def validar_cambio_rol(
    actor: Mapping[str, Any],
    usuario: Mapping[str, Any],
    nuevo_rol: str,
    administradores_activos: int,
) -> Resultado:
    """Valida un cambio de rol solicitado por un administrador."""
    if actor.get("rol") != ROL_ADMINISTRADOR:
        return Resultado(False, "Solo un administrador puede cambiar roles.")
    if (
        isinstance(administradores_activos, bool)
        or not isinstance(administradores_activos, int)
        or administradores_activos < 0
    ):
        return Resultado(False, "No se pudo validar la cantidad de administradores activos.")
    if not isinstance(nuevo_rol, str) or nuevo_rol not in ROLES:
        return Resultado(False, "El rol indicado no es válido.")
    if (
        actor.get("id") is not None
        and actor.get("id") == usuario.get("id")
        and nuevo_rol != ROL_ADMINISTRADOR
    ):
        return Resultado(False, "No puedes quitarte tu propio rol de administrador.")
    if (
        usuario.get("rol") == ROL_ADMINISTRADOR
        and usuario.get("activo") is True
        and nuevo_rol != ROL_ADMINISTRADOR
        and administradores_activos <= 1
    ):
        return Resultado(
            False, "No se puede dejar el sistema sin administradores activos."
        )
    return Resultado(True, datos={"rol": nuevo_rol})


def validar_cambio_estado(
    actor: Mapping[str, Any],
    usuario: Mapping[str, Any],
    nuevo_estado: bool,
    administradores_activos: int,
) -> Resultado:
    """Valida la activación o desactivación de una cuenta."""
    if actor.get("rol") != ROL_ADMINISTRADOR:
        return Resultado(False, "Solo un administrador puede cambiar estados.")
    if (
        isinstance(administradores_activos, bool)
        or not isinstance(administradores_activos, int)
        or administradores_activos < 0
    ):
        return Resultado(False, "No se pudo validar la cantidad de administradores activos.")
    if not isinstance(nuevo_estado, bool):
        return Resultado(False, "El estado debe ser activo o inactivo.")
    if (
        actor.get("id") is not None
        and actor.get("id") == usuario.get("id")
        and not nuevo_estado
    ):
        return Resultado(False, "No puedes desactivar tu propia cuenta.")
    if (
        usuario.get("rol") == ROL_ADMINISTRADOR
        and usuario.get("activo") is True
        and not nuevo_estado
        and administradores_activos <= 1
    ):
        return Resultado(
            False, "No se puede dejar el sistema sin administradores activos."
        )
    return Resultado(True, datos={"activo": nuevo_estado})