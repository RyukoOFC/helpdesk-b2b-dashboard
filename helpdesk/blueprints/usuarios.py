"""Gestão de usuários (exclusiva para administradores)."""

import re

from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..models import ROLE_ADMIN, ROLES, Usuario
from ..security import role_required
from ..ui import ROLE_UI

bp = Blueprint("usuarios", __name__, url_prefix="/admin/usuarios")

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
SENHA_MINIMA = 8


def _renderizar_lista(erros=None, valores=None, status=200):
    return (
        render_template(
            "admin/usuarios.html",
            usuarios=Usuario.query.order_by(Usuario.created_at.desc(), Usuario.id.desc()).all(),
            erros=erros or {},
            valores=valores or {"nome": "", "email": "", "role": "cliente"},
            role_ui=ROLE_UI,
            papeis=ROLES,
        ),
        status,
    )


@bp.get("/")
@role_required(ROLE_ADMIN)
def listar():
    return _renderizar_lista()


@bp.post("/")
@role_required(ROLE_ADMIN)
def criar():
    valores = {
        "nome": request.form.get("nome", "").strip(),
        "email": request.form.get("email", "").strip().lower(),
        "role": request.form.get("role", "").strip(),
    }
    senha = request.form.get("senha", "")
    erros = {}

    if not valores["nome"]:
        erros["nome"] = "Informe o nome."
    elif len(valores["nome"]) > 120:
        erros["nome"] = "O nome deve ter no máximo 120 caracteres."
    if not EMAIL_REGEX.match(valores["email"]) or len(valores["email"]) > 160:
        erros["email"] = "Informe um e-mail válido."
    elif Usuario.query.filter_by(email=valores["email"]).first():
        erros["email"] = "Já existe uma conta com este e-mail."
    if len(senha) < SENHA_MINIMA:
        erros["senha"] = f"A senha deve ter pelo menos {SENHA_MINIMA} caracteres."
    if valores["role"] not in ROLES:
        erros["role"] = "Selecione um perfil válido."

    if erros:
        return _renderizar_lista(erros=erros, valores=valores, status=422)

    usuario = Usuario(nome=valores["nome"], email=valores["email"], role=valores["role"])
    usuario.definir_senha(senha)
    db.session.add(usuario)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash("Não foi possível criar a conta: e-mail já cadastrado.", "erro")
        return redirect(url_for("usuarios.listar"))

    flash(f"Conta de {usuario.nome} criada com o perfil {ROLE_UI[usuario.role]['rotulo']}.", "sucesso")
    return redirect(url_for("usuarios.listar"))


@bp.post("/<int:usuario_id>/papel")
@role_required(ROLE_ADMIN)
def alterar_papel(usuario_id):
    usuario = db.session.get(Usuario, usuario_id)
    if usuario is None:
        abort(404)

    novo_papel = request.form.get("role", "")
    if novo_papel not in ROLES:
        flash("Perfil inválido.", "erro")
    elif usuario.id == g.usuario.id:
        flash("Você não pode alterar o próprio perfil.", "erro")
    else:
        usuario.role = novo_papel
        db.session.commit()
        flash(f"Perfil de {usuario.nome} alterado para {ROLE_UI[novo_papel]['rotulo']}.", "sucesso")

    return redirect(url_for("usuarios.listar"))
