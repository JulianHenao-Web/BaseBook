# Jimmy Prada — Sistema de Gestión

Aplicación de escritorio para gestionar el catálogo de perfumes, registrar
inventarios físicos por gramos y generar catálogos y reportes en PDF.

Funciona **con o sin internet**: si hay conexión usa Supabase (nube), y si no
la hay trabaja contra una base local y sincroniza los cambios cuando vuelve
la conexión.

---

## 1. Requisitos previos

- **Python 3.10 o superior** (probado con 3.10 y 3.13).
- **pip** (viene con Python).
- **Internet** la primera vez para instalar dependencias.

Comprueba tu versión de Python:

```bash
python --version