import unittest
from unittest.mock import patch
from postgrest.exceptions import APIError

from almacen.libros import agregar_libro, LibroYaRegistrado


class TestLibros(unittest.TestCase):

    @patch("almacen.libros.registrar_log")
    @patch("almacen.libros.cliente_admin")
    def test_agregar_libro(self, cliente_mock, log_mock):

        datos = {
            "isbn": "9780156012195",
            "titulo": "El principito"
        }

        cliente = cliente_mock.return_value

        cliente.table.return_value.insert.return_value.execute.return_value.data = [
            {**datos, "total_ejemplares": 5, "ejemplares_disponibles": 5}
        ]

        resultado = agregar_libro(datos, 5)

        self.assertEqual(resultado["total_ejemplares"], 5)
        self.assertEqual(resultado["ejemplares_disponibles"], 5)

        log_mock.assert_called_once()

    @patch("almacen.libros.registrar_log")
    @patch("almacen.libros.cliente_admin")
    def test_libro_duplicado(self, cliente_mock, log_mock):

        datos = {
            "isbn": "9780156012195",
            "titulo": "El principito"
        }

        cliente = cliente_mock.return_value

        cliente.table.return_value.insert.return_value.execute.side_effect = APIError({
            "code": "23505",
            "message": "ISBN duplicado"
        })

        with self.assertRaises(LibroYaRegistrado):
            agregar_libro(datos, 5)

        log_mock.assert_not_called()