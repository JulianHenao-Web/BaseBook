"""Acceso a datos de préstamos y actualización de ejemplares."""

import logging
from datetime import date, datetime
from typing import Any

from almacen.conexion import cliente_admin
from almacen.usuarios import ErrorUsuarios, _proteger, registrar_log
from nucleo.tipos import PRESTAMO_ACTIVO, PRESTAMO_DEVUELTO


logger = logging.getLogger(__name__)


class ErrorPrestamos(ErrorUsuarios):
    """Error funcional relacionado con los préstamos."""


class SinEjemplaresDisponibles(ErrorPrestamos):
    """El libro no tiene ejemplares que se puedan prestar."""


class PrestamoYaDevuelto(ErrorPrestamos):
    """El préstamo no estaba activo al intentar devolverlo."""


def _filas(respuesta: Any) -> list[dict[str, Any]]:
    datos = respuesta.data
    if datos is None:
        return []
    if isinstance(datos, dict):
        return [datos]
    return list(datos)


def _actualizar_ejemplar(funcion: str, isbn: str) -> list[dict[str, Any]]:
    respuesta = cliente_admin().rpc(
        funcion, {"p_isbn": isbn}
    ).execute()
    return _filas(respuesta)


def _validar_fecha(valor: date, campo: str) -> None:
    if not isinstance(valor, date) or isinstance(valor, datetime):
        raise ErrorPrestamos(f"{campo} debe ser una fecha válida.")


@_proteger
def crear_prestamo(
    usuario_id: str,
    isbn: str,
    fecha_prestamo: date,
    fecha_limite: date,
    registrado_por: str | None,
) -> dict[str, Any]:
    """Descuenta un ejemplar y registra el préstamo, compensando si falla."""
    _validar_fecha(fecha_prestamo, "La fecha del préstamo")
    _validar_fecha(fecha_limite, "La fecha límite")

    if not _actualizar_ejemplar("descontar_ejemplar", isbn):
        raise SinEjemplaresDisponibles(
            "No hay ejemplares disponibles para prestar este libro."
        )

    datos = {
        "usuario_id": usuario_id,
        "isbn": isbn,
        "fecha_prestamo": fecha_prestamo.isoformat(),
        "fecha_limite": fecha_limite.isoformat(),
        "estado": PRESTAMO_ACTIVO,
        "registrado_por": registrado_por,
    }

    try:
        respuesta = (
            cliente_admin()
            .table("prestamos")
            .insert(datos)
            .select("*")
            .execute()
        )
        prestamos = _filas(respuesta)
        if not prestamos:
            raise RuntimeError("La base de datos no devolvió el préstamo insertado.")
    except Exception:
        try:
            if not _actualizar_ejemplar("devolver_ejemplar", isbn):
                raise RuntimeError(
                    "La base de datos no pudo restablecer el ejemplar descontado."
                )
        except Exception as compensacion_error:
            logger.exception(
                "Falló la compensación de ejemplar para el ISBN %s", isbn
            )
            raise RuntimeError(
                "No se pudo registrar el préstamo ni restablecer el ejemplar."
            ) from compensacion_error
        raise

    prestamo = prestamos[0]
    registrar_log(
        registrado_por,
        "prestamo_creado",
        {"prestamo_id": prestamo.get("id"), "usuario_id": usuario_id, "isbn": isbn},
    )
    return prestamo


@_proteger
def obtener_prestamo(id: int) -> dict[str, Any] | None:
    """Obtiene un préstamo por su identificador."""
    respuesta = (
        cliente_admin()
        .table("prestamos")
        .select("*")
        .eq("id", id)
        .limit(1)
        .execute()
    )
    prestamos = _filas(respuesta)
    return prestamos[0] if prestamos else None


@_proteger
def listar_prestamos(
    usuario_id: str | None = None, estado: str | None = None
) -> list[dict[str, Any]]:
    """Lista préstamos con filtros opcionales por lector y estado."""
    consulta = cliente_admin().table("prestamos").select("*")
    if usuario_id is not None:
        consulta = consulta.eq("usuario_id", usuario_id)
    if estado is not None:
        consulta = consulta.eq("estado", estado)
    respuesta = consulta.order("fecha_prestamo", desc=True).execute()
    return _filas(respuesta)


def listar_prestamos_activos(usuario_id: str) -> list[dict[str, Any]]:
    """Lista los préstamos activos de un lector para evaluar una solicitud."""
    return listar_prestamos(usuario_id=usuario_id, estado=PRESTAMO_ACTIVO)


@_proteger
def marcar_devuelto(
    prestamo_id: int, fecha_devolucion: date, actor_id: str
) -> dict[str, Any]:
    """Marca como devuelto únicamente un préstamo que aún esté activo."""
    _validar_fecha(fecha_devolucion, "La fecha de devolución")
    respuesta = (
        cliente_admin()
        .table("prestamos")
        .update(
            {
                "estado": PRESTAMO_DEVUELTO,
                "fecha_devolucion": fecha_devolucion.isoformat(),
            }
        )
        .eq("id", prestamo_id)
        .eq("estado", PRESTAMO_ACTIVO)
        .select("*")
        .execute()
    )
    prestamos = _filas(respuesta)
    if not prestamos:
        raise PrestamoYaDevuelto("El préstamo ya fue devuelto o no existe.")

    prestamo = prestamos[0]
    isbn = prestamo["isbn"]
    if not _actualizar_ejemplar("devolver_ejemplar", isbn):
        raise RuntimeError(
            "No se pudo devolver el ejemplar asociado al préstamo."
        )

    registrar_log(
        actor_id,
        "prestamo_devuelto",
        {"prestamo_id": prestamo_id, "isbn": isbn},
    )
    return prestamo