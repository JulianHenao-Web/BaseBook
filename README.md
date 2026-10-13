# BaseBook — Sistema de Gestión de Biblioteca

Aplicación web para gestionar el préstamo y la devolución de libros en una biblioteca universitaria, con catálogo de consulta, reservas, control de multas y roles diferenciados para lectores, bibliotecarios y administradores.

> **Proyecto Integrador — Entornos de Desarrollo de Software**
> Universidad Tecnológica de Pereira · Facultad de Ingenierías · Tecnología en Desarrollo de Software
> Docente: Juan Camilo Olarte Betancourt

## Estado del proyecto

**Primera entrega: análisis, modelado y organización del proyecto.** El repositorio contiene la estructura inicial del sistema: las carpetas y los archivos de cada módulo. Los archivos de código están creados pero todavía sin implementar; el prototipo se desarrollará en la entrega final.

## Problema que resuelve

Cuando la administración de una biblioteca se hace de forma manual, aparecen errores en el registro de usuarios, en el control de préstamos y devoluciones, y no hay certeza de si un libro está realmente disponible. BaseBook centraliza esa información en un solo sistema, evita que dos personas vean un mismo libro como disponible y automatiza el cálculo de multas.

## Usuarios y roles

| Rol | Qué hace en el sistema |
|---|---|
| **Lector** | Se registra, consulta el catálogo y la disponibilidad, solicita préstamos, reserva libros no disponibles y revisa sus préstamos y multas |
| **Bibliotecario** | Gestiona el catálogo de libros, registra préstamos y devoluciones, administra reservas y multas |
| **Administrador** | Gestiona usuarios y roles, y configura parámetros como el período de préstamo y el valor de la multa |

## Funcionalidades principales

1. Gestión de libros
2. Gestión de usuarios
3. Consulta y búsqueda del catálogo
4. Consulta de disponibilidad
5. Gestión de préstamos y devoluciones
6. Gestión de reservas
7. Gestión de multas (cálculo automático por retraso)

El análisis completo define **21 requerimientos funcionales y 9 no funcionales**.

## Arquitectura

Arquitectura **Cliente-Servidor Web**, organizada internamente en **tres capas**:

| Capa | Carpeta | Responsabilidad |
|---|---|---|
| Presentación | `interfaz/` | Rutas web (Flask), plantillas HTML y archivos estáticos |
| Negocio | `nucleo/` | Reglas y validaciones como funciones puras, sin depender de Flask ni de la base de datos |
| Datos | `almacen/` | Lectura y escritura en la base de datos y control de transacciones |

El núcleo de reglas no depende de nada externo, por lo que se puede probar sin servidor ni base de datos.

## Tecnologías

- **Python** y **Flask** (framework web)
- **Supabase** (base de datos PostgreSQL en la nube)
- **Git** y **GitHub** (control de versiones)
- **Visual Studio Code** (editor)

## Estructura del repositorio

```
BaseBook/
├── README.md
└── Basebook-code/
    ├── main.py                  # arranque de la aplicación web
    ├── interfaz/                # capa de presentación
    │   ├── plantillas/
    │   └── estaticos/
    ├── nucleo/                  # capa de negocio (funciones puras)
    │   ├── tipos.py
    │   ├── reglas_catalogo.py
    │   ├── reglas_prestamo.py
    │   ├── reglas_reserva.py
    │   ├── reglas_multa.py
    │   ├── reglas_usuario.py
    │   ├── autenticacion.py
    │   └── permisos.py
    ├── almacen/                 # capa de datos
    │   ├── conexion.py
    │   ├── libros.py
    │   ├── prestamos.py
    │   ├── reservas.py
    │   ├── multas.py
    │   ├── usuarios.py
    │   └── parametros.py
    ├── pruebas/
    │   └── test_nucleo/
    └── datos/                   # esquema SQL y datos de ejemplo
```

## Equipo

- Julian David Henao Cataño
- Daniel Londoño Ruiz
- Alejandro Mosquera Lopez
- Miguel Angel Vergara Martinez