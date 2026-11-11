from datetime import datetime

from flask import Blueprint, Response, abort, flash, g, redirect, render_template, request, url_for

from ..extensions import db
from ..models import (
    PRIORIDADES,
    ROLE_ADMIN,
    ROLE_TECNICO,
    STATUSES,
    TRANSICOES_PERMITIDAS,
    Chamado,
    Comentario,
    TransicaoInvalidaError,
)
from ..security import login_required, role_required
from ..services import chamados_visiveis, gerar_csv_chamados
from ..ui import CATEGORIAS, PRIORIDADE_UI, STATUS_UI

bp = Blueprint("chamados", __name__, url_prefix="/chamados")

PAPEIS_GESTAO = (ROLE_ADMIN, ROLE_TECNICO)


def _chamado_visivel_ou_404(chamado_id):
    chamado = db.session.get(Chamado, chamado_id)
    if chamado is None:
        abort(404)
    if g.usuario.is_cliente and chamado.cliente_id != g.usuario.id:
        abort(404)
    return chamado


def _comentarios_visiveis(chamado, eh_gestor):
    """Notas internas só aparecem para técnicos e admins."""
    return [
        c
        for c in sorted(chamado.comentarios, key=lambda c: c.created_at)
        if eh_gestor or not c.visibilidade_interna
    ]


@bp.get("/exportar.csv")
@role_required(*PAPEIS_GESTAO)
def exportar_csv():
    conteudo = gerar_csv_chamados(chamados_visiveis(g.usuario).order_by(Chamado.id).all())
    return Response(
        conteudo,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=chamados.csv"},
    )


@bp.get("/")
@login_required
def listar():
    status = request.args.get("status", "")
    prioridade = request.args.get("prioridade", "")

    consulta = chamados_visiveis(g.usuario)
    if status in STATUSES:
        consulta = consulta.filter(Chamado.status == status)
    if prioridade in PRIORIDADES:
        consulta = consulta.filter(Chamado.prioridade == prioridade)

    chamados = consulta.order_by(Chamado.created_at.desc()).all()
    return render_template(
        "chamados/lista.html",
        chamados=chamados,
        filtro_status=status,
        filtro_prioridade=prioridade,
        status_ui=STATUS_UI,
        prioridade_ui=PRIORIDADE_UI,
        status_opcoes=STATUSES,
        prioridade_opcoes=PRIORIDADES,
    )


@bp.route("/novo", methods=["GET", "POST"])
@login_required
def novo():
    erros = {}
    valores = {"titulo": "", "descricao": "", "categoria": "", "prioridade": "media"}

    if request.method == "POST":
        valores = {
            "titulo": request.form.get("titulo", "").strip(),
            "descricao": request.form.get("descricao", "").strip(),
            "categoria": request.form.get("categoria", "").strip(),
            "prioridade": request.form.get("prioridade", "").strip(),
        }
        if not valores["titulo"]:
            erros["titulo"] = "Informe um título."
        elif len(valores["titulo"]) > 150:
            erros["titulo"] = "O título deve ter no máximo 150 caracteres."
        if not valores["descricao"]:
            erros["descricao"] = "Descreva o problema."
        if valores["categoria"] not in CATEGORIAS:
            erros["categoria"] = "Selecione uma categoria válida."
        if valores["prioridade"] not in PRIORIDADES:
            erros["prioridade"] = "Selecione uma prioridade válida."

        if not erros:
            chamado = Chamado(
                titulo=valores["titulo"],
                descricao=valores["descricao"],
                categoria=valores["categoria"],
                prioridade=valores["prioridade"],
                cliente=g.usuario,
            )
            db.session.add(chamado)
            db.session.commit()
            flash(f"Chamado {chamado.protocolo} aberto com sucesso.", "sucesso")
            return redirect(url_for("chamados.detalhe", chamado_id=chamado.id))

    return render_template(
        "chamados/novo.html",
        erros=erros,
        valores=valores,
        categorias=CATEGORIAS,
        prioridade_opcoes=PRIORIDADES,
        prioridade_ui=PRIORIDADE_UI,
    )


@bp.get("/<int:chamado_id>")
@login_required
def detalhe(chamado_id):
    chamado = _chamado_visivel_ou_404(chamado_id)
    eh_gestor = g.usuario.role in PAPEIS_GESTAO
    comentarios = _comentarios_visiveis(chamado, eh_gestor)
    timeline = sorted(chamado.historico, key=lambda h: h.data_mudanca, reverse=True)

    return render_template(
        "chamados/detalhe.html",
        chamado=chamado,
        comentarios=comentarios,
        timeline=timeline,
        eh_gestor=eh_gestor,
        proximos_status=sorted(TRANSICOES_PERMITIDAS.get(chamado.status, ())),
        status_ui=STATUS_UI,
        prioridade_ui=PRIORIDADE_UI,
    )


@bp.get("/<int:chamado_id>/imprimir")
@login_required
def imprimir(chamado_id):
    chamado = _chamado_visivel_ou_404(chamado_id)

    return render_template(
        "chamados/imprimir.html",
        chamado=chamado,
        comentarios=_comentarios_visiveis(chamado, eh_gestor=False),
        historico=sorted(chamado.historico, key=lambda h: h.data_mudanca),
        agora=datetime.now(),
        status_ui=STATUS_UI,
        prioridade_ui=PRIORIDADE_UI,
    )


@bp.post("/<int:chamado_id>/status")
@role_required(*PAPEIS_GESTAO)
def alterar_status(chamado_id):
    chamado = _chamado_visivel_ou_404(chamado_id)
    novo_status = request.form.get("status", "")

    if novo_status not in STATUSES:
        flash("Status inválido.", "erro")
    else:
        try:
            chamado.alterar_status(novo_status, g.usuario)
            db.session.commit()
            flash(f"Status alterado para {STATUS_UI[novo_status]['rotulo']}.", "sucesso")
        except TransicaoInvalidaError as exc:
            db.session.rollback()
            flash(str(exc), "erro")

    return redirect(url_for("chamados.detalhe", chamado_id=chamado.id))


@bp.post("/<int:chamado_id>/assumir")
@role_required(*PAPEIS_GESTAO)
def assumir(chamado_id):
    chamado = _chamado_visivel_ou_404(chamado_id)
    try:
        chamado.assumir(g.usuario)
        db.session.commit()
        flash("Chamado atribuído a você.", "sucesso")
    except TransicaoInvalidaError as exc:
        db.session.rollback()
        flash(str(exc), "erro")
    return redirect(url_for("chamados.detalhe", chamado_id=chamado.id))


@bp.post("/<int:chamado_id>/comentarios")
@login_required
def comentar(chamado_id):
    chamado = _chamado_visivel_ou_404(chamado_id)
    conteudo = request.form.get("conteudo", "").strip()
    eh_gestor = g.usuario.role in PAPEIS_GESTAO
    # Só técnicos e admins podem gerar notas internas; para os demais o flag é ignorado.
    interna = eh_gestor and request.form.get("visibilidade_interna") == "on"

    if not conteudo:
        flash("O comentário não pode estar vazio.", "erro")
    elif len(conteudo) > 2000:
        flash("O comentário deve ter no máximo 2000 caracteres.", "erro")
    else:
        db.session.add(
            Comentario(
                chamado=chamado,
                autor=g.usuario,
                conteudo=conteudo,
                visibilidade_interna=interna,
            )
        )
        db.session.commit()
        flash("Comentário adicionado.", "sucesso")

    return redirect(url_for("chamados.detalhe", chamado_id=chamado.id))
