"""Fuente única de verdad de permisos por rol."""

from typing import Any

from nucleo.tipos import (
    ROL_ADMINISTRADOR,
    ROL_BIBLIOTECARIO,
    ROL_LECTOR,
    ROLES,
)


_PERMISOS = {
    ROL_LECTOR: frozenset(
        (
            "catalogo.consultar",
            "prestamo.solicitar",
            "reserva.crear",
            "multa.consultar_propias",
        )
    ),
    ROL_BIBLIOTECARIO: frozenset(
        (
            "catalogo.consultar",
            "catalogo.gestionar",
            "prestamo.registrar",
            "devolucion.registrar",
            "reserva.administrar",
            "multa.administrar",
        )
    ),
    ROL_ADMINISTRADOR: frozenset(
        ("usuario.gestionar", "rol.cambiar", "parametro.configurar")
    ),
}

_ACCIONES = frozenset(
    accion for permisos in _PERMISOS.values() for accion in permisos
)


def tiene_permiso(rol: str, accion: str) -> bool:
    """Indica si un rol conocido puede realizar una acción conocida."""
    if (
        not isinstance(rol, str)
        or not isinstance(accion, str)
        or rol not in ROLES
        or accion not in _ACCIONES
    ):
        return False
    return accion in _PERMISOS[rol]


def puede_ver_recurso(rol: str, id_sesion: Any, id_dueno: Any) -> bool:
    """Los lectores ven solo sus recursos y los bibliotecarios ven todos."""
    if rol == ROL_BIBLIOTECARIO:
        return True
    if rol == ROL_LECTOR:
        return id_sesion is not None and id_sesion == id_dueno
    return False