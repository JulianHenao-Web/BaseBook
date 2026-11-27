""" Gestion del catalogo de libros BaseBook."""

from almacen import api_libros

class LibroYaRegistrado(Exception):
    """El libro ya existe en el catalogo."""

class LibroNoEncontrado(Exception):
    """El libro no existe en el catalogo."""

class EjemplaresInvalidos(Exception):
    """La cantidad de ejemplares no es valida."""

class SinEjemplaresDisponibles(Exception):
    """No hay ejemplares disponibles para prestar."""

def buscar_en_api(consulta:str, limite: int = 10):
    """Busca informacion bibliografica en Open Library."""
    return api_libros.buscar_libros(consulta, limite)

def _seleccionar_isbn(isbns):
    """Seleccionar un ISBN de 13 digitos."""
    for isbn in isbns:
        if len(isbn) == 13 and isbn.isdigit():
            return isbn
    return None

def a_datos_catalogo(libro: api_libros.LibroExterno) -> dict:
    """Transforma los datos externos al formato del catalogo."""
    return {
        "isbn":_seleccionar_isbn(libro.isbn),
        "titulo":libro.titulo,
        "autor":", ".join(libro.autores) or None,
        "anio":libro.anio_primera_publicacion,
        "portada":libro.portada_url,
        "tema": None,
    }