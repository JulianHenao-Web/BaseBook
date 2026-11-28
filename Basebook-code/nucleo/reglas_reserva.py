"""Reglas puras para reservas."""

from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any

from nucleo.tipos import (
    LIBRO_ACTIVO,
    RESERVA_EN_ESPERA,
    RESERVA_LISTA,
    ROL_BIBLIOTECARIO,
    Resultado,
)


def evaluar_reserva(
    lector: Mapping[str, Any],
    libro: Mapping[str, Any],
    ejemplares_disponibles: int,
    reserva_activa: Any,
    prestamo_activo_mismo_libro: Any,
) -> Resultado:
    """Evalúa si un lector puede reservar un libro sin ejemplares libres."""
    if lector.get("activo") is not True:
        return Resultado(False, "El lector no tiene una cuenta activa.")
    if libro.get("estado") != LIBRO_ACTIVO:
        return Resultado(False, "El libro no está activo para reserva.")
    if (
        isinstance(ejemplares_disponibles, bool)
        or not isinstance(ejemplares_disponibles, int)
        or ejemplares_disponibles < 0
    ):
        return Resultado(False, "La disponibilidad del libro no es válida.")
    if ejemplares_disponibles > 0:
        return Resultado(False, "Hay ejemplares disponibles; solicita un préstamo.")
    if reserva_activa:
        return Resultado(False, "Ya tienes una reserva activa para este libro.")
    if prestamo_activo_mismo_libro:
        return Resultado(False, "Ya tienes este libro en préstamo.")
    return Resultado(True)


def siguiente_en_cola(reservas: Sequence[Mapping[str, Any]]) -> Mapping[str, Any] | None:
    """Devuelve la reserva en espera con la fecha de solicitud más antigua."""
    en_espera = [
        (indice, reserva)
        for indice, reserva in enumerate(reservas)
        if reserva.get("estado") == RESERVA_EN_ESPERA
    ]
    if not en_espera:
        return None

    campos_fecha = (
        "fecha_reserva",
        "fecha_solicitud",
        "fecha_creacion",
        "creado_en",
    )

    def clave(item: tuple[int, Mapping[str, Any]]) -> tuple[Any, int]:
        indice, reserva = item
        fecha = next((reserva[campo] for campo in campos_fecha if campo in reserva), None)
        return (fecha is None, fecha if fecha is not None else indice)

    return min(en_espera, key=clave)[1]


def reserva_vencida(fecha_limite_recogida: date, hoy: date) -> bool:
    """Indica si ya pasó la fecha límite de recogida."""
    return hoy > fecha_limite_recogida


def puede_cancelar(
    reserva: Mapping[str, Any], id_sesion: Any, rol: str
) -> Resultado:
    """Solo dueño o bibliotecario pueden cancelar una reserva no finalizada."""
    if reserva.get("estado") not in (RESERVA_EN_ESPERA, RESERVA_LISTA):
        return Resultado(False, "Esta reserva ya no se puede cancelar.")
    if rol != ROL_BIBLIOTECARIO and (
        rol != "lector"
        or id_sesion is None
        or id_sesion != reserva.get("usuario_id", reserva.get("lector_id"))
    ):
        return Resultado(False, "No tienes permiso para cancelar esta reserva.")
    return Resultado(True)