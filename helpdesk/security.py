"""Autenticação por sessão e controle de acesso por papel (RBAC)."""

from functools import wraps

from flask import abort, g, redirect, session, url_for

from .models import Usuario
from .extensions import db


def carregar_usuario_logado():
    """Carrega o usuário da sessão em g.usuario antes de cada requisição."""
    g.usuario = None
    usuario_id = session.get("usuario_id")
    if usuario_id is None:
        return
    usuario = db.session.get(Usuario, usuario_id)
    if usuario is None:
        session.clear()
        return
    g.usuario = usuario


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if g.get("usuario") is None:
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)

    return wrapper


def role_required(*papeis):
    """Restringe a rota aos papéis informados. Responde 403 se o papel não for permitido."""

    def decorador(view):
        @wraps(view)
        @login_required
        def wrapper(*args, **kwargs):
            if g.usuario.role not in papeis:
                abort(403)
            return view(*args, **kwargs)

        return wrapper

    return decorador
