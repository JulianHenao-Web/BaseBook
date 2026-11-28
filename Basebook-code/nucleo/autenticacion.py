"""Validaciones puras relacionadas con la autenticación."""

from collections.abc import Mapping
from typing import Any

from nucleo.reglas_usuario import normalizar_correo
from nucleo.tipos import Resultado


def validar_credenciales(correo: str, contrasena: str) -> Resultado:
    """Comprueba que el correo y la contraseña tengan un formato utilizable."""
    if (
        not isinstance(correo, str)
        or not correo.strip()
        or not isinstance(contrasena, str)
        or not contrasena
    ):
        return Resultado(False, "No se pudo validar el inicio de sesión. Revisa tus datos.")

    correo_normalizado = normalizar_correo(correo)
    if not _correo_valido(correo_normalizado):
        return Resultado(False, "No se pudo validar el inicio de sesión. Revisa tus datos.")
    return Resultado(True, datos={"correo": correo_normalizado})


def _correo_valido(correo: str) -> bool:
    partes = correo.split("@")
    return (
        len(partes) == 2
        and bool(partes[0])
        and "." in partes[1]
        and all(partes)
        and not any(caracter.isspace() for caracter in correo)
        and not partes[1].startswith(".")
        and not partes[1].endswith(".")
    )


def usuario_de_sesion(sesion: Mapping[str, Any] | None) -> Any | None:
    """Obtiene el usuario guardado en una sesión o devuelve None."""
    if not isinstance(sesion, Mapping):
        return None
    usuario = sesion.get("usuario")
    return usuario if isinstance(usuario, Mapping) else None