"""
almacen/parametros.py

Capa de datos para consultar y actualizar los parametros
configurables del sistema BaseBook.
"""

import logging

from almacen.conexion import cliente_admin
from almacen.usuarios import (
    _proteger,
    registrar_log,
    ErrorUsuarios,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------
# Errores propios
# ---------------------------------------------------------------------


class ParametroNoEncontrado(ErrorUsuarios):
    """El parametro solicitado no existe en la base de datos."""


class ParametroInvalido(ErrorUsuarios):
    """El valor proporcionado no es un entero valido."""


# ---------------------------------------------------------------------
# Conversion de valores
# ---------------------------------------------------------------------

def _convertir_entero(valor):
    """Convierte un valor a entero sin aceptar valores decimales."""

    if isinstance(valor, bool):
        raise ParametroInvalido("El valor debe ser un numero entero.")

    try:
        resultado = int(valor)
    except (TypeError, ValueError, OverflowError):
        raise ParametroInvalido(
            "El valor del parametro debe ser un numero entero."
        )

    if isinstance(valor, float) and not valor.is_integer():
        raise ParametroInvalido(
            "El valor del parametro no puede tener decimales."
        )

    return resultado


# ---------------------------------------------------------------------
# Consultar un parametro
# ---------------------------------------------------------------------

@_proteger
def obtener_parametro(clave):
    """
    Busca un parametro por su clave y devuelve su valor como entero.

    Si no existe, lanza ParametroNoEncontrado.
    """

    respuesta = (
        cliente_admin()
        .table("parametros")
        .select("clave, valor")
        .eq("clave", clave)
        .limit(1)
        .execute()
    )

    if not respuesta.data:
        raise ParametroNoEncontrado(
            f"No existe el parametro '{clave}'."
        )

    return _convertir_entero(respuesta.data[0]["valor"])


# ---------------------------------------------------------------------
# Consultar todos los parametros
# ---------------------------------------------------------------------

@_proteger
def obtener_parametros():
    """
    Devuelve todos los parametros en un diccionario.

    Ejemplo:
    {
        "dias_prestamo": 7,
        "valor_multa_dia": 1000
    }
    """

    respuesta = (
        cliente_admin()
        .table("parametros")
        .select("clave, valor")
        .execute()
    )

    parametros = {}

    for fila in respuesta.data:
        parametros[fila["clave"]] = _convertir_entero(
            fila["valor"]
        )

    return parametros


# ---------------------------------------------------------------------
# Actualizar un parametro
# ---------------------------------------------------------------------

@_proteger
def actualizar_parametro(clave, valor, actor_id):
    """
    Actualiza el valor de un parametro existente.

    Registra el valor anterior y el nuevo en la auditoria.
    Devuelve el registro actualizado.
    """

    nuevo_valor = _convertir_entero(valor)

    # Consultar el valor anterior.
    respuesta_anterior = (
        cliente_admin()
        .table("parametros")
        .select("*")
        .eq("clave", clave)
        .limit(1)
        .execute()
    )

    if not respuesta_anterior.data:
        raise ParametroNoEncontrado(
            f"No existe el parametro '{clave}'."
        )

    anterior = respuesta_anterior.data[0]
    valor_anterior = _convertir_entero(anterior["valor"])

    # Actualizar el parametro.
    respuesta = (
        cliente_admin()
        .table("parametros")
        .update({
            "valor": nuevo_valor,
            "actualizado_por": actor_id,
        })
        .eq("clave", clave)
        .select("*")
        .execute()
    )

    if not respuesta.data:
        raise ParametroNoEncontrado(
            f"No se pudo actualizar el parametro '{clave}'."
        )

    actualizado = respuesta.data[0]

    # Registrar el cambio en la auditoria.
    registrar_log(
        actor_id,
        "parametro_cambiado",
        {
            "clave": clave,
            "valor_anterior": valor_anterior,
            "valor_nuevo": nuevo_valor,
        },
    )

    return actualizado
