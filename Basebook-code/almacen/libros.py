""" Gestion del catalogo de libros BaseBook."""

from almacen import api_libros
from almacen.conexion import cliente_admin
from almacen.usuarios import registrar_log, ErrorBaseDatos
from postgrest.exceptions import APIError

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

def _validar_ejemplares(cantidad):
    """Comprueba que la cantidad de ejemplares sea valida."""

    if (
        not isinstance(cantidad, int)
        or isinstance(cantidad,bool)
        or cantidad < 0
    ):
        raise EjemplaresInvalidos("La cantidad de ejemplares debe ser un entero no negativo")

def agregar_libro(datos, total_ejemplares, actor_id =None):
    """Registra un libro en el catalogo."""

    isbn = datos.get("isbn")

    if not isbn:
        raise ValueError("El libro debe tener un ISBN.")

    _validar_ejemplares(total_ejemplares)

    registro ={
        "isbn":isbn,
        "titulo": datos.get("titulo"),
        "autor": datos.get("autor"),
        "anio": datos.get("anio"),
        "portada": datos.get("portada"),
        "tema": datos.get("tema"),
        "total_ejemplares":total_ejemplares,
        "ejemplares_disponibles": total_ejemplares,
        "estado": "activo",
    }

    try: 
        respuesta =(
            cliente_admin()
            .table("libros")
            .insert(registro)
            .execute()
        )

    except APIError as error:
        if error.code =="23505":
            raise LibroYaRegistrado(
                "El libro ya está registrado."
            )from error

        raise ErrorBaseDatos(
            "No se puede registrar el libro."
        )from error

    if not respuesta.data:
        raise ErrorBaseDatos(
            "No se recibieron los datos del libro registrado."
        )

    registrar_log(actor_id, "agregar_libro",{"isbn":isbn})

    return respuesta.data[0]