"""Carga inicial de dados de demonstração (executada apenas se o banco estiver vazio)."""

from datetime import timedelta

from .extensions import db
from .models import (
    PRIORIDADE_ALTA,
    PRIORIDADE_BAIXA,
    PRIORIDADE_CRITICA,
    PRIORIDADE_MEDIA,
    ROLE_ADMIN,
    ROLE_CLIENTE,
    ROLE_TECNICO,
    STATUS_AGUARDANDO_VALIDACAO,
    STATUS_CANCELADO,
    STATUS_CONCLUIDO,
    STATUS_EM_ANALISE,
    STATUS_EM_EXECUCAO,
    Chamado,
    Comentario,
    Usuario,
    utcnow,
)

USUARIOS_INICIAIS = [
    ("Ana Administradora", "admin@helpdesk.local", ROLE_ADMIN),
    ("Carlos Técnico", "carlos.tecnico@helpdesk.local", ROLE_TECNICO),
    ("Mariana Suporte", "mariana.suporte@helpdesk.local", ROLE_TECNICO),
    ("TI Alfa Ltda", "ti@alfa.example.com", ROLE_CLIENTE),
    ("Suporte Beta S.A.", "suporte@beta.example.com", ROLE_CLIENTE),
]

# Cada cenário: (titulo, descricao, categoria, prioridade, cliente, tecnico,
#                dias_atras, fluxo, comentarios). O fluxo é lista de (status, ator, horas_apos).
# ator: "cliente" | "tecnico" (técnico atribuído) | "cancelamento_cliente"
CENARIOS = [
    {
        "titulo": "Impressora do financeiro sem conexão de rede",
        "descricao": "A impressora HP do setor financeiro não aparece na rede desde ontem.",
        "categoria": "Hardware",
        "prioridade": PRIORIDADE_ALTA,
        "cliente": "ti@alfa.example.com",
        "tecnico": "carlos.tecnico@helpdesk.local",
        "dias_atras": 20,
        "fluxo": [(STATUS_EM_ANALISE, 2), (STATUS_EM_EXECUCAO, 5), (STATUS_AGUARDANDO_VALIDACAO, 30), (STATUS_CONCLUIDO, 48)],
    },
    {
        "titulo": "Acesso VPN bloqueado para equipe remota",
        "descricao": "Três colaboradores não conseguem autenticar na VPN corporativa.",
        "categoria": "Redes",
        "prioridade": PRIORIDADE_CRITICA,
        "cliente": "suporte@beta.example.com",
        "tecnico": "mariana.suporte@helpdesk.local",
        "dias_atras": 15,
        "fluxo": [(STATUS_EM_ANALISE, 1), (STATUS_EM_EXECUCAO, 2), (STATUS_AGUARDANDO_VALIDACAO, 8), (STATUS_CONCLUIDO, 10)],
    },
    {
        "titulo": "Instalação do pacote Office no novo notebook",
        "descricao": "Solicitação de instalação e ativação de licença Office 365.",
        "categoria": "Software",
        "prioridade": PRIORIDADE_BAIXA,
        "cliente": "ti@alfa.example.com",
        "tecnico": "carlos.tecnico@helpdesk.local",
        "dias_atras": 12,
        "fluxo": [(STATUS_EM_ANALISE, 4), (STATUS_EM_EXECUCAO, 6), (STATUS_AGUARDANDO_VALIDACAO, 9), (STATUS_CONCLUIDO, 24)],
    },
    {
        "titulo": "Lentidão extrema no servidor de arquivos",
        "descricao": "Cópias de arquivos levam mais de 10 minutos desde a última atualização.",
        "categoria": "Infraestrutura",
        "prioridade": PRIORIDADE_CRITICA,
        "cliente": "ti@alfa.example.com",
        "tecnico": "mariana.suporte@helpdesk.local",
        "dias_atras": 9,
        "fluxo": [(STATUS_EM_ANALISE, 1), (STATUS_EM_EXECUCAO, 3)],
    },
    {
        "titulo": "Configuração de e-mail corporativo no celular",
        "descricao": "Preciso sincronizar o e-mail corporativo no meu smartphone.",
        "categoria": "Software",
        "prioridade": PRIORIDADE_BAIXA,
        "cliente": "suporte@beta.example.com",
        "tecnico": None,
        "dias_atras": 6,
        "fluxo": [],
    },
    {
        "titulo": "Solicitação de novo usuário para o ERP",
        "descricao": "Criar acesso ao ERP para novo analista de compras.",
        "categoria": "Acessos",
        "prioridade": PRIORIDADE_MEDIA,
        "cliente": "suporte@beta.example.com",
        "tecnico": "carlos.tecnico@helpdesk.local",
        "dias_atras": 5,
        "fluxo": [(STATUS_EM_ANALISE, 3), (STATUS_EM_EXECUCAO, 8)],
    },
    {
        "titulo": "Falha intermitente no sistema de ponto",
        "descricao": "O terminal de ponto da portaria reinicia sem aviso.",
        "categoria": "Hardware",
        "prioridade": PRIORIDADE_ALTA,
        "cliente": "ti@alfa.example.com",
        "tecnico": "mariana.suporte@helpdesk.local",
        "dias_atras": 4,
        "fluxo": [(STATUS_EM_ANALISE, 2), (STATUS_EM_EXECUCAO, 5), (STATUS_AGUARDANDO_VALIDACAO, 20)],
    },
    {
        "titulo": "Atualização de certificado SSL do portal",
        "descricao": "Certificado do portal de clientes expira em 10 dias.",
        "categoria": "Segurança",
        "prioridade": PRIORIDADE_ALTA,
        "cliente": "suporte@beta.example.com",
        "tecnico": "carlos.tecnico@helpdesk.local",
        "dias_atras": 3,
        "fluxo": [(STATUS_EM_ANALISE, 1)],
    },
    {
        "titulo": "Pedido de cancelamento de licença duplicada",
        "descricao": "Licença comprada em duplicidade pelo setor de vendas.",
        "categoria": "Software",
        "prioridade": PRIORIDADE_BAIXA,
        "cliente": "ti@alfa.example.com",
        "tecnico": None,
        "dias_atras": 2,
        "fluxo": [(STATUS_CANCELADO, 1)],
    },
    {
        "titulo": "Monitor com tela piscando",
        "descricao": "Monitor secundário da estação de vendas apresenta flicker constante.",
        "categoria": "Hardware",
        "prioridade": PRIORIDADE_MEDIA,
        "cliente": "suporte@beta.example.com",
        "tecnico": "mariana.suporte@helpdesk.local",
        "dias_atras": 1,
        "fluxo": [(STATUS_EM_ANALISE, 2)],
    },
]

COMENTARIOS_EXEMPLO = {
    "Impressora do financeiro sem conexão de rede": [
        ("tecnico", "Driver reinstalado, aguardando teste do usuário.", False),
        ("tecnico", "Verificar a VLAN do switch do 2º andar (uso interno).", True),
    ],
    "Lentidão extrema no servidor de arquivos": [
        ("cliente", "O problema começou após a última janela de manutenção.", False),
    ],
}


def _usuario_por_email(email):
    return Usuario.query.filter_by(email=email).one()


def popular_banco_inicial(senha_padrao):
    """Cria usuários e chamados de demonstração se a tabela de usuários estiver vazia."""
    if Usuario.query.first() is not None:
        return False

    try:
        usuarios = {}
        for nome, email, role in USUARIOS_INICIAIS:
            usuario = Usuario(nome=nome, email=email, role=role)
            usuario.definir_senha(senha_padrao)
            db.session.add(usuario)
            usuarios[email] = usuario
        db.session.flush()

        agora = utcnow()
        for cenario in CENARIOS:
            criado_em = agora - timedelta(days=cenario["dias_atras"])
            cliente = usuarios[cenario["cliente"]]
            tecnico = usuarios[cenario["tecnico"]] if cenario["tecnico"] else None

            chamado = Chamado(
                titulo=cenario["titulo"],
                descricao=cenario["descricao"],
                categoria=cenario["categoria"],
                prioridade=cenario["prioridade"],
                cliente=cliente,
                created_at=criado_em,
                updated_at=criado_em,
            )
            db.session.add(chamado)
            db.session.flush()

            if tecnico is not None and cenario["fluxo"]:
                chamado.tecnico = tecnico

            for novo_status, horas in cenario["fluxo"]:
                momento = criado_em + timedelta(hours=horas)
                if novo_status == STATUS_CANCELADO:
                    autor = cliente
                else:
                    autor = tecnico
                chamado.alterar_status(novo_status, autor, momento=momento)
                db.session.flush()

            for ator, conteudo, interno in COMENTARIOS_EXEMPLO.get(cenario["titulo"], []):
                autor = cliente if ator == "cliente" else tecnico
                db.session.add(
                    Comentario(
                        chamado=chamado,
                        autor=autor,
                        conteudo=conteudo,
                        visibilidade_interna=interno,
                        created_at=criado_em + timedelta(hours=1),
                    )
                )

        db.session.commit()
        return True
    except Exception:
        db.session.rollback()
        raise
