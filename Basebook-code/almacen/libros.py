""" Gestion del catalogo de libros BaseBook."""

class LibroYaRegistrado(Exception):
    """El libro ya existe en el catalogo."""

class LibroNoEncontrado(Exception):
    """El libro no existe en el catalogo."""

class EjemplaresInvalidos(Exception):
    """La cantidad de ejemplares no es valida."""

class SinEjemplaresDisponibles(Exception):
    """No hay ejemplares disponibles para prestar."""