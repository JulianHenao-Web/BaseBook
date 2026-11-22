import logging
import os

from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()

logger = logging.getLogger(__name__)

_cliente_admin = None


class ErrorConfiguracion(Exception):
    """Falta una variable de entorno necesaria para conectar con Supabase."""


def _variable(nombre):
    valor = os.getenv(nombre)
    if not valor:
        logger.error("Falta la variable de entorno %s", nombre)
        raise ErrorConfiguracion(
            f"Falta la variable de entorno {nombre}. Revisa el archivo .env."
        )
    return valor


def cliente_anon() -> Client:
    """Cliente nuevo con la clave anon (registro / inicio de sesion)."""
    return create_client(_variable("SUPABASE_URL"), _variable("SUPABASE_ANON_KEY"))


def cliente_admin() -> Client:
    """Cliente unico con la clave service_role (solo servidor)."""
    global _cliente_admin
    if _cliente_admin is None:
        _cliente_admin = create_client(
            _variable("SUPABASE_URL"), _variable("SUPABASE_SERVICE_ROLE_KEY")
        )
    return _cliente_admin
