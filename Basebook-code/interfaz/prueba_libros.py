"""Interfaz de consola para probar las búsquedas de Open Library."""

import sys
from pathlib import Path


_RAIZ_PROYECTO = Path(__file__).resolve().parents[1]
if str(_RAIZ_PROYECTO) not in sys.path:
    sys.path.insert(0, str(_RAIZ_PROYECTO))

from almacen.api_libros import ErrorBusquedaOpenLibrary, LibroExterno, buscar_libros


def _mostrar_libro(numero: int, libro: LibroExterno) -> None:
    anio = (
        str(libro.anio_primera_publicacion)
        if libro.anio_primera_publicacion is not None
        else "No disponible"
    )
    ediciones = (
        str(libro.cantidad_ediciones)
        if libro.cantidad_ediciones is not None
        else "No disponible"
    )
    print(f"\n{numero}. {libro.titulo}")
    print(f"   Autores: {', '.join(libro.autores) or 'No disponibles'}")
    print(f"   Primera publicación: {anio}")
    print(f"   Editoriales: {', '.join(libro.editoriales) or 'No disponibles'}")
    print(f"   ISBN: {', '.join(libro.isbn) or 'No disponible'}")
    print(f"   Idiomas: {', '.join(libro.idiomas) or 'No disponibles'}")
    print(f"   Cantidad de ediciones: {ediciones}")
    print(f"   Portada: {libro.portada_url or 'No disponible'}")
    print(f"   Open Library: {libro.url_openlibrary or 'No disponible'}")


def main() -> None:
    print("Buscador de libros de Open Library (máximo 5 resultados)")
    print("Escribe 'salir' para terminar.\n")

    while True:
        consulta = input("Buscar libros: ").strip()
        if consulta.lower() in {"salir", "exit"}:
            print("Fin de la búsqueda.")
            return
        if not consulta:
            print("Escribe un título, autor o tema para buscar.\n")
            continue

        try:
            libros = buscar_libros(consulta, limite=5)
        except (ErrorBusquedaOpenLibrary, ValueError) as error:
            print(f"No se pudo completar la búsqueda: {error}\n")
            continue

        if not libros:
            print("No se encontraron libros.\n")
            continue

        for numero, libro in enumerate(libros, start=1):
            _mostrar_libro(numero, libro)
        print()


if __name__ == "__main__":
    main()