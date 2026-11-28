"""Acceso a datos de multas."""

from datetime import date, datetime
from typing import Any

from almacen.conexion import cliente_admin
from almacen.usuarios import (
    ErrorUsuarios,
    _es_duplicado,
    _proteger,
    registrar_log,
)
from nucleo.tipos import MULTA_PAGADA, MULTA_PENDIENTE


class ErrorMultas(ErrorUsuarios):
    """Error funcional relacionado con las multas."""


class MultaYaExiste(ErrorMultas):
    """Ya existe una multa asociada al préstamo."""


class MultaNoPendiente(ErrorMultas):
    """La multa ya no está pendiente."""


class MultaNoEncontrada(ErrorMultas):
    """No existe la multa solicitada."""


class MultaInvalida(ErrorMultas):
    """Los valores de la multa no cumplen las restricciones."""


def _filas(respuesta: Any) -> list[dict[str, Any]]:
    datos = respuesta.data
    if datos is None:
        return []
    if isinstance(datos, dict):
        return [datos]
    return list(datos)


def _validar_entero(valor: Any, campo: str, minimo: int) -> None:
    if (
        isinstance(valor, bool)
        or not isinstance(valor, int)
        or valor < minimo
    ):
        raise MultaInvalida(
            f"{campo} debe ser un entero mayor o igual a {minimo}."
        )


def _validar_fecha(fecha_pago: date) -> None:
    if not isinstance(fecha_pago, date) or isinstance(fecha_pago, datetime):
        raise MultaInvalida("La fecha de pago debe ser una fecha válida.")


@_proteger
def crear_multa(
    prestamo_id: int,
    usuario_id: str,
    dias_retraso: int,
    valor_dia: int,
    monto: int,
) -> dict[str, Any]:
    """Crea una multa y traduce el índice único a un error funcional."""
    _validar_entero(dias_retraso, "Los días de retraso", 1)
    _validar_entero(valor_dia, "El valor diario", 0)
    _validar_entero(monto, "El monto", 0)
    datos = {
        "prestamo_id": prestamo_id,
        "usuario_id": usuario_id,
        "dias_retraso": dias_retraso,
        "valor_dia": valor_dia,
        "monto": monto,
        "estado": MULTA_PENDIENTE,
    }
    try:
        respuesta = (
            cliente_admin()
            .table("multas")
            .insert(datos)
            .select("*")
            .execute()
        )
    except Exception as error:
        if _es_duplicado(error):
            raise MultaYaExiste("Ya existe una multa para este préstamo.") from error
        raise

    multas = _filas(respuesta)
    if not multas:
        raise RuntimeError("La base de datos no devolvió la multa insertada.")
    multa = multas[0]
    registrar_log(
        None,
        "multa_creada",
        {
            "multa_id": multa.get("id"),
            "prestamo_id": prestamo_id,
            "usuario_id": usuario_id,
            "monto": monto,
        },
    )
    return multa


@_proteger
def obtener_multa(id: int) -> dict[str, Any] | None:
    """Obtiene una multa por su identificador."""
    respuesta = (
        cliente_admin()
        .table("multas")
        .select("*")
        .eq("id", id)
        .limit(1)
        .execute()
    )
    multas = _filas(respuesta)
    return multas[0] if multas else None


@_proteger
def listar_multas(
    usuario_id: str | None = None, estado: str | None = None
) -> list[dict[str, Any]]:
    """Lista multas con filtros opcionales por lector y estado."""
    consulta = cliente_admin().table("multas").select("*")
    if usuario_id is not None:
        consulta = consulta.eq("usuario_id", usuario_id)
    if estado is not None:
        consulta = consulta.eq("estado", estado)
    respuesta = consulta.order("fecha_generacion", desc=True).execute()
    return _filas(respuesta)


@_proteger
def tiene_multas_pendientes(usuario_id: str) -> int:
    """Devuelve el número exacto de multas pendientes del lector."""
    respuesta = (
        cliente_admin()
        .table("multas")
        .select("id", count="exact")
        .eq("usuario_id", usuario_id)
        .eq("estado", MULTA_PENDIENTE)
        .execute()
    )
    if respuesta.count is None:
        raise RuntimeError("La base de datos no devolvió el conteo de multas.")
    return respuesta.count


@_proteger
def marcar_pagada(
    multa_id: int, actor_id: str, fecha_pago: date
) -> dict[str, Any]:
    """Marca una multa pendiente como pagada en la fecha proporcionada."""
    _validar_fecha(fecha_pago)
    respuesta = (
        cliente_admin()
        .table("multas")
        .update(
            {"estado": MULTA_PAGADA, "fecha_pago": fecha_pago.isoformat()}
        )
        .eq("id", multa_id)
        .eq("estado", MULTA_PENDIENTE)
        .select("*")
        .execute()
    )
    multas = _filas(respuesta)
    if not multas:
        raise MultaNoPendiente("La multa no existe o ya fue pagada.")

    multa = multas[0]
    registrar_log(actor_id, "multa_pagada", {"multa_id": multa_id})
    return multa


@_proteger
def modificar_monto(
    multa_id: int, nuevo_monto: int, motivo: str, actor_id: str
) -> dict[str, Any]:
    """Modifica el monto de una multa pendiente y audita el motivo."""
    _validar_entero(nuevo_monto, "El monto", 0)
    if not isinstance(motivo, str) or not motivo.strip():
        raise MultaInvalida("El motivo de la modificación es obligatorio.")

    anterior = obtener_multa(multa_id)
    if anterior is None:
        raise MultaNoEncontrada("La multa no existe.")
    if anterior.get("estado") != MULTA_PENDIENTE:
        raise MultaNoPendiente("No se puede modificar una multa pagada.")

    respuesta = (
        cliente_admin()
        .table("multas")
        .update({"monto": nuevo_monto})
        .eq("id", multa_id)
        .eq("estado", MULTA_PENDIENTE)
        .select("*")
        .execute()
    )
    multas = _filas(respuesta)
    if not multas:
        raise MultaNoPendiente("La multa ya no está pendiente.")

    multa = multas[0]
    registrar_log(
        actor_id,
        "multa_monto_modificado",
        {
            "multa_id": multa_id,
            "monto_anterior": anterior["monto"],
            "monto_nuevo": nuevo_monto,
            "motivo": motivo.strip(),
        },
    )
    return multa