"""Reglas puras para préstamos y devoluciones."""

from collections.abc import Mapping, Sequence
from datetime import date, timedelta
from typing import Any

from nucleo.tipos import LIBRO_ACTIVO, PRESTAMO_ACTIVO, Resultado


def calcular_fecha_limite(hoy: date, dias: int) -> date:
    """Calcula la fecha límite sumando días calendario a la fecha inicial."""
    if isinstance(dias, bool) or not isinstance(dias, int) or dias < 0:
        raise ValueError("Los días del préstamo deben ser un entero no negativo.")
    return hoy + timedelta(days=dias)


def evaluar_prestamo(
    lector: Mapping[str, Any],
    libro: Mapping[str, Any],
    multas_pendientes: Any,
    prestamos_activos: Sequence[Mapping[str, Any]],
    dias_prestamo: int,
    hoy: date,
) -> Resultado:
    """Evalúa un préstamo en el orden de prioridad establecido."""
    if lector.get("activo") is not True:
        return Resultado(False, "El lector no tiene una cuenta activa.")
    if libro.get("estado") != LIBRO_ACTIVO:
        return Resultado(False, "El libro no está activo para préstamo.")
    disponibles = libro.get("ejemplares_disponibles", 0)
    if not (
        isinstance(disponibles, int)
        and not isinstance(disponibles, bool)
        and disponibles > 0
    ):
        return Resultado(
            False, "No hay ejemplares disponibles. Puedes reservar este libro."
        )
    if _hay_multas_pendientes(multas_pendientes):
        return Resultado(False, "Tienes multas pendientes que debes pagar antes de solicitar un préstamo.")
    if any(_es_mismo_libro(prestamo, libro) for prestamo in prestamos_activos):
        return Resultado(False, "Ya tienes este libro en préstamo.")
    if isinstance(dias_prestamo, bool) or not isinstance(dias_prestamo, int) or dias_prestamo < 0:
        return Resultado(False, "El período del préstamo no es válido.")

    fecha_limite = calcular_fecha_limite(hoy, dias_prestamo)
    return Resultado(
        True,
        datos={"fecha_prestamo": hoy, "fecha_limite": fecha_limite},
    )


def _hay_multas_pendientes(multas: Any) -> bool:
    if isinstance(multas, bool):
        return multas
    if isinstance(multas, int):
        return multas > 0
    return bool(multas)


def _es_mismo_libro(prestamo: Mapping[str, Any], libro: Mapping[str, Any]) -> bool:
    if prestamo.get("estado", PRESTAMO_ACTIVO) != PRESTAMO_ACTIVO:
        return False
    identificador = libro.get("isbn", libro.get("id"))
    return identificador is not None and identificador in (
        prestamo.get("isbn"),
        prestamo.get("libro_id"),
        prestamo.get("id_libro"),
    )


def esta_vencido(fecha_limite: date, hoy: date) -> bool:
    """Un préstamo vence cuando hoy es posterior a su fecha límite."""
    return hoy > fecha_limite


def puede_devolverse(prestamo: Mapping[str, Any]) -> Resultado:
    """Comprueba que el préstamo todavía esté activo."""
    if prestamo.get("estado") != PRESTAMO_ACTIVO:
        return Resultado(False, "Este préstamo ya fue devuelto.")
    return Resultado(True)