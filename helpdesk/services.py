"""Consultas e agregações usadas pelo painel analítico e pelas listagens de chamados."""

import csv
import io

from sqlalchemy import func

from .extensions import db
from .models import (
    PRIORIDADE_CRITICA,
    PRIORIDADES,
    STATUS_AGUARDANDO_VALIDACAO,
    STATUS_ABERTO,
    STATUS_CONCLUIDO,
    STATUS_EM_ANALISE,
    STATUS_EM_EXECUCAO,
    Chamado,
)
from .ui import CATEGORIAS, PRIORIDADE_UI, STATUS_UI

STATUS_EM_ANDAMENTO = (
    STATUS_ABERTO,
    STATUS_EM_ANALISE,
    STATUS_EM_EXECUCAO,
    STATUS_AGUARDANDO_VALIDACAO,
)


def filtros_visibilidade(usuario):
    """Cliente vê apenas os próprios chamados; técnico e admin veem todos."""
    if usuario.is_cliente:
        return [Chamado.cliente_id == usuario.id]
    return []


def chamados_visiveis(usuario):
    return Chamado.query.filter(*filtros_visibilidade(usuario))


def resumo_kpis(usuario):
    filtros = filtros_visibilidade(usuario)

    def contar(*criterios):
        return db.session.query(func.count(Chamado.id)).filter(*filtros, *criterios).scalar()

    return {
        "total": contar(),
        "em_andamento": contar(Chamado.status.in_(STATUS_EM_ANDAMENTO)),
        "concluidos": contar(Chamado.status == STATUS_CONCLUIDO),
        "criticos": contar(
            Chamado.prioridade == PRIORIDADE_CRITICA,
            Chamado.status.in_(STATUS_EM_ANDAMENTO),
        ),
    }


def gerar_csv_chamados(chamados):
    """CSV com separador ';' e BOM UTF-8, para abrir corretamente no Excel."""
    buffer = io.StringIO()
    escritor = csv.writer(buffer, delimiter=";")
    escritor.writerow(
        [
            "Protocolo",
            "Título",
            "Categoria",
            "Prioridade",
            "Status",
            "Cliente",
            "Técnico",
            "Aberto em",
            "Atualizado em",
        ]
    )
    for chamado in chamados:
        escritor.writerow(
            [
                chamado.protocolo,
                chamado.titulo,
                chamado.categoria,
                PRIORIDADE_UI[chamado.prioridade]["rotulo"],
                STATUS_UI[chamado.status]["rotulo"],
                chamado.cliente.nome,
                chamado.tecnico.nome if chamado.tecnico else "",
                chamado.created_at.strftime("%d/%m/%Y %H:%M"),
                chamado.updated_at.strftime("%d/%m/%Y %H:%M"),
            ]
        )
    return "\ufeff" + buffer.getvalue()


def dados_graficos():
    """Dados agregados para o Chart.js (somente técnicos e admins)."""
    por_status = dict(
        db.session.query(Chamado.status, func.count(Chamado.id))
        .group_by(Chamado.status)
        .all()
    )
    por_categoria_prioridade = {
        (categoria, prioridade): total
        for categoria, prioridade, total in db.session.query(
            Chamado.categoria, Chamado.prioridade, func.count(Chamado.id)
        )
        .group_by(Chamado.categoria, Chamado.prioridade)
        .all()
    }

    return {
        "status": {
            "labels": [info["rotulo"] for info in STATUS_UI.values()],
            "valores": [por_status.get(status, 0) for status in STATUS_UI],
            "cores": [info["cor"] for info in STATUS_UI.values()],
        },
        "categorias": {
            "labels": list(CATEGORIAS),
            "series": [
                {
                    "label": PRIORIDADE_UI[prioridade]["rotulo"],
                    "cor": PRIORIDADE_UI[prioridade]["cor"],
                    "valores": [
                        por_categoria_prioridade.get((categoria, prioridade), 0)
                        for categoria in CATEGORIAS
                    ],
                }
                for prioridade in PRIORIDADES
            ],
        },
    }
