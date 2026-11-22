"crear la conexion con supabase para confirmar"

"""
almacen/usuarios.py  --  Capa de datos del modulo de usuarios (Supabase).

Responsabilidad: SOLO acceso a datos (Supabase Auth + tablas `usuarios`,
`roles` y `logs_auditoria`). No valida formatos ni decide permisos: eso vive
en nucleo/reglas_usuario.py, nucleo/autenticacion.py y nucleo/permisos.py.
No importa nada de Flask ni de interfaz/.

Requiere que almacen/conexion.py exponga:
    cliente_anon()   -> cliente NUEVO con la clave anon (registro / login).
                        Debe ser nuevo en cada llamada: al iniciar sesion el
                        cliente guarda la sesion del usuario.
    cliente_admin()  -> cliente con la clave service_role (operaciones
                        administrativas). Nunca se usa para iniciar sesion.

Formato de usuario devuelto (siempre igual):
    {"id", "nombre", "apellido", "documento", "correo", "telefono",
     "rol", "activo"}
"""

import functools
import logging

from almacen.conexion import cliente_admin, cliente_anon

# Excepciones de las librerias de Supabase (el modulo cambia de nombre segun
# la version instalada, por eso el respaldo).
try:
    from supabase_auth.errors import AuthApiError
except ImportError:  # pragma: no cover
    try:
        from gotrue.errors import AuthApiError
    except ImportError:
        class AuthApiError(Exception):
            """Respaldo si no se encuentra la clase de la libreria."""

try:
    from postgrest.exceptions import APIError
except ImportError:  # pragma: no cover
    class APIError(Exception):
        """Respaldo si no se encuentra la clase de la libreria."""

logger = logging.getLogger(__name__)

ROLES_VALIDOS = ("lector", "bibliotecario", "administrador")
CAMPOS_EDITABLES = ("nombre", "apellido", "telefono")  # nunca rol_id ni activo


# ---------------------------------------------------------------------------
# Errores propios (la interfaz solo ve estos, nunca el error crudo de Supabase)
# ---------------------------------------------------------------------------
class ErrorUsuarios(Exception):
    """Error base del modulo. El mensaje es apto para mostrar al usuario."""


class CorreoYaRegistrado(ErrorUsuarios):
    pass


class DocumentoYaRegistrado(ErrorUsuarios):
    pass


class CredencialesInvalidas(ErrorUsuarios):
    pass


class UsuarioInactivo(ErrorUsuarios):
    pass


class UsuarioNoEncontrado(ErrorUsuarios):
    pass


class RolInvalido(ErrorUsuarios):
    pass


class ErrorBaseDatos(ErrorUsuarios):
    """Fallo tecnico (base caida, red, etc.). Detalle solo en el log."""


def _proteger(funcion):
    """Convierte cualquier fallo inesperado en ErrorBaseDatos y lo registra."""

    @functools.wraps(funcion)
    def envoltura(*args, **kwargs):
        try:
            return funcion(*args, **kwargs)
        except ErrorUsuarios:
            raise
        except Exception:
            logger.exception("Fallo tecnico en usuarios.%s", funcion.__name__)
            raise ErrorBaseDatos(
                "El servicio no esta disponible en este momento. "
                "Intenta de nuevo mas tarde."
            )

    return envoltura


# ---------------------------------------------------------------------------
# Auxiliares internos
# ---------------------------------------------------------------------------
def _formatear(fila):
    """Fila de `usuarios` (con join a roles) -> diccionario uniforme."""
    if not fila:
        return None
    rol = fila.get("roles")
    if isinstance(rol, list):
        rol = rol[0] if rol else None
    return {
        "id": fila.get("id"),
        "nombre": fila.get("nombre"),
        "apellido": fila.get("apellido"),
        "documento": fila.get("documento"),
        "correo": fila.get("correo"),
        "telefono": fila.get("telefono"),
        "rol": rol.get("nombre") if rol else None,
        "activo": fila.get("activo"),
    }


def _id_rol(nombre_rol):
    """Devuelve el id de un rol por su nombre."""
    if nombre_rol not in ROLES_VALIDOS:
        raise RolInvalido(f"Rol no valido: {nombre_rol}")
    resp = (
        cliente_admin().table("roles").select("id").eq("nombre", nombre_rol)
        .limit(1).execute()
    )
    if not resp.data:
        raise RolInvalido(f"El rol '{nombre_rol}' no existe en la base de datos.")
    return resp.data[0]["id"]


def _es_duplicado(error):
    """True si un APIError de Postgrest es violacion de unicidad (23505)."""
    return getattr(error, "code", None) == "23505" or "duplicate" in str(error).lower()


# ---------------------------------------------------------------------------
# Auditoria
# ---------------------------------------------------------------------------
def registrar_log(usuario_id, accion, detalle=None):
    """
    Inserta en logs_auditoria. Es 'mejor esfuerzo': si falla, se registra en
    el log tecnico pero NO interrumpe la operacion principal.
    Nunca pasar contrasenas en `detalle`.
    """
    try:
        cliente_admin().table("logs_auditoria").insert({
            "usuario_id": usuario_id,
            "accion": accion,
            "detalle": detalle or {},
        }).execute()
    except Exception:
        logger.exception("No se pudo registrar el log de auditoria: %s", accion)


# ---------------------------------------------------------------------------
# Registro e inicio / cierre de sesion
# ---------------------------------------------------------------------------
@_proteger
def registrar_usuario(correo, contrasena, nombre, apellido=None,
                      documento=None, telefono=None):
    """
    Crea el usuario en Supabase Auth. El trigger de la base crea el perfil en
    `usuarios` con rol 'lector'; despues se completan los demas campos.
    Devuelve el usuario en formato uniforme.
    """
    correo = correo.strip().lower()

    try:
        resp = cliente_anon().auth.sign_up({
            "email": correo,
            "password": contrasena,
            "options": {"data": {"nombre": nombre}},
        })
    except AuthApiError as e:
        if "already" in str(e).lower() or "registered" in str(e).lower():
            raise CorreoYaRegistrado("Ese correo ya esta registrado.")
        logger.warning("sign_up rechazado: %s", e)
        raise ErrorUsuarios("No se pudo completar el registro.")

    usuario_auth = resp.user
    # Con confirmacion de correo activa, un correo repetido no lanza error:
    # devuelve un usuario sin 'identities'.
    if usuario_auth is None or not getattr(usuario_auth, "identities", True):
        raise CorreoYaRegistrado("Ese correo ya esta registrado.")

    datos = {"apellido": apellido, "documento": documento, "telefono": telefono}
    datos = {k: v for k, v in datos.items() if v is not None}

    if datos:
        try:
            cliente_admin().table("usuarios").update(datos).eq(
                "id", usuario_auth.id).execute()
        except APIError as e:
            # Deshacer: no dejar un usuario de Auth sin perfil completo.
            try:
                cliente_admin().auth.admin.delete_user(usuario_auth.id)
            except Exception:
                logger.exception("No se pudo revertir el usuario %s", usuario_auth.id)
            if _es_duplicado(e):
                raise DocumentoYaRegistrado("Ese documento ya esta registrado.")
            raise

    registrar_log(usuario_auth.id, "registro", {"correo": correo})
    return obtener_usuario_por_id(usuario_auth.id)


@_proteger
def iniciar_sesion(correo, contrasena):
    """
    Autentica con Supabase Auth (cliente anon nuevo). Devuelve el usuario con
    su rol y, en la clave "sesion", los tokens para que la capa web los guarde.
    Lanza CredencialesInvalidas o UsuarioInactivo segun el caso.
    """
    correo = correo.strip().lower()

    try:
        resp = cliente_anon().auth.sign_in_with_password(
            {"email": correo, "password": contrasena})
    except AuthApiError:
        registrar_log(None, "login_fallido", {"correo": correo})
        raise CredencialesInvalidas("Correo o contrasena incorrectos.")

    usuario = obtener_usuario_por_id(resp.user.id)
    if usuario is None:
        registrar_log(resp.user.id, "login_fallido",
                      {"correo": correo, "motivo": "sin_perfil"})
        raise CredencialesInvalidas("Correo o contrasena incorrectos.")

    if not usuario["activo"]:
        registrar_log(usuario["id"], "login_fallido",
                      {"correo": correo, "motivo": "usuario_inactivo"})
        raise UsuarioInactivo("Tu cuenta esta desactivada. Contacta a la biblioteca.")

    registrar_log(usuario["id"], "login_exitoso", {"correo": correo})
    usuario["sesion"] = {
        "access_token": resp.session.access_token,
        "refresh_token": resp.session.refresh_token,
    }
    return usuario


@_proteger
def cerrar_sesion(access_token=None):
    """
    Invalida la sesion en Supabase si se entrega el token. La sesion de Flask
    (cookie) la limpia la capa de interfaz.
    """
    if access_token:
        try:
            cliente_admin().auth.admin.sign_out(access_token)
        except Exception:
            logger.warning("No se pudo invalidar el token en Supabase.")


# ---------------------------------------------------------------------------
# Consultas
# ---------------------------------------------------------------------------
@_proteger
def obtener_usuario_por_id(usuario_id):
    resp = (
        cliente_admin().table("usuarios").select("*, roles(nombre)")
        .eq("id", usuario_id).limit(1).execute()
    )
    return _formatear(resp.data[0]) if resp.data else None


@_proteger
def obtener_usuario_por_correo(correo):
    resp = (
        cliente_admin().table("usuarios").select("*, roles(nombre)")
        .eq("correo", correo.strip().lower()).limit(1).execute()
    )
    return _formatear(resp.data[0]) if resp.data else None


@_proteger
def listar_usuarios(rol=None, activo=None, texto=None, limite=50, desplazamiento=0):
    """
    Lista usuarios con filtros opcionales: rol, activo y texto (busca en
    nombre, apellido y correo). Paginado con limite / desplazamiento.
    """
    consulta = cliente_admin().table("usuarios").select("*, roles(nombre)")

    if rol is not None:
        consulta = consulta.eq("rol_id", _id_rol(rol))
    if activo is not None:
        consulta = consulta.eq("activo", activo)
    if texto:
        t = "".join(c for c in texto if c not in ",()%*").strip()
        if t:
            consulta = consulta.or_(
                f"nombre.ilike.%{t}%,apellido.ilike.%{t}%,correo.ilike.%{t}%")

    resp = (
        consulta.order("nombre")
        .range(desplazamiento, desplazamiento + limite - 1).execute()
    )
    return [_formatear(f) for f in resp.data]


# ---------------------------------------------------------------------------
# Modificaciones
# ---------------------------------------------------------------------------
@_proteger
def actualizar_perfil(usuario_id, datos):
    """
    Actualiza SOLO nombre, apellido y telefono. Cualquier otro campo
    (rol_id, activo, correo...) se ignora.
    """
    permitidos = {k: v for k, v in datos.items() if k in CAMPOS_EDITABLES}
    if not permitidos:
        raise ErrorUsuarios("No hay campos validos para actualizar.")

    resp = (
        cliente_admin().table("usuarios").update(permitidos)
        .eq("id", usuario_id).execute()
    )
    if not resp.data:
        raise UsuarioNoEncontrado("El usuario no existe.")
    return obtener_usuario_por_id(usuario_id)


@_proteger
def cambiar_rol(usuario_id, nuevo_rol, actor_id=None):
    """
    Cambia el rol de un usuario. Llamar SOLO despues de que permisos.py haya
    confirmado que quien lo pide (actor_id) es administrador.
    """
    anterior = obtener_usuario_por_id(usuario_id)
    if anterior is None:
        raise UsuarioNoEncontrado("El usuario no existe.")

    cliente_admin().table("usuarios").update(
        {"rol_id": _id_rol(nuevo_rol)}).eq("id", usuario_id).execute()

    registrar_log(actor_id, "cambio_rol", {
        "usuario_afectado": usuario_id,
        "rol_anterior": anterior["rol"],
        "rol_nuevo": nuevo_rol,
    })
    return obtener_usuario_por_id(usuario_id)


@_proteger
def cambiar_estado(usuario_id, activo, actor_id=None):
    """Activa o desactiva un usuario (activo=True / False)."""
    resp = (
        cliente_admin().table("usuarios").update({"activo": bool(activo)})
        .eq("id", usuario_id).execute()
    )
    if not resp.data:
        raise UsuarioNoEncontrado("El usuario no existe.")

    registrar_log(actor_id, "cambio_estado", {
        "usuario_afectado": usuario_id,
        "activo": bool(activo),
    })
    return obtener_usuario_por_id(usuario_id)
