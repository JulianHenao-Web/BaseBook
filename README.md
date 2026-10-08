# sin nombre por el momento  - Sistema de Gestion de Biblioteca

 aplicacion para gestionar el prestamo y devolucion de libros en una biblioteca universitaria, con catalogo publico de consulta, control de multas y roles diferenciados para lectores y bibliotecarios.


Funciona **con o sin internet**: por aclarar

dividida en varios modulos funcionales

--Config(carpeta de configuracion para futuros ajustes en caso de querer conectarlo a alguna base )
---database.py(opcional)
---security.py(opcional)
--app(aqui todo lo que compone el programa )
-----front(Capa de presentacion)
-----business (Capa de negocio)
-----dates(Base de datos)
-----LOGS(Capa de logs y registro tota)

-main 
-requeriments.txt

## 1. Requisitos previos

- **Python 3.10 o superior** (con 3.10 y 3.13).
- **pip** (viene con Python).
- **Internet** 
instalacion de requeriments
--pip install -r requirements.txt

EStructura  deseada 
biblioteca/
├── main.py                      # arranque (Flask o consola)
├── nucleo/                     # SOLO funciones puras, sin imports de BD ni Flask
│   ├── tipos.py                # Libro, Prestamo, Reserva, Multa, Usuario (inmutables)
│   ├── reglas_catalogo.py      # filtrar_libros(), estado_resultante()
│   ├── reglas_prestamo.py      # puede_prestar(), crear_prestamo(), cerrar_prestamo()
│   ├── reglas_reserva.py       # puede_reservar(), siguiente_en_cola()
│   ├── reglas_multa.py         # dias_retraso(), calcular_multa()
│   └── permisos.py             # PERMISOS = {rol: {operaciones}}, rol_permite()
├── almacen/                    # funciones de entrada/salida a la BD
│   ├── conexion.py             # transaccion()
│   ├── libros.py  prestamos.py  reservas.py  multas.py  usuarios.py  parametros.py
├── interfaz/                   # rutas web o menús
├── pruebas/
│   ├── test_nucleo/          
└── datos/
