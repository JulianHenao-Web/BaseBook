import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock, patch

from almacen.usuarios import ErrorBaseDatos
from almacen import multas, prestamos


def _respuesta(data=None, count=None):
    return SimpleNamespace(data=data, count=count)


class PruebasAlmacenPrestamos(unittest.TestCase):
    @patch("almacen.prestamos.cliente_admin")
    def test_obtener_prestamo_devuelve_none_si_no_existe(self, cliente_admin):
        cliente = Mock()
        (
            cliente.table.return_value.select.return_value.eq.return_value
            .limit.return_value.execute.return_value
        ) = _respuesta([])
        cliente_admin.return_value = cliente

        self.assertIsNone(prestamos.obtener_prestamo(999))

    @patch("almacen.prestamos.registrar_log")
    @patch("almacen.prestamos.cliente_admin")
    def test_crear_prestamo_descontando_ejemplar_y_registrando(self, cliente_admin, log):
        cliente = Mock()
        cliente.rpc.return_value.execute.return_value = _respuesta([{"isbn": "123"}])
        prestamo = {"id": 8, "usuario_id": "u1", "isbn": "123"}
        (
            cliente.table.return_value.insert.return_value.select.return_value
            .execute.return_value
        ) = _respuesta([prestamo])
        cliente_admin.return_value = cliente

        resultado = prestamos.crear_prestamo(
            "u1", "123", date(2026, 1, 1), date(2026, 1, 8), "b1"
        )

        self.assertEqual(resultado, prestamo)
        self.assertEqual(cliente.rpc.call_args.args[0], "descontar_ejemplar")
        log.assert_called_once_with(
            "b1",
            "prestamo_creado",
            {"prestamo_id": 8, "usuario_id": "u1", "isbn": "123"},
        )

    @patch("almacen.prestamos.cliente_admin")
    def test_sin_ejemplares_no_intenta_insertar(self, cliente_admin):
        cliente = Mock()
        cliente.rpc.return_value.execute.return_value = _respuesta([])
        cliente_admin.return_value = cliente

        with self.assertRaises(prestamos.SinEjemplaresDisponibles):
            prestamos.crear_prestamo(
                "u1", "123", date(2026, 1, 1), date(2026, 1, 8), "b1"
            )

        cliente.table.assert_not_called()

    @patch("almacen.prestamos.cliente_admin")
    def test_fallo_de_insert_compensa_el_desconto(self, cliente_admin):
        cliente = Mock()
        descontar = Mock()
        descontar.execute.return_value = _respuesta([{"isbn": "123"}])
        devolver = Mock()
        devolver.execute.return_value = _respuesta([{"isbn": "123"}])
        cliente.rpc.side_effect = [descontar, devolver]
        (
            cliente.table.return_value.insert.return_value.select.return_value
            .execute.side_effect
        ) = RuntimeError("insert fallido")
        cliente_admin.return_value = cliente

        with self.assertRaises(ErrorBaseDatos):
            prestamos.crear_prestamo(
                "u1", "123", date(2026, 1, 1), date(2026, 1, 8), "b1"
            )

        self.assertEqual(
            [llamada.args[0] for llamada in cliente.rpc.call_args_list],
            ["descontar_ejemplar", "devolver_ejemplar"],
        )

    @patch("almacen.prestamos.registrar_log")
    @patch("almacen.prestamos.cliente_admin")
    def test_marcar_devuelto_actualiza_estado_devuelve_ejemplar_y_audita(
        self, cliente_admin, log
    ):
        cliente = Mock()
        prestamo = {"id": 8, "isbn": "123", "estado": "devuelto"}
        (
            cliente.table.return_value.update.return_value.eq.return_value.eq
            .return_value.select.return_value.execute.return_value
        ) = _respuesta([prestamo])
        cliente.rpc.return_value.execute.return_value = _respuesta([{"isbn": "123"}])
        cliente_admin.return_value = cliente

        resultado = prestamos.marcar_devuelto(8, date(2026, 1, 9), "b1")

        self.assertEqual(resultado, prestamo)
        cliente.rpc.assert_called_once_with(
            "devolver_ejemplar", {"p_isbn": "123"}
        )
        log.assert_called_once_with(
            "b1", "prestamo_devuelto", {"prestamo_id": 8, "isbn": "123"}
        )

    @patch("almacen.prestamos.cliente_admin")
    def test_marcar_devuelto_rechaza_un_prestamo_ya_cerrado(self, cliente_admin):
        cliente = Mock()
        (
            cliente.table.return_value.update.return_value.eq.return_value.eq
            .return_value.select.return_value.execute.return_value
        ) = _respuesta([])
        cliente_admin.return_value = cliente

        with self.assertRaises(prestamos.PrestamoYaDevuelto):
            prestamos.marcar_devuelto(8, date(2026, 1, 9), "b1")

        cliente.rpc.assert_not_called()

    @patch("almacen.prestamos.cliente_admin")
    def test_listar_prestamos_activos_filtra_por_usuario_y_estado(
        self, cliente_admin
    ):
        cliente = Mock()
        table = cliente.table.return_value
        (
            table.select.return_value.eq.return_value.eq.return_value
            .order.return_value.execute.return_value
        ) = _respuesta([{"id": 8, "estado": "activo"}])
        cliente_admin.return_value = cliente

        resultado = prestamos.listar_prestamos_activos("u1")

        self.assertEqual(resultado, [{"id": 8, "estado": "activo"}])
        table.select.return_value.eq.assert_any_call("usuario_id", "u1")
        table.select.return_value.eq.return_value.eq.assert_called_once_with(
            "estado", "activo"
        )


class PruebasAlmacenMultas(unittest.TestCase):
    @patch("almacen.multas.cliente_admin")
    def test_obtener_multa_devuelve_none_si_no_existe(self, cliente_admin):
        cliente = Mock()
        (
            cliente.table.return_value.select.return_value.eq.return_value
            .limit.return_value.execute.return_value
        ) = _respuesta([])
        cliente_admin.return_value = cliente

        self.assertIsNone(multas.obtener_multa(999))

    @patch("almacen.multas.registrar_log")
    @patch("almacen.multas.cliente_admin")
    def test_crear_multa_guarda_valores_y_audita(self, cliente_admin, log):
        cliente = Mock()
        multa = {"id": 3, "prestamo_id": 8, "monto": 2000}
        (
            cliente.table.return_value.insert.return_value.select.return_value
            .execute.return_value
        ) = _respuesta([multa])
        cliente_admin.return_value = cliente

        resultado = multas.crear_multa(8, "u1", 2, 1000, 2000)

        self.assertEqual(resultado, multa)
        datos = cliente.table.return_value.insert.call_args.args[0]
        self.assertEqual(datos["valor_dia"], 1000)
        self.assertEqual(datos["estado"], "pendiente")
        log.assert_called_once_with(
            None,
            "multa_creada",
            {
                "multa_id": 3,
                "prestamo_id": 8,
                "usuario_id": "u1",
                "monto": 2000,
            },
        )

    @patch("almacen.multas.cliente_admin")
    def test_crear_multa_traduce_violacion_de_unicidad(self, cliente_admin):
        cliente = Mock()
        error = RuntimeError("duplicate key")
        error.code = "23505"
        (
            cliente.table.return_value.insert.return_value.select.return_value
            .execute.side_effect
        ) = error
        cliente_admin.return_value = cliente

        with self.assertRaises(multas.MultaYaExiste):
            multas.crear_multa(8, "u1", 2, 1000, 2000)

    @patch("almacen.multas.cliente_admin")
    def test_tiene_multas_pendientes_devuelve_conteo_exacto(self, cliente_admin):
        cliente = Mock()
        table = cliente.table.return_value
        (
            table.select.return_value.eq.return_value.eq.return_value
            .execute.return_value
        ) = _respuesta([], count=2)
        cliente_admin.return_value = cliente

        self.assertEqual(multas.tiene_multas_pendientes("u1"), 2)
        table.select.assert_called_once_with("id", count="exact")
        table.select.return_value.eq.return_value.eq.assert_called_once_with(
            "estado", "pendiente"
        )

    @patch("almacen.multas.registrar_log")
    @patch("almacen.multas.cliente_admin")
    def test_marcar_pagada_guarda_fecha_recibida_y_audita(self, cliente_admin, log):
        cliente = Mock()
        multa = {"id": 3, "estado": "pagada", "fecha_pago": "2026-01-10"}
        (
            cliente.table.return_value.update.return_value.eq.return_value.eq
            .return_value.select.return_value.execute.return_value
        ) = _respuesta([multa])
        cliente_admin.return_value = cliente

        resultado = multas.marcar_pagada(3, "b1", date(2026, 1, 10))

        self.assertEqual(resultado, multa)
        datos = cliente.table.return_value.update.call_args.args[0]
        self.assertEqual(datos["fecha_pago"], "2026-01-10")
        log.assert_called_once_with("b1", "multa_pagada", {"multa_id": 3})

    @patch("almacen.multas.registrar_log")
    @patch("almacen.multas.cliente_admin")
    def test_modificar_monto_guarda_motivo_en_log(self, cliente_admin, log):
        cliente = Mock()
        lectura = Mock()
        lectura.select.return_value.eq.return_value.limit.return_value.execute.return_value = (
            _respuesta([{"id": 3, "estado": "pendiente", "monto": 2000}])
        )
        escritura = Mock()
        (
            escritura.update.return_value.eq.return_value.eq.return_value
            .select.return_value.execute.return_value
        ) = _respuesta([{"id": 3, "estado": "pendiente", "monto": 1500}])
        cliente.table.side_effect = [lectura, escritura]
        cliente_admin.return_value = cliente

        resultado = multas.modificar_monto(3, 1500, "Ajuste autorizado", "b1")

        self.assertEqual(resultado["monto"], 1500)
        log.assert_called_once_with(
            "b1",
            "multa_monto_modificado",
            {
                "multa_id": 3,
                "monto_anterior": 2000,
                "monto_nuevo": 1500,
                "motivo": "Ajuste autorizado",
            },
        )


if __name__ == "__main__":
    unittest.main()
