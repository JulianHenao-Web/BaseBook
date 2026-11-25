import unittest
from unittest.mock import patch

import main
from almacen.api_libros import LibroExterno


class PruebasInterfazWeb(unittest.TestCase):
    def setUp(self):
        main.app.config.update(TESTING=True, SECRET_KEY="clave-de-prueba")
        self.cliente = main.app.test_client()

    def _token_csrf(self, ruta):
        self.cliente.get(ruta)
        with self.cliente.session_transaction() as sesion:
            return sesion["_csrf_token"]

    def test_paginas_principales_y_estilos_cargan(self):
        for ruta in ("/", "/login", "/registro", "/static/styles.css"):
            with self.subTest(ruta=ruta):
                respuesta = self.cliente.get(ruta)
                try:
                    self.assertEqual(respuesta.status_code, 200)
                finally:
                    respuesta.close()

    def test_login_sigue_mostrando_la_interfaz_si_falta_supabase(self):
        token = self._token_csrf("/login")

        respuesta = self.cliente.post(
            "/login",
            data={
                "csrf_token": token,
                "correo": "lector@example.com",
                "contrasena": "contrasena-segura",
            },
        )

        self.assertEqual(respuesta.status_code, 503)
        self.assertIn(b"Este servicio no est", respuesta.data)

    def test_login_crea_sesion_sin_guardar_credenciales(self):
        token = self._token_csrf("/login")
        usuario = {
            "id": "usuario-1",
            "nombre": "Lector",
            "apellido": "Prueba",
            "rol": "lector",
            "sesion": {"access_token": "secreto"},
        }

        with patch("main._operar_usuarios", return_value=usuario):
            respuesta = self.cliente.post(
                "/login",
                data={
                    "csrf_token": token,
                    "correo": "lector@example.com",
                    "contrasena": "contrasena-segura",
                },
            )

        self.assertEqual(respuesta.status_code, 302)
        with self.cliente.session_transaction() as sesion:
            self.assertEqual(sesion["usuario"]["id"], "usuario-1")
            self.assertNotIn("sesion", sesion["usuario"])
            self.assertNotIn("contrasena", sesion)

    def test_catalogo_sigue_cargando_si_falta_la_api(self):
        with patch(
            "main.importlib.import_module",
            side_effect=ModuleNotFoundError("almacen.api_libros"),
        ):
            respuesta = self.cliente.get("/?q=libro")

        self.assertEqual(respuesta.status_code, 200)
        self.assertIn(b"Este servicio no est", respuesta.data)

    def test_registro_valida_contrasena_antes_de_acceder_al_servicio(self):
        token = self._token_csrf("/registro")

        respuesta = self.cliente.post(
            "/registro",
            data={
                "csrf_token": token,
                "nombre": "Lector",
                "correo": "lector@example.com",
                "contrasena": "corta",
                "confirmar_contrasena": "corta",
            },
        )

        self.assertEqual(respuesta.status_code, 400)
        self.assertIn(b"al menos 8 caracteres", respuesta.data)

    def test_registro_envia_datos_al_modulo_de_usuarios(self):
        token = self._token_csrf("/registro")

        with patch("main._operar_usuarios") as operar_mock:
            respuesta = self.cliente.post(
                "/registro",
                data={
                    "csrf_token": token,
                    "nombre": "Lector",
                    "apellido": "Prueba",
                    "correo": "lector@example.com",
                    "documento": "12345",
                    "telefono": "",
                    "contrasena": "contrasena-segura",
                    "confirmar_contrasena": "contrasena-segura",
                },
            )

        self.assertEqual(respuesta.status_code, 302)
        operar_mock.assert_called_once_with(
            "registrar_usuario",
            error_http=400,
            correo="lector@example.com",
            contrasena="contrasena-segura",
            nombre="Lector",
            apellido="Prueba",
            documento="12345",
            telefono=None,
        )

    @patch("main._buscar_libros")
    def test_muestra_datos_del_catalogo(self, buscar_mock):
        buscar_mock.return_value = (
            LibroExterno(
                clave="/works/OL1W",
                titulo="Libro de ejemplo",
                autores=("Autora de prueba",),
                anio_primera_publicacion=2020,
                editoriales=("Editorial",),
                isbn=("1234567890",),
                idiomas=("spa",),
                cantidad_ediciones=2,
                portada_url=None,
                url_openlibrary="https://openlibrary.org/works/OL1W",
            ),
        )

        respuesta = self.cliente.get("/?q=ejemplo")

        self.assertEqual(respuesta.status_code, 200)
        self.assertIn(b"Libro de ejemplo", respuesta.data)
        self.assertIn(b"Autora de prueba", respuesta.data)


if __name__ == "__main__":
    unittest.main()
