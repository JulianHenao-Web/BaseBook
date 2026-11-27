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