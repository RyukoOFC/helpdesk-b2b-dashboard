"""Modelos do domínio: usuários, chamados, histórico de status e comentários."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import event, inspect
from sqlalchemy.orm import Session
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db

ROLE_ADMIN = "admin"
ROLE_TECNICO = "tecnico"
ROLE_CLIENTE = "cliente"
ROLES = (ROLE_ADMIN, ROLE_TECNICO, ROLE_CLIENTE)

PRIORIDADE_BAIXA = "baixa"
PRIORIDADE_MEDIA = "media"
PRIORIDADE_ALTA = "alta"
PRIORIDADE_CRITICA = "critica"
PRIORIDADES = (PRIORIDADE_BAIXA, PRIORIDADE_MEDIA, PRIORIDADE_ALTA, PRIORIDADE_CRITICA)

STATUS_ABERTO = "aberto"
STATUS_EM_ANALISE = "em_analise"
STATUS_EM_EXECUCAO = "em_execucao"
STATUS_AGUARDANDO_VALIDACAO = "aguardando_validacao"
STATUS_CONCLUIDO = "concluido"
STATUS_CANCELADO = "cancelado"
STATUSES = (
    STATUS_ABERTO,
    STATUS_EM_ANALISE,
    STATUS_EM_EXECUCAO,
    STATUS_AGUARDANDO_VALIDACAO,
    STATUS_CONCLUIDO,
    STATUS_CANCELADO,
)

# Fluxo lógico permitido. Estados terminais não aparecem como chaves.
TRANSICOES_PERMITIDAS = {
    STATUS_ABERTO: {STATUS_EM_ANALISE, STATUS_CANCELADO},
    STATUS_EM_ANALISE: {STATUS_EM_EXECUCAO, STATUS_CANCELADO},
    STATUS_EM_EXECUCAO: {STATUS_AGUARDANDO_VALIDACAO, STATUS_EM_ANALISE},
    STATUS_AGUARDANDO_VALIDACAO: {STATUS_CONCLUIDO, STATUS_EM_EXECUCAO},
}


class TransicaoInvalidaError(ValueError):
    """Lançado quando uma mudança de status não segue o fluxo permitido."""


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _check(expressao, nome):
    return db.CheckConstraint(expressao, name=nome)


class Usuario(db.Model):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(160), nullable=False, unique=True, index=True)
    senha_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default=ROLE_CLIENTE)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    chamados_abertos = db.relationship(
        "Chamado", foreign_keys="Chamado.cliente_id", back_populates="cliente"
    )
    chamados_atribuidos = db.relationship(
        "Chamado", foreign_keys="Chamado.tecnico_id", back_populates="tecnico"
    )

    __table_args__ = (
        _check(f"role IN {ROLES}", "ck_usuarios_role"),
    )

    def definir_senha(self, senha):
        self.senha_hash = generate_password_hash(senha)

    def verificar_senha(self, senha):
        return check_password_hash(self.senha_hash, senha)

    @property
    def is_admin(self):
        return self.role == ROLE_ADMIN

    @property
    def is_tecnico(self):
        return self.role == ROLE_TECNICO

    @property
    def is_cliente(self):
        return self.role == ROLE_CLIENTE

    def __repr__(self):
        return f"<Usuario {self.email} ({self.role})>"


class Chamado(db.Model):
    __tablename__ = "chamados_os"

    id = db.Column(db.Integer, primary_key=True)
    # Placeholder único; o protocolo definitivo é gravado pelo listener after_insert.
    protocolo = db.Column(
        db.String(20), unique=True, nullable=False, default=lambda: f"TMP-{uuid.uuid4().hex}"
    )
    titulo = db.Column(db.String(150), nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    categoria = db.Column(db.String(60), nullable=False)
    prioridade = db.Column(db.String(10), nullable=False, default=PRIORIDADE_MEDIA)
    status = db.Column(db.String(25), nullable=False, default=STATUS_ABERTO)
    cliente_id = db.Column(
        db.Integer, db.ForeignKey("usuarios.id"), nullable=False, index=True
    )
    tecnico_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    cliente = db.relationship(
        "Usuario", foreign_keys=[cliente_id], back_populates="chamados_abertos"
    )
    tecnico = db.relationship(
        "Usuario", foreign_keys=[tecnico_id], back_populates="chamados_atribuidos"
    )
    historico = db.relationship(
        "HistoricoStatus",
        back_populates="chamado",
        cascade="all, delete-orphan",
        order_by="HistoricoStatus.data_mudanca",
    )
    comentarios = db.relationship(
        "Comentario",
        back_populates="chamado",
        cascade="all, delete-orphan",
        order_by="Comentario.created_at",
    )

    __table_args__ = (
        _check(f"prioridade IN {PRIORIDADES}", "ck_chamados_prioridade"),
        _check(f"status IN {STATUSES}", "ck_chamados_status"),
        db.Index("ix_chamados_status_prioridade", "status", "prioridade"),
    )

    def alterar_status(self, novo_status, usuario, momento=None):
        """Altera o status validando o fluxo. O histórico é gravado no flush."""
        if novo_status not in STATUSES:
            raise TransicaoInvalidaError(f"Status desconhecido: {novo_status}")
        atual = self.status
        if novo_status == atual:
            return
        if novo_status not in TRANSICOES_PERMITIDAS.get(atual, set()):
            raise TransicaoInvalidaError(
                f"Transição não permitida: {atual} -> {novo_status}"
            )
        self._auditor = usuario
        self._momento_auditoria = momento
        self.status = novo_status

    def assumir(self, usuario, momento=None):
        """Atribui o chamado ao técnico. Se estava 'aberto', avança automaticamente para 'em_analise'."""
        self.tecnico = usuario
        if self.status == STATUS_ABERTO:
            self.alterar_status(STATUS_EM_ANALISE, usuario, momento)

    def _resolver_auditor(self):
        return getattr(self, "_auditor", None)

    def __repr__(self):
        return f"<Chamado {self.protocolo} [{self.status}]>"


class HistoricoStatus(db.Model):
    __tablename__ = "historico_status"

    id = db.Column(db.Integer, primary_key=True)
    chamado_id = db.Column(
        db.Integer, db.ForeignKey("chamados_os.id"), nullable=False, index=True
    )
    status_anterior = db.Column(db.String(25), nullable=True)
    status_novo = db.Column(db.String(25), nullable=False)
    alterado_por = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    data_mudanca = db.Column(db.DateTime, nullable=False, default=utcnow)

    chamado = db.relationship("Chamado", back_populates="historico")
    autor = db.relationship("Usuario", foreign_keys=[alterado_por])


class Comentario(db.Model):
    __tablename__ = "anexos_comentarios"

    id = db.Column(db.Integer, primary_key=True)
    chamado_id = db.Column(
        db.Integer, db.ForeignKey("chamados_os.id"), nullable=False, index=True
    )
    autor_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    conteudo = db.Column(db.Text, nullable=False)
    visibilidade_interna = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    chamado = db.relationship("Chamado", back_populates="comentarios")
    autor = db.relationship("Usuario", foreign_keys=[autor_id])


# ---------------------------------------------------------------------------
# Auditoria automática de status
# ---------------------------------------------------------------------------

@event.listens_for(Session, "before_flush")
def _registrar_historico_status(session, flush_context, instances):
    """Grava um HistoricoStatus sempre que o status de um chamado muda."""
    for obj in list(session.new):
        if isinstance(obj, Chamado):
            if obj.status is None:
                obj.status = STATUS_ABERTO
            auditor = obj._resolver_auditor() or _auditor_padrao(session, obj)
            session.add(
                HistoricoStatus(
                    chamado=obj,
                    status_anterior=None,
                    status_novo=obj.status,
                    alterado_por=auditor.id,
                    data_mudanca=obj.created_at or utcnow(),
                )
            )

    for obj in list(session.dirty):
        if not isinstance(obj, Chamado):
            continue
        historico = inspect(obj).attrs.status.history
        if not historico.has_changes() or not historico.deleted:
            continue
        anterior = historico.deleted[0]
        novo = obj.status
        auditor = obj._resolver_auditor()
        if auditor is None:
            raise RuntimeError(
                "Mudança de status sem auditor. Use Chamado.alterar_status()."
            )
        momento = getattr(obj, "_momento_auditoria", None) or utcnow()
        session.add(
            HistoricoStatus(
                chamado=obj,
                status_anterior=anterior,
                status_novo=novo,
                alterado_por=auditor.id,
                data_mudanca=momento,
            )
        )
        obj.updated_at = momento
        obj._auditor = None
        obj._momento_auditoria = None


def _auditor_padrao(session, obj):
    """Usuário que criou o chamado (cliente), usado quando não há auditor explícito."""
    return obj.cliente


@event.listens_for(Chamado, "after_insert")
def _gerar_protocolo(mapper, connection, target):
    """Gera o protocolo #OS-AAAA-NNNN a partir do id global, após o insert."""
    ano = (target.created_at or utcnow()).year
    protocolo = f"#OS-{ano}-{target.id:04d}"
    connection.execute(
        Chamado.__table__.update()
        .where(Chamado.__table__.c.id == target.id)
        .values(protocolo=protocolo)
    )
    target.protocolo = protocolo
