"""Rotas principais de renderização inicial."""

from flask import Blueprint, g, redirect, render_template, url_for

from ..security import login_required, role_required
from ..services import dados_graficos, resumo_kpis
from ..ui import PRIORIDADE_UI, STATUS_UI

main_bp = Blueprint("main", __name__)

PAPEIS_GRAFICOS = ("admin", "tecnico")


@main_bp.route("/")
def index():
    return redirect(url_for("main.painel"))


@main_bp.route("/painel")
@login_required
def painel():
    eh_gestor = g.usuario.role in PAPEIS_GRAFICOS
    return render_template(
        "painel.html",
        kpis=resumo_kpis(g.usuario),
        graficos=dados_graficos() if eh_gestor else None,
        eh_gestor=eh_gestor,
        status_ui=STATUS_UI,
        prioridade_ui=PRIORIDADE_UI,
    )


@main_bp.route("/admin")
@role_required("admin")
def admin():
    return redirect(url_for("usuarios.listar"))
