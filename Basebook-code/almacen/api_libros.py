"""Adaptador aislado para buscar metadatos de libros en Open Library."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen


_URL_BUSQUEDA = "https://openlibrary.org/search.json"
_CAMPOS_BUSQUEDA = (
    "key,title,author_name,first_publish_year,publisher,isbn,language,"
    "edition_count,cover_i"
)


class ErrorBusquedaOpenLibrary(Exception):
    """Error de conexión o respuesta al consultar Open Library."""


@dataclass(frozen=True)
class LibroExterno:
    """Metadatos normalizados de un libro encontrado en Open Library."""

    clave: str
    titulo: str
    autores: Tuple[str, ...]
    anio_primera_publicacion: Optional[int]
    editoriales: Tuple[str, ...]
    isbn: Tuple[str, ...]
    idiomas: Tuple[str, ...]
    cantidad_ediciones: Optional[int]
    portada_url: Optional[str]
    url_openlibrary: Optional[str]


def buscar_libros(
    consulta: str, limite: int = 10, timeout: float = 10
) -> Tuple[LibroExterno, ...]:
    """Busca libros por texto general y devuelve metadatos, sin guardarlos localmente.

    ``limite`` acepta valores entre 1 y 100. Los datos devueltos son de Open
    Library; disponibilidad, préstamos y ejemplares pertenecen al catálogo local.
    """
    if not isinstance(consulta, str) or not consulta.strip():
        raise ValueError("La consulta de búsqueda no puede estar vacía.")
    if (
        not isinstance(limite, int)
        or isinstance(limite, bool)
        or not 1 <= limite <= 100
    ):
        raise ValueError("El límite debe ser un entero entre 1 y 100.")
    if timeout <= 0:
        raise ValueError("El tiempo de espera debe ser mayor que cero.")

    parametros = urlencode(
        {
            "q": consulta.strip(),
            "limit": limite,
            "fields": _CAMPOS_BUSQUEDA,
        }
    )
    url = f"{_URL_BUSQUEDA}?{parametros}"

    try:
        with urlopen(url, timeout=timeout) as respuesta:
            datos = json.loads(respuesta.read().decode("utf-8"))
    except HTTPError as error:
        raise ErrorBusquedaOpenLibrary(
            f"Open Library respondió con HTTP {error.code}."
        ) from error
    except (URLError, TimeoutError) as error:
        raise ErrorBusquedaOpenLibrary(
            f"No se pudo conectar con Open Library: {error}."
        ) from error
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ErrorBusquedaOpenLibrary(
            "Open Library devolvió una respuesta que no se pudo leer."
        ) from error

    if not isinstance(datos, dict) or not isinstance(datos.get("docs"), list):
        raise ErrorBusquedaOpenLibrary(
            "Open Library devolvió una respuesta con formato inesperado."
        )

    return tuple(
        _normalizar_libro(documento)
        for documento in datos["docs"]
        if isinstance(documento, dict)
    )


def _normalizar_libro(documento: dict[str, Any]) -> LibroExterno:
    clave = _texto(documento.get("key")) or ""
    portada_id = documento.get("cover_i")
    portada_url = (
        f"https://covers.openlibrary.org/b/id/{portada_id}-M.jpg"
        if isinstance(portada_id, int) and not isinstance(portada_id, bool)
        else None
    )

    return LibroExterno(
        clave=clave,
        titulo=_texto(documento.get("title")) or "Título no disponible",
        autores=_textos(documento.get("author_name")),
        anio_primera_publicacion=_entero(documento.get("first_publish_year")),
        editoriales=_textos(documento.get("publisher")),
        isbn=_textos(documento.get("isbn")),
        idiomas=_textos(documento.get("language")),
        cantidad_ediciones=_entero(documento.get("edition_count")),
        portada_url=portada_url,
        url_openlibrary=f"https://openlibrary.org{clave}" if clave else None,
    )


def _texto(valor: Any) -> Optional[str]:
    if isinstance(valor, str) and valor.strip():
        return valor.strip()
    return None


def _textos(valor: Any) -> Tuple[str, ...]:
    if not isinstance(valor, list):
        return ()
    resultado = []
    for elemento in valor:
        texto = _texto(elemento)
        if texto:
            resultado.append(texto)
    return tuple(resultado)


def _entero(valor: Any) -> Optional[int]:
    if isinstance(valor, int) and not isinstance(valor, bool):
        return valor
    return None