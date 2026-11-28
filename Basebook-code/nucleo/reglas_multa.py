"""Reglas puras para el cálculo y modificación de multas."""

from collections.abc import Mapping
from datetime import date
from typing import Any

from nucleo.tipos import MULTA_PAGADA, Resultado


def calcular_dias_retraso(fecha_limite: date, fecha_devolucion: date) -> int:
    """Calcula los días de retraso, con mínimo de cero."""
    return max(0, (fecha_devolucion - fecha_limite).days)


def calcular_monto(dias: int, valor_dia: int) -> int:
    """Calcula el monto en pesos enteros."""
    if (
        isinstance(dias, bool)
        or not isinstance(dias, int)
        or dias < 0
        or isinstance(valor_dia, bool)
        or not isinstance(valor_dia, int)
        or valor_dia < 0
    ):
        raise ValueError("Los días y el valor diario deben ser enteros no negativos.")
    return dias * valor_dia


def evaluar_multa(
    fecha_limite: date, fecha_devolucion: date, valor_dia: int
) -> Resultado:
    """Calcula la multa final o informa que no hubo retraso."""
    dias = calcular_dias_retraso(fecha_limite, fecha_devolucion)
    try:
        monto = calcular_monto(dias, valor_dia)
    except ValueError as error:
        return Resultado(False, str(error))
    datos = {"dias_retraso": dias, "valor_dia": valor_dia, "monto": monto}
    if dias == 0:
        return Resultado(True, "No hay multa por retraso.", datos)
    return Resultado(True, datos=datos)


def estimar_multa(fecha_limite: date, hoy: date, valor_dia: int) -> Resultado:
    """Calcula una multa provisional para un préstamo aún no devuelto."""
    return evaluar_multa(fecha_limite, hoy, valor_dia)


def validar_modificacion(
    multa: Mapping[str, Any], nuevo_monto: int, motivo: str
) -> Resultado:
    """Valida una modificación de monto mientras la multa siga pendiente."""
    if multa.get("estado") == MULTA_PAGADA:
        return Resultado(False, "No se puede modificar una multa pagada.")
    if isinstance(nuevo_monto, bool) or not isinstance(nuevo_monto, int) or nuevo_monto < 0:
        return Resultado(False, "El monto debe ser un entero mayor o igual a cero.")
    if not isinstance(motivo, str) or not motivo.strip():
        return Resultado(False, "El motivo de la modificación es obligatorio.")
    return Resultado(
        True, datos={"monto": nuevo_monto, "motivo": motivo.strip()}
    )