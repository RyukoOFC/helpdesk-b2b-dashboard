from dotenv import load_dotenv

# Precisa rodar antes de importar config/helpdesk, pois as configs leem variáveis de ambiente.
load_dotenv()

from helpdesk import create_app  # noqa: E402

app = create_app()

if __name__ == "__main__":
    app.run(debug=app.config["DEBUG"])
