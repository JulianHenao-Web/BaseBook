import json
import unittest
from io import BytesIO
from unittest.mock import patch
from urllib.error import URLError
from urllib.parse import parse_qs, urlparse

from almacen.api_libros import (
    ErrorBusquedaOpenLibrary,
    LibroExterno,
    buscar_libros,
)


class PruebasApiLibros(unittest.TestCase):
    @patch("almacen.api_libros.urlopen")
    def test_busca_y_normaliza_campos_independientes(self, urlopen_mock):
        respuesta = {
            "docs": [
                {
                    "key": "/works/OL123W",
                    "title": "Libro de prueba",
                    "author_name": ["Autora Uno", "Autor Dos"],
                    "first_publish_year": 1999,
                    "publisher": ["Editorial"],
                    "isbn": ["1234567890"],
                    "language": ["spa"],
                    "edition_count": 3,
                    "cover_i": 456,
                }
            ]
        }
        urlopen_mock.return_value = BytesIO(json.dumps(respuesta).encode("utf-8"))

        libros = buscar_libros("  historia universal  ", limite=5)

        self.assertEqual(len(libros), 1)
        libro = libros[0]
        self.assertIsInstance(libro, LibroExterno)
        self.assertEqual(libro.titulo, "Libro de prueba")
        self.assertEqual(libro.autores, ("Autora Uno", "Autor Dos"))
        self.assertEqual(libro.anio_primera_publicacion, 1999)
        self.assertEqual(libro.editoriales, ("Editorial",))
        self.assertEqual(libro.isbn, ("1234567890",))
        self.assertEqual(libro.idiomas, ("spa",))
        self.assertEqual(libro.cantidad_ediciones, 3)
        self.assertEqual(
            libro.portada_url, "https://covers.openlibrary.org/b/id/456-M.jpg"
        )
        self.assertEqual(libro.url_openlibrary, "https://openlibrary.org/works/OL123W")

        url = urlopen_mock.call_args.args[0]
        parametros = parse_qs(urlparse(url).query)
        self.assertEqual(parametros["q"], ["historia universal"])
        self.assertEqual(parametros["limit"], ["5"])

    @patch("almacen.api_libros.urlopen")
    def test_campos_ausentes_se_representan_sin_inventar_datos(self, urlopen_mock):
        urlopen_mock.return_value = BytesIO(b'{"docs": [{"title": "Sin datos"}]}')

        libro = buscar_libros("sin datos")[0]

        self.assertEqual(libro.titulo, "Sin datos")
        self.assertEqual(libro.autores, ())
        self.assertIsNone(libro.anio_primera_publicacion)
        self.assertIsNone(libro.portada_url)
        self.assertIsNone(libro.url_openlibrary)

    def test_rechaza_consulta_vacia_y_limite_fuera_de_rango(self):
        with self.assertRaises(ValueError):
            buscar_libros("  ")
        with self.assertRaises(ValueError):
            buscar_libros("libros", limite=101)

    @patch("almacen.api_libros.urlopen", side_effect=URLError("sin conexión"))
    def test_expone_error_de_conexion(self, _urlopen_mock):
        with self.assertRaises(ErrorBusquedaOpenLibrary):
            buscar_libros("libros")


if __name__ == "__main__":
    unittest.main()
