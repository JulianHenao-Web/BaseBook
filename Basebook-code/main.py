"""Aplicación web inicial de BaseBook."""

import hmac
import importlib
import logging
import os
import secrets
from typing import Any

from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    pass
else:
    load_dotenv()


logger = logging.getLogger(__name__)
app = Flask(
    __name__,
    template_folder="interfaz/plantillas",
    static_folder="interfaz/estaticos",
    static_url_path="/static",
)
app.config.update(
    SECRET_KEY=os.getenv("FLASK_SECRET_KEY") or secrets.token_hex(32),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.getenv("FLASK_COOKIE_SECURE") == "1",
)


class ServicioNoDisponible(Exception):
    """Un módulo opcional o una de sus dependencias no está instalado."""


class ErrorOperacion(Exception):
    """Error funcional que se puede mostrar en la interfaz."""

    def __init__(self, mensaje: str, codigo_http: int = 400) -> None:
        super().__init__(mensaje)
        self.codigo_http = codigo_http


def _cargar_servicio(nombre: str, simbolos: tuple[str, ...]) -> Any:
    try:
        modulo = importlib.import_module(nombre)
    except ModuleNotFoundError as error:
        logger.warning("No está disponible el módulo %s: %s", nombre, error)
        raise ServicioNoDisponible(
            "Este servicio no está disponible todavía. "
            "La interfaz puede seguir usándose."
        ) from error
    if any(not hasattr(modulo, simbolo) for simbolo in simbolos):
        logger.warning("El módulo %s todavía no implementa su servicio.", nombre)
        raise ServicioNoDisponible(
            "Este servicio no está implementado todavía. "
            "La interfaz puede seguir usándose."
        )
    return modulo


def _token_csrf() -> str:
    token = session.get("_csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["_csrf_token"] = token
    return token


@app.context_processor
def exponer_token_csrf() -> dict[str, Any]:
    return {"csrf_token": _token_csrf}


@app.before_request
def proteger_formularios() -> None:
    if request.method != "POST":
        return

    token_enviado = request.form.get("csrf_token", "")
    token_sesion = session.get("_csrf_token", "")
    if not token_enviado or not token_sesion or not hmac.compare_digest(
        token_enviado, token_sesion
    ):
        abort(
            400,
            description="El formulario expiró. Recarga la página e inténtalo de nuevo.",
        )


def _buscar_libros(consulta: str) -> tuple[Any, ...]:
    api_libros = _cargar_servicio(
        "almacen.api_libros", ("ErrorBusquedaOpenLibrary", "buscar_libros")
    )
    try:
        return api_libros.buscar_libros(consulta, limite=8)
    except api_libros.ErrorBusquedaOpenLibrary as error:
        raise ErrorOperacion(str(error), 503) from error


def _operar_usuarios(
    operacion: str, *, error_http: int, **datos: Any
) -> Any:
    usuarios = _cargar_servicio(
        "almacen.usuarios",
        ("ErrorBaseDatos", "ErrorUsuarios", operacion),
    )
    try:
        return getattr(usuarios, operacion)(**datos)
    except usuarios.ErrorBaseDatos as error:
        raise ErrorOperacion(str(error), 503) from error
    except usuarios.ErrorUsuarios as error:
        raise ErrorOperacion(str(error), error_http) from error


@app.get("/")
def inicio():
    consulta = request.args.get("q", "").strip()
    libros = ()

    if consulta:
        try:
            libros = _buscar_libros(consulta)
        except ServicioNoDisponible as error:
            flash(str(error), "error")
        except ErrorOperacion as error:
            flash(str(error), "error")
        except ValueError as error:
            flash(str(error), "error")

    return render_template("index.html", consulta=consulta, libros=libros)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    correo = request.form.get("correo", "").strip()
    contrasena = request.form.get("contrasena", "")
    if not correo or not contrasena:
        flash("Ingresa tu correo y contraseña.", "error")
        return render_template("login.html"), 400

    try:
        usuario = _operar_usuarios(
            "iniciar_sesion",
            error_http=401,
            correo=correo,
            contrasena=contrasena,
        )
    except (ServicioNoDisponible, ErrorOperacion) as error:
        flash(str(error), "error")
        codigo_http = (
            error.codigo_http if isinstance(error, ErrorOperacion) else 503
        )
        return render_template("login.html"), codigo_http

    session.clear()
    session["usuario"] = {
        "id": usuario.get("id"),
        "nombre": usuario.get("nombre") or "",
        "apellido": usuario.get("apellido") or "",
        "rol": usuario.get("rol") or "lector",
    }
    flash("Sesión iniciada correctamente.", "success")
    return redirect(url_for("inicio"))


@app.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "GET":
        return render_template("registro.html")

    nombre = request.form.get("nombre", "").strip()
    apellido = request.form.get("apellido", "").strip()
    correo = request.form.get("correo", "").strip()
    documento = request.form.get("documento", "").strip()
    telefono = request.form.get("telefono", "").strip()
    contrasena = request.form.get("contrasena", "")
    confirmar_contrasena = request.form.get("confirmar_contrasena", "")

    if not nombre or not correo or not contrasena:
        flash("Nombre, correo y contraseña son obligatorios.", "error")
        return render_template("registro.html"), 400
    if len(contrasena) < 8:
        flash("La contraseña debe tener al menos 8 caracteres.", "error")
        return render_template("registro.html"), 400
    if contrasena != confirmar_contrasena:
        flash("Las contraseñas no coinciden.", "error")
        return render_template("registro.html"), 400

    try:
        _operar_usuarios(
            "registrar_usuario",
            error_http=400,
            correo=correo,
            contrasena=contrasena,
            nombre=nombre,
            apellido=apellido or None,
            documento=documento or None,
            telefono=telefono or None,
        )
    except (ServicioNoDisponible, ErrorOperacion) as error:
        flash(str(error), "error")
        codigo_http = (
            error.codigo_http if isinstance(error, ErrorOperacion) else 503
        )
        return render_template("registro.html"), codigo_http

    flash("Registro completado. Ya puedes iniciar sesión.", "success")
    return redirect(url_for("login"))


@app.post("/logout")
def logout():
    session.clear()
    flash("Has cerrado sesión.", "success")
    return redirect(url_for("inicio"))


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=int(os.getenv("PORT", "5000")),
        debug=os.getenv("FLASK_DEBUG") == "1",
    )