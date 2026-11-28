"""Tipos y constantes compartidos por las reglas de negocio."""

from dataclasses import dataclass, field
from typing import Any


ROL_LECTOR = "lector"
ROL_BIBLIOTECARIO = "bibliotecario"
ROL_ADMINISTRADOR = "administrador"
ROLES = frozenset((ROL_LECTOR, ROL_BIBLIOTECARIO, ROL_ADMINISTRADOR))

PRESTAMO_ACTIVO = "activo"
PRESTAMO_DEVUELTO = "devuelto"
ESTADOS_PRESTAMO = frozenset((PRESTAMO_ACTIVO, PRESTAMO_DEVUELTO))

RESERVA_EN_ESPERA = "en_espera"
RESERVA_LISTA = "lista"
RESERVA_CANCELADA = "cancelada"
RESERVA_ATENDIDA = "atendida"
ESTADOS_RESERVA = frozenset(
    (RESERVA_EN_ESPERA, RESERVA_LISTA, RESERVA_CANCELADA, RESERVA_ATENDIDA)
)

MULTA_PENDIENTE = "pendiente"
MULTA_PAGADA = "pagada"
ESTADOS_MULTA = frozenset((MULTA_PENDIENTE, MULTA_PAGADA))

LIBRO_ACTIVO = "activo"
LIBRO_INACTIVO = "inactivo"
ESTADOS_LIBRO = frozenset((LIBRO_ACTIVO, LIBRO_INACTIVO))


@dataclass(frozen=True)
class Resultado:
    """Resultado uniforme de una regla de negocio."""

    permitido: bool
    motivo: str | None = None
    datos: dict[str, Any] = field(default_factory=dict)