"""Rotas de autenticação: login e logout."""

from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from ..models import Usuario

auth_bp = Blueprint("auth", __name__)

# Hash fictício usado para igualar o tempo de resposta quando o e-mail não existe.
_HASH_FICTICIO = generate_password_hash("senha-ficticia-para-timing")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if g.get("usuario") is not None:
        return redirect(url_for("main.painel"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha", "")

        usuario = Usuario.query.filter_by(email=email).first()
        if usuario is None:
            check_password_hash(_HASH_FICTICIO, senha)
            autenticado = False
        else:
            autenticado = usuario.verificar_senha(senha)

        if autenticado:
            session.clear()
            session["usuario_id"] = usuario.id
            session.permanent = True
            flash(f"Bem-vindo, {usuario.nome}!", "sucesso")
            return redirect(url_for("main.painel"))

        flash("E-mail ou senha inválidos.", "erro")
        return render_template("login.html", email=email), 401

    return render_template("login.html", email="")


@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("Sessão encerrada.", "info")
    return redirect(url_for("auth.login"))
