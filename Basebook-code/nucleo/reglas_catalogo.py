"""Reglas puras para el catálogo de libros."""

from collections.abc import Mapping
from typing import Any

from nucleo.tipos import LIBRO_ACTIVO, Resultado


def normalizar_isbn(isbn: str) -> str:
    """Elimina guiones y espacios de un ISBN."""
    if not isinstance(isbn, str):
        return ""
    return "".join(caracter for caracter in isbn if caracter != "-" and not caracter.isspace())


def validar_libro(datos: Mapping[str, Any]) -> Resultado:
    """Valida los campos mínimos de un libro."""
    errores = []
    isbn = normalizar_isbn(datos.get("isbn", ""))
    if len(isbn) not in (10, 13) or not isbn.isdigit():
        errores.append("El ISBN debe tener 10 o 13 dígitos.")
    if not isinstance(datos.get("titulo"), str) or not datos["titulo"].strip():
        errores.append("El título es obligatorio.")

    anio = datos.get("anio")
    if (
        isinstance(anio, bool)
        or not isinstance(anio, int)
        or not 1450 <= anio <= 2100
    ):
        errores.append("El año debe ser un entero razonable.")

    total = datos.get("total_ejemplares")
    if isinstance(total, bool) or not isinstance(total, int) or total <= 0:
        errores.append("El total de ejemplares debe ser un entero mayor que cero.")

    if errores:
        return Resultado(False, " ".join(errores))
    return Resultado(True, datos={"isbn": isbn})


def validar_cambio_total(nuevo_total: int, prestados: int) -> Resultado:
    """Impide reducir el total de ejemplares por debajo de los prestados."""
    if (
        isinstance(nuevo_total, bool)
        or not isinstance(nuevo_total, int)
        or nuevo_total <= 0
    ):
        return Resultado(False, "El total de ejemplares debe ser un entero mayor que cero.")
    if isinstance(prestados, bool) or not isinstance(prestados, int) or prestados < 0:
        return Resultado(False, "La cantidad de ejemplares prestados no es válida.")
    if nuevo_total < prestados:
        return Resultado(
            False, "El total no puede ser menor que la cantidad de ejemplares prestados."
        )
    return Resultado(True, datos={"total_ejemplares": nuevo_total})


def esta_disponible(libro: Mapping[str, Any]) -> bool:
    """Indica si el libro está activo y tiene ejemplares disponibles."""
    disponibles = libro.get("ejemplares_disponibles", 0)
    return (
        libro.get("estado") == LIBRO_ACTIVO
        and isinstance(disponibles, int)
        and not isinstance(disponibles, bool)
        and disponibles > 0
    )