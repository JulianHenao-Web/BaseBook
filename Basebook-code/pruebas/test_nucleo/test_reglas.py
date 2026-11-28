import unittest
from datetime import date

from nucleo.autenticacion import usuario_de_sesion, validar_credenciales
from nucleo.permisos import puede_ver_recurso, tiene_permiso
from nucleo.reglas_catalogo import (
    esta_disponible,
    normalizar_isbn,
    validar_cambio_total,
    validar_libro,
)
from nucleo.reglas_multa import (
    calcular_dias_retraso,
    calcular_monto,
    estimar_multa,
    evaluar_multa,
    validar_modificacion,
)
from nucleo.reglas_prestamo import (
    calcular_fecha_limite,
    esta_vencido,
    evaluar_prestamo,
    puede_devolverse,
)
from nucleo.reglas_reserva import (
    evaluar_reserva,
    puede_cancelar,
    reserva_vencida,
    siguiente_en_cola,
)
from nucleo.reglas_usuario import (
    normalizar_correo,
    validar_cambio_estado,
    validar_cambio_rol,
    validar_registro,
)
from nucleo.tipos import Resultado


class PruebasReglasUsuario(unittest.TestCase):
    def test_registro_retorna_todos_los_errores_y_acepta_campos_opcionales(self):
        errores = validar_registro("", "correo-invalido", "corta", "otra", "12x", "")
        self.assertEqual(len(errores), 5)
        self.assertEqual(
            validar_registro(
                " Lector ", "lector@example.com", "clave-segura",
                "clave-segura", "", None,
            ),
            [],
        )

    def test_normaliza_correo(self):
        self.assertEqual(normalizar_correo("  Lector@Ejemplo.COM "), "lector@ejemplo.com")

    def test_cambio_de_rol_protege_al_ultimo_administrador(self):
        administrador = {
            "id": "admin-1",
            "rol": "administrador",
            "activo": True,
        }
        resultado = validar_cambio_rol(
            administrador, administrador, "lector", administradores_activos=1
        )
        self.assertFalse(resultado.permitido)
        self.assertIsInstance(resultado, Resultado)

    def test_cambio_de_estado_no_permite_autodesactivacion(self):
        administrador = {"id": "admin-1", "rol": "administrador", "activo": True}
        resultado = validar_cambio_estado(
            administrador, administrador, False, administradores_activos=2
        )
        self.assertFalse(resultado.permitido)


class PruebasAutenticacionYPermisos(unittest.TestCase):
    def test_credenciales_solo_validan_formato_y_mensaje_es_generico(self):
        correcto = validar_credenciales(" Lector@Ejemplo.com ", "x")
        incorrecto = validar_credenciales("correo-invalido", "x")
        self.assertTrue(correcto.permitido)
        self.assertEqual(correcto.datos["correo"], "lector@ejemplo.com")
        self.assertFalse(incorrecto.permitido)
        self.assertNotIn("correo", incorrecto.motivo.lower())
        self.assertNotIn("contraseña", incorrecto.motivo.lower())

    def test_sesion_devuelve_el_usuario_o_none(self):
        usuario = {"id": "lector-1"}
        self.assertEqual(usuario_de_sesion({"usuario": usuario}), usuario)
        self.assertIsNone(usuario_de_sesion({}))
        self.assertIsNone(usuario_de_sesion(None))

    def test_permisos_corresponden_a_roles_del_readme(self):
        self.assertTrue(tiene_permiso("lector", "prestamo.solicitar"))
        self.assertTrue(tiene_permiso("bibliotecario", "catalogo.gestionar"))
        self.assertTrue(tiene_permiso("administrador", "rol.cambiar"))
        self.assertTrue(tiene_permiso("lector", "multa.consultar_propias"))
        self.assertFalse(tiene_permiso("bibliotecario", "multa.consultar_propias"))
        self.assertFalse(tiene_permiso("administrador", "catalogo.gestionar"))
        self.assertFalse(tiene_permiso("rol-desconocido", "catalogo.consultar"))
        self.assertFalse(tiene_permiso("lector", "accion.desconocida"))

    def test_alcance_de_recurso(self):
        self.assertTrue(puede_ver_recurso("lector", "u1", "u1"))
        self.assertFalse(puede_ver_recurso("lector", "u1", "u2"))
        self.assertTrue(puede_ver_recurso("bibliotecario", "u1", "u2"))
        self.assertFalse(puede_ver_recurso("administrador", "u1", "u2"))


class PruebasReglasCatalogo(unittest.TestCase):
    def test_valida_libro_y_normaliza_isbn(self):
        self.assertEqual(normalizar_isbn(" 978-0 306-40615-7 "), "9780306406157")
        resultado = validar_libro(
            {"isbn": "0-306-40615-2", "titulo": "Libro", "anio": 2000,
             "total_ejemplares": 2}
        )
        self.assertTrue(resultado.permitido)
        self.assertEqual(resultado.datos["isbn"], "0306406152")

    def test_rechaza_total_menor_que_prestados_y_detecta_disponibilidad(self):
        self.assertFalse(validar_cambio_total(1, 2).permitido)
        self.assertTrue(validar_cambio_total(2, 2).permitido)
        self.assertTrue(
            esta_disponible({"estado": "activo", "ejemplares_disponibles": 1})
        )
        self.assertFalse(
            esta_disponible({"estado": "inactivo", "ejemplares_disponibles": 1})
        )


class PruebasReglasPrestamo(unittest.TestCase):
    def setUp(self):
        self.lector = {"activo": True}
        self.libro = {
            "isbn": "1234567890",
            "estado": "activo",
            "ejemplares_disponibles": 1,
        }
        self.hoy = date(2026, 1, 1)

    def test_evalua_orden_de_rechazo_y_devuelve_fechas(self):
        resultado = evaluar_prestamo(
            {"activo": False}, {"estado": "inactivo"}, 1, (), 7, self.hoy
        )
        self.assertIn("lector", resultado.motivo)
        resultado = evaluar_prestamo(
            self.lector,
            {"estado": "inactivo", "ejemplares_disponibles": 1},
            0,
            (),
            7,
            self.hoy,
        )
        self.assertIn("libro", resultado.motivo)
        resultado = evaluar_prestamo(
            self.lector,
            {**self.libro, "ejemplares_disponibles": 0},
            1,
            (),
            7,
            self.hoy,
        )
        self.assertEqual(resultado.motivo, "No hay ejemplares disponibles. Puedes reservar este libro.")
        resultado = evaluar_prestamo(
            self.lector, self.libro, 1, (), 7, self.hoy
        )
        self.assertIn("multas", resultado.motivo)

    def test_prestamo_exitoso_fechas_vencimiento_y_devolucion(self):
        resultado = evaluar_prestamo(
            self.lector, self.libro, 0, (), 7, self.hoy
        )
        self.assertTrue(resultado.permitido)
        self.assertEqual(resultado.datos["fecha_prestamo"], self.hoy)
        self.assertEqual(resultado.datos["fecha_limite"], date(2026, 1, 8))
        self.assertEqual(calcular_fecha_limite(self.hoy, 7), date(2026, 1, 8))
        self.assertFalse(esta_vencido(date(2026, 1, 8), date(2026, 1, 8)))
        self.assertTrue(esta_vencido(date(2026, 1, 8), date(2026, 1, 9)))
        self.assertTrue(puede_devolverse({"estado": "activo"}).permitido)
        self.assertFalse(puede_devolverse({"estado": "devuelto"}).permitido)

    def test_rechaza_multas_pendientes_y_el_mismo_libro_activo(self):
        self.assertIn(
            "multas",
            evaluar_prestamo(
                self.lector, self.libro, 1, (), 7, self.hoy
            ).motivo,
        )
        self.assertIn(
            "Ya tienes",
            evaluar_prestamo(
                self.lector,
                self.libro,
                0,
                [{"isbn": self.libro["isbn"], "estado": "activo"}],
                7,
                self.hoy,
            ).motivo,
        )


class PruebasReglasReserva(unittest.TestCase):
    def test_solo_reserva_sin_ejemplares_y_sin_otra_operacion_activa(self):
        lector = {"activo": True}
        libro = {"estado": "activo"}
        resultado = evaluar_reserva(lector, libro, 0, False, False)
        self.assertTrue(resultado.permitido)
        self.assertFalse(evaluar_reserva(lector, libro, 1, False, False).permitido)
        self.assertFalse(evaluar_reserva(lector, libro, 0, True, False).permitido)
        self.assertFalse(evaluar_reserva(lector, libro, 0, False, True).permitido)

    def test_siguiente_en_cola_ignora_reservas_no_esperando(self):
        primera = {"estado": "en_espera", "fecha_reserva": date(2026, 1, 2)}
        antigua = {"estado": "en_espera", "fecha_reserva": date(2026, 1, 1)}
        self.assertIs(
            siguiente_en_cola(
                [{"estado": "lista", "fecha_reserva": date(2025, 1, 1)},
                 primera, antigua]
            ),
            antigua,
        )
        self.assertIsNone(siguiente_en_cola([]))

    def test_cancelacion_solo_por_dueno_o_bibliotecario_y_reserva_vigente(self):
        reserva = {"estado": "lista", "usuario_id": "u1"}
        self.assertTrue(puede_cancelar(reserva, "u1", "lector").permitido)
        self.assertTrue(puede_cancelar(reserva, "u2", "bibliotecario").permitido)
        self.assertFalse(puede_cancelar(reserva, "u2", "lector").permitido)
        self.assertTrue(reserva_vencida(date(2026, 1, 1), date(2026, 1, 2)))
        self.assertFalse(reserva_vencida(date(2026, 1, 2), date(2026, 1, 2)))


class PruebasReglasMulta(unittest.TestCase):
    def test_calcula_dias_monto_y_evaluacion(self):
        limite = date(2026, 1, 1)
        devolucion = date(2026, 1, 4)
        self.assertEqual(calcular_dias_retraso(limite, limite), 0)
        self.assertEqual(calcular_dias_retraso(limite, devolucion), 3)
        self.assertEqual(calcular_monto(3, 1000), 3000)
        self.assertEqual(
            evaluar_multa(limite, devolucion, 1000).datos,
            {"dias_retraso": 3, "valor_dia": 1000, "monto": 3000},
        )
        self.assertIn(
            "No hay multa",
            evaluar_multa(limite, limite, 1000).motivo,
        )

    def test_estima_multa_y_valida_modificacion(self):
        estimada = estimar_multa(date(2026, 1, 1), date(2026, 1, 3), 500)
        self.assertEqual(estimada.datos["monto"], 1000)
        self.assertTrue(
            validar_modificacion(
                {"estado": "pendiente"}, 0, "Corrección justificada"
            ).permitido
        )
        self.assertFalse(
            validar_modificacion({"estado": "pagada"}, 100, "Ajuste").permitido
        )
        self.assertFalse(
            validar_modificacion({"estado": "pendiente"}, -1, "Ajuste").permitido
        )


if __name__ == "__main__":
    unittest.main()
