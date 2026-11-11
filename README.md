# Help Desk B2B com Dashboard Analítico

![Python](https://img.shields.io/badge/Python-3.14-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.1-000000?logo=flask&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-3-003B57?logo=sqlite&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-D71F00)
![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-CDN-06B6D4?logo=tailwindcss&logoColor=white)
![Chart.js](https://img.shields.io/badge/Chart.js-4.4-FF6384?logo=chartdotjs&logoColor=white)
![Tests](https://img.shields.io/badge/testes-unittest-success)

Sistema de gestão de Ordens de Serviço (OS) para equipes de suporte B2B, com controle de acesso por perfil (RBAC), trilha de auditoria completa das mudanças de status, dashboard analítico e exportação de dados.

---

## Screenshots e GIFs

<!-- Substitua os blocos abaixo pelas imagens reais, por exemplo: docs/screenshots/login.png -->

| Login (Acesso rápido demo) | Dashboard analítico | Ordem de Serviço (impressão) |
|:---:|:---:|:---:|
| `![Login](docs/screenshots/login.png)` | `![Dashboard](docs/screenshots/dashboard.png)` | `![OS](docs/screenshots/os.png)` |

---

## O problema de negócio

Empresas que prestam suporte técnico a clientes corporativos (B2B) costumam tratar chamados por e-mail, planilhas ou mensagens instantâneas. Isso gera:

- **Falta de rastreabilidade:** não se sabe quem mudou o status de um chamado, nem quando.
- **Visibilidade desigual:** clientes enxergam chamados de outras empresas, ou nada.
- **Decisões no escuro:** gestores não sabem o volume por prioridade, gargalos ou chamados críticos em aberto.
- **Retrabalho documental:** relatórios e OS impressas são montados manualmente.

Este projeto resolve esses pontos com uma fila de chamados, perfis de acesso bem definidos, histórico automático de auditoria, dashboard com indicadores e exportação em CSV e PDF.

---

## Funcionalidades

- **Autenticação segura:** senhas armazenadas apenas como hash (Werkzeug), sessão no servidor e proteção CSRF nos formulários.
- **RBAC com três perfis:** `admin`, `tecnico` e `cliente`, aplicados por decoradores nas rotas e também na consulta aos dados.
- **Ciclo de vida da OS:** abertura, assunção pelo técnico, mudanças de status validadas e comentários.
- **Auditoria automática:** toda mudança de status grava um registro em `historico_status`, sem depender da rota que a executou.
- **Dashboard analítico:** KPIs (total, em andamento, concluídos, críticos) e gráficos Chart.js alimentados por agregações SQL.
- **Exportação CSV:** arquivo com BOM UTF-8 e separador `;`, aberto corretamente no Excel em português.
- **Impressão / PDF da OS:** página limpa para `Ctrl+P` ou "Salvar como PDF", com histórico de status e somente comentários públicos.
- **Gestão de usuários (admin):** listagem, criação de contas e alteração de perfil, com bloqueio de auto-rebaixamento.

---

## Arquitetura

### Perfis e permissões (RBAC)

| Ação | `cliente` | `tecnico` | `admin` |
|---|:---:|:---:|:---:|
| Abrir chamado | ✅ (próprio) | ✅ | ✅ |
| Ver chamados | Somente os próprios | Todos | Todos |
| Assumir chamado | ❌ | ✅ | ✅ |
| Alterar status | ❌ | ✅ | ✅ |
| Comentário público | ✅ | ✅ | ✅ |
| Nota interna | ❌ | ✅ | ✅ |
| Dashboard analítico | ❌ | ✅ | ✅ |
| Exportar CSV | ❌ | ✅ | ✅ |
| Gestão de usuários | ❌ | ❌ | ✅ |

Chamados de outro cliente retornam **404** (e não 403), para não revelar a existência do recurso.

### Máquina de estados e auditoria

| De | Para |
|---|---|
| `aberto` | `em_analise`, `cancelado` |
| `em_analise` | `em_execucao`, `cancelado` |
| `em_execucao` | `aguardando_validacao`, `em_analise` |
| `aguardando_validacao` | `concluido`, `em_execucao` |
| `concluido`, `cancelado` | terminais (sem saída) |

- Transições fora dessa tabela são bloqueadas no modelo (`TRANSICOES_PERMITIDAS` em [models.py](helpdesk/models.py)) e geram `TransicaoInvalidaError`.
- Um **listener SQLAlchemy** (`before_flush`) grava automaticamente um registro em `historico_status` sempre que `status` muda, independentemente da rota que fez a alteração.
- Ao **assumir** um chamado `aberto`, o sistema move para `em_analise` e registra a transição com o técnico responsável.

### Impressão da OS

A rota `/chamados/<id>/imprimir` renderiza uma página independente do layout principal. Ela mostra os dados da OS, a linha do tempo de status e **somente comentários públicos**. Notas internas são filtradas no servidor, então nunca chegam ao HTML, independentemente do perfil de quem imprime.

---

## Estrutura de diretórios

```
Dashboard corporativo/
├── app.py                      # Ponto de entrada (cria o app e sobe o servidor)
├── config.py                   # Configurações por ambiente (development, testing, production)
├── requirements.txt            # Dependências pinadas
├── .env.example                # Modelo de variáveis de ambiente
├── helpdesk/
│   ├── __init__.py             # Fábrica create_app(): registra blueprints e o seed
│   ├── extensions.py           # Instâncias de db (SQLAlchemy) e csrf
│   ├── models.py               # Entidades, máquina de estados e listener de auditoria
│   ├── services.py             # Regras de consulta: KPIs, agregações e exportação CSV
│   ├── security.py             # Decoradores login_required e role_required (RBAC)
│   ├── seed.py                 # Dados de demonstração (usuários e 10 chamados)
│   ├── ui.py                   # Rótulos, cores de badges e listas de domínio
│   ├── blueprints/
│   │   ├── auth.py             # Login e logout
│   │   ├── main.py             # Painel (dashboard)
│   │   ├── chamados.py         # CRUD, status, assumir, comentários, CSV e impressão
│   │   └── usuarios.py         # Gestão de usuários (somente admin)
│   ├── templates/              # Jinja2 + Tailwind (CDN)
│   │   ├── base.html
│   │   ├── login.html
│   │   ├── painel.html
│   │   ├── chamados/           # lista, novo, detalhe, imprimir
│   │   └── admin/usuarios.html
│   └── static/js/
│       ├── dashboard.js        # Gráficos Chart.js
│       └── glyph-background.js # Fundo animado da tela de login
├── tests/
│   └── test_smoke.py           # Testes de RBAC, auditoria e regras de negócio
└── instance/                   # Banco SQLite local (gerado; ignorado pelo Git)
```

---

## Como executar localmente

**Pré-requisitos:** Python 3.9 ou superior (testado com 3.14) e Git.

```powershell
# 1. Clone o repositório
git clone https://github.com/SEU-USUARIO/helpdesk-b2b.git
cd helpdesk-b2b

# 2. Crie e ative o ambiente virtual
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux / macOS

# 3. Instale as dependências
pip install -r requirements.txt

# 4. (Opcional) Configure as variáveis de ambiente
copy .env.example .env          # Windows
# cp .env.example .env          # Linux / macOS

# 5. Rode o servidor de desenvolvimento
python app.py
```

Acesse **http://127.0.0.1:5000**.

Na primeira execução, o banco `instance/helpdesk.db` é criado e populado automaticamente com usuários e chamados de demonstração. O seed só roda quando a tabela de usuários está vazia.

Para rodar os testes automatizados:

```powershell
python -m unittest -v
```

### Variáveis de ambiente

| Variável | Padrão | Descrição |
|---|---|---|
| `FLASK_CONFIG` | `development` | `development`, `testing` ou `production` |
| `SECRET_KEY` | chave de desenvolvimento | Obrigatória em produção |
| `DATABASE_URL` | `instance/helpdesk.db` | URI do SQLAlchemy |
| `SEED_SENHA_PADRAO` | `Demo@2026` | Senha das contas de demonstração |

---

## Credenciais de demonstração

Todas as contas usam a senha **`Demo@2026`**. Na tela de login, os botões **Acesso Rápido** preenchem o formulário automaticamente.

| Perfil | E-mail | Nome | Pode |
|---|---|---|---|
| `admin` | `admin@helpdesk.local` | Ana Administradora | Tudo, incluindo gestão de usuários |
| `tecnico` | `carlos.tecnico@helpdesk.local` | Carlos Técnico | Fila completa, status, notas internas |
| `tecnico` | `mariana.suporte@helpdesk.local` | Mariana Suporte | Mesmo acesso do técnico acima |
| `cliente` | `ti@alfa.example.com` | TI Alfa Ltda | Abrir e acompanhar os próprios chamados |
| `cliente` | `suporte@beta.example.com` | Suporte Beta S.A. | Abrir e acompanhar os próprios chamados |

---

## Decisões técnicas

- **Protocolo sem colisão:** o formato `#OS-AAAA-NNNN` usa o `id` global com `zfill(4)`, então não depende de contadores separados nem de sequências no SQLite.
- **Auditoria no modelo, não na rota:** o listener garante que nenhuma rota futura consiga mudar status sem gravar histórico.
- **Sem ORM de consulta espalhado:** agregações do dashboard ficam em `services.py`, e as rotas apenas orquestram.
- **Testes sem dependências extras:** a suíte usa `unittest` da biblioteca padrão e roda contra SQLite em memória, com a configuração `testing` (CSRF desligado apenas nesse ambiente).

---

## Roadmap

- Notificações por e-mail a cada mudança de status
- SLA com prazo por prioridade e alertas de estouro
- Anexos nos chamados e comentários
- Migrações de esquema com Flask-Migrate (Alembic)

---

## Autor

Desenvolvido por **RYUKO**. Projeto de portfólio.
