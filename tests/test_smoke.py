"""Testes automatizados: RBAC, máquina de estados com auditoria e regras de negócio.

Executar a partir da raiz do projeto:
    python -m unittest -v
"""

import unittest

from helpdesk import create_app
from helpdesk.extensions import db
from helpdesk.models import (
    STATUS_ABERTO,
    STATUS_EM_ANALISE,
    STATUS_EM_EXECUCAO,
    Chamado,
    Comentario,
    HistoricoStatus,
    Usuario,
)
from helpdesk.seed import popular_banco_inicial

SENHA = "Demo@2026"
EMAIL_ADMIN = "admin@helpdesk.local"
EMAIL_TECNICO = "carlos.tecnico@helpdesk.local"
EMAIL_CLIENTE = "ti@alfa.example.com"
EMAIL_CLIENTE_OUTRO = "suporte@beta.example.com"
BOM_UTF8 = b"\xef\xbb\xbf"


class HelpdeskTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.ctx = self.app.app_context()
        self.ctx.push()
        popular_banco_inicial(SENHA)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def login(self, email):
        cliente_http = self.app.test_client()
        resposta = cliente_http.post("/login", data={"email": email, "senha": SENHA})
        self.assertEqual(resposta.status_code, 302, "login deveria redirecionar")
        return cliente_http

    @staticmethod
    def usuario(email):
        return Usuario.query.filter_by(email=email).one()

    def criar_chamado(self, email_cliente=EMAIL_CLIENTE, titulo="Chamado de teste"):
        chamado = Chamado(
            titulo=titulo,
            descricao="Descrição de teste.",
            categoria="Hardware",
            prioridade="alta",
            cliente=self.usuario(email_cliente),
        )
        db.session.add(chamado)
        db.session.commit()
        return chamado.id

    @staticmethod
    def recarregar(modelo, identificador):
        db.session.expire_all()
        return db.session.get(modelo, identificador)


class SeedTests(HelpdeskTestCase):
    def test_seed_cria_cinco_usuarios_e_dez_chamados(self):
        self.assertEqual(Usuario.query.count(), 5)
        self.assertEqual(Chamado.query.count(), 10)

    def test_seed_e_idempotente(self):
        self.assertFalse(popular_banco_inicial(SENHA))
        self.assertEqual(Usuario.query.count(), 5)

    def test_protocolo_segue_formato_os_ano_id(self):
        for chamado in Chamado.query.all():
            self.assertRegex(chamado.protocolo, r"^#OS-\d{4}-\d{4}$")

    def test_senhas_sao_armazenadas_como_hash(self):
        admin = self.usuario(EMAIL_ADMIN)
        self.assertNotEqual(admin.senha_hash, SENHA)
        self.assertTrue(admin.verificar_senha(SENHA))


class RBACTests(HelpdeskTestCase):
    def test_rota_protegida_sem_login_redireciona(self):
        resposta = self.app.test_client().get("/painel")
        self.assertEqual(resposta.status_code, 302)
        self.assertIn("/login", resposta.headers["Location"])

    def test_cliente_nao_exporta_csv(self):
        resposta = self.login(EMAIL_CLIENTE).get("/chamados/exportar.csv")
        self.assertEqual(resposta.status_code, 403)

    def test_tecnico_exporta_csv_com_bom_utf8(self):
        resposta = self.login(EMAIL_TECNICO).get("/chamados/exportar.csv")
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.mimetype, "text/csv")
        self.assertTrue(resposta.data.startswith(BOM_UTF8))

    def test_cliente_nao_acessa_gestao_de_usuarios(self):
        resposta = self.login(EMAIL_CLIENTE).get("/admin/usuarios/")
        self.assertEqual(resposta.status_code, 403)

    def test_tecnico_nao_acessa_gestao_de_usuarios(self):
        resposta = self.login(EMAIL_TECNICO).get("/admin/usuarios/")
        self.assertEqual(resposta.status_code, 403)

    def test_admin_acessa_gestao_de_usuarios(self):
        resposta = self.login(EMAIL_ADMIN).get("/admin/usuarios/")
        self.assertEqual(resposta.status_code, 200)

    def test_cliente_nao_ve_chamado_de_outro_cliente(self):
        id_outro = self.criar_chamado(EMAIL_CLIENTE_OUTRO, "Chamado do outro cliente")
        resposta = self.login(EMAIL_CLIENTE).get(f"/chamados/{id_outro}")
        self.assertEqual(resposta.status_code, 404)

    def test_cliente_ve_o_proprio_chamado(self):
        id_proprio = self.criar_chamado(EMAIL_CLIENTE, "Meu chamado")
        resposta = self.login(EMAIL_CLIENTE).get(f"/chamados/{id_proprio}")
        self.assertEqual(resposta.status_code, 200)

    def test_cliente_nao_altera_status(self):
        id_chamado = self.criar_chamado(EMAIL_CLIENTE)
        self.login(EMAIL_CLIENTE).post(
            f"/chamados/{id_chamado}/status", data={"status": STATUS_EM_ANALISE}
        )
        chamado = self.recarregar(Chamado, id_chamado)
        self.assertEqual(chamado.status, STATUS_ABERTO)

    def test_admin_recebe_pagina_do_painel(self):
        resposta = self.login(EMAIL_ADMIN).get("/painel")
        self.assertEqual(resposta.status_code, 200)

    def test_admin_redireciona_para_gestao_de_usuarios(self):
        resposta = self.login(EMAIL_ADMIN).get("/admin")
        self.assertEqual(resposta.status_code, 302)
        self.assertIn("/admin/usuarios", resposta.headers["Location"])


class MaquinaDeEstadosTests(HelpdeskTestCase):
    def test_assumir_chamado_aberto_muda_para_em_analise_e_grava_historico(self):
        id_chamado = self.criar_chamado()
        tecnico = self.usuario(EMAIL_TECNICO)

        self.login(EMAIL_TECNICO).post(f"/chamados/{id_chamado}/assumir")

        chamado = self.recarregar(Chamado, id_chamado)
        self.assertEqual(chamado.status, STATUS_EM_ANALISE)
        self.assertEqual(chamado.tecnico_id, tecnico.id)

        transicao = HistoricoStatus.query.filter_by(
            chamado_id=id_chamado, status_novo=STATUS_EM_ANALISE
        ).one()
        self.assertEqual(transicao.status_anterior, STATUS_ABERTO)

    def test_mudanca_de_status_gera_historico_automatico(self):
        id_chamado = self.criar_chamado()
        http = self.login(EMAIL_TECNICO)
        http.post(f"/chamados/{id_chamado}/assumir")
        http.post(f"/chamados/{id_chamado}/status", data={"status": STATUS_EM_EXECUCAO})

        chamado = self.recarregar(Chamado, id_chamado)
        self.assertEqual(chamado.status, STATUS_EM_EXECUCAO)
        # Registro de criação (None -> aberto) + assumir + execução
        self.assertEqual(HistoricoStatus.query.filter_by(chamado_id=id_chamado).count(), 3)

    def test_transicao_invalida_e_bloqueada(self):
        id_chamado = self.criar_chamado()
        self.login(EMAIL_TECNICO).post(
            f"/chamados/{id_chamado}/status", data={"status": "concluido"}
        )
        chamado = self.recarregar(Chamado, id_chamado)
        self.assertEqual(chamado.status, STATUS_ABERTO)
        # Apenas o registro de criação deve existir
        self.assertEqual(HistoricoStatus.query.filter_by(chamado_id=id_chamado).count(), 1)


class ComentariosTests(HelpdeskTestCase):
    def test_nota_interna_nao_aparece_na_impressao(self):
        id_chamado = self.criar_chamado()
        chamado = self.recarregar(Chamado, id_chamado)
        autor = self.usuario(EMAIL_TECNICO)
        db.session.add(
            Comentario(
                chamado=chamado,
                autor=autor,
                conteudo="SEGREDO-INTERNO-123",
                visibilidade_interna=True,
            )
        )
        db.session.add(
            Comentario(
                chamado=chamado,
                autor=autor,
                conteudo="RESPOSTA-PUBLICA-456",
                visibilidade_interna=False,
            )
        )
        db.session.commit()

        resposta = self.login(EMAIL_TECNICO).get(f"/chamados/{id_chamado}/imprimir")
        corpo = resposta.get_data(as_text=True)
        self.assertEqual(resposta.status_code, 200)
        self.assertNotIn("SEGREDO-INTERNO-123", corpo)
        self.assertIn("RESPOSTA-PUBLICA-456", corpo)

    def test_cliente_nao_consegue_criar_nota_interna(self):
        id_chamado = self.criar_chamado(EMAIL_CLIENTE)
        self.login(EMAIL_CLIENTE).post(
            f"/chamados/{id_chamado}/comentarios",
            data={"conteudo": "Tentativa de nota", "visibilidade_interna": "on"},
        )
        comentario = Comentario.query.filter_by(chamado_id=id_chamado).one()
        self.assertFalse(comentario.visibilidade_interna)


class GestaoDeUsuariosTests(HelpdeskTestCase):
    def test_admin_cria_novo_usuario(self):
        self.login(EMAIL_ADMIN).post(
            "/admin/usuarios/",
            data={
                "nome": "Novo Tecnico",
                "email": "novo.tecnico@helpdesk.local",
                "role": "tecnico",
                "senha": "SenhaForte123",
            },
        )
        novo = Usuario.query.filter_by(email="novo.tecnico@helpdesk.local").one()
        self.assertEqual(novo.role, "tecnico")
        self.assertTrue(novo.verificar_senha("SenhaForte123"))

    def test_email_duplicado_retorna_422(self):
        resposta = self.login(EMAIL_ADMIN).post(
            "/admin/usuarios/",
            data={
                "nome": "Duplicado",
                "email": EMAIL_TECNICO,
                "role": "cliente",
                "senha": "SenhaForte123",
            },
        )
        self.assertEqual(resposta.status_code, 422)

    def test_senha_curta_e_rejeitada(self):
        resposta = self.login(EMAIL_ADMIN).post(
            "/admin/usuarios/",
            data={
                "nome": "Senha Curta",
                "email": "curta@helpdesk.local",
                "role": "cliente",
                "senha": "123",
            },
        )
        self.assertEqual(resposta.status_code, 422)
        self.assertIsNone(Usuario.query.filter_by(email="curta@helpdesk.local").first())

    def test_admin_nao_altera_o_proprio_perfil(self):
        admin = self.usuario(EMAIL_ADMIN)
        self.login(EMAIL_ADMIN).post(
            f"/admin/usuarios/{admin.id}/papel", data={"role": "cliente"}
        )
        self.assertEqual(self.recarregar(Usuario, admin.id).role, "admin")

    def test_admin_altera_papel_de_outro_usuario(self):
        cliente = self.usuario(EMAIL_CLIENTE)
        self.login(EMAIL_ADMIN).post(
            f"/admin/usuarios/{cliente.id}/papel", data={"role": "tecnico"}
        )
        self.assertEqual(self.recarregar(Usuario, cliente.id).role, "tecnico")


if __name__ == "__main__":
    unittest.main()
