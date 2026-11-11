"""Fábrica da aplicação Flask."""

import os

from flask import Flask, g, render_template

from config import config_by_name

from .extensions import csrf, db


def create_app(config_name=None):
    app = Flask(__name__, instance_relative_config=True)

    nome = config_name or os.getenv("FLASK_CONFIG", "development")
    app.config.from_object(config_by_name[nome])

    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    csrf.init_app(app)

    from .blueprints.auth import auth_bp
    from .blueprints.chamados import bp as chamados_bp
    from .blueprints.main import main_bp
    from .blueprints.usuarios import bp as usuarios_bp
    from .security import carregar_usuario_logado

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(chamados_bp)
    app.register_blueprint(usuarios_bp)
    app.before_request(carregar_usuario_logado)

    contas_demo = {
        "admin": "admin@helpdesk.local",
        "tecnico": "carlos.tecnico@helpdesk.local",
        "cliente": "ti@alfa.example.com",
    }

    @app.context_processor
    def injetar_usuario():
        demo = None
        if app.config.get("SEED_ENABLED"):
            demo = {"contas": contas_demo, "senha": app.config["SEED_SENHA_PADRAO"]}
        return {"usuario_atual": g.get("usuario"), "contas_demo": demo}

    @app.errorhandler(403)
    def acesso_negado(_erro):
        return render_template("erro.html", codigo=403, mensagem="Acesso negado."), 403

    with app.app_context():
        from . import models  # noqa: F401  (registra os modelos e listeners)

        db.create_all()
        if app.config.get("SEED_ENABLED"):
            from .seed import popular_banco_inicial

            popular_banco_inicial(app.config["SEED_SENHA_PADRAO"])

    return app
