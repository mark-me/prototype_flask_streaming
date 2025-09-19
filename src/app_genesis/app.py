import re
from pathlib import Path

import markdown
import yaml
from ansi2html import Ansi2HTMLConverter
from flask import (
    Flask,
    Response,
    current_app,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from genesis_runner import GenesisRunner

from logtools import get_logger

logger = get_logger(__name__)

app = Flask(__name__)
runner = GenesisRunner()

CONFIG_DIR = Path("configs")
OUTPUT_DIR = Path("output")


@app.route("/")
def index() -> Response:
    """Toont de startpagina met een lijst van beschikbare configuratiebestanden.

    Deze functie verzamelt alle configuratiebestanden en rendert de indexpagina waarop deze worden weergegeven.

    Returns:
        Response: Een HTML-pagina met een lijst van configuratiebestanden.
    """
    configs = sorted(
        [
            f.name
            for f in CONFIG_DIR.iterdir()
            if f.is_file() and f.suffix.lower() in [".yaml", ".yml"]
        ]
    )
    return render_template("index.html", configs=configs)


@app.route("/edit/<config>", methods=["GET", "POST"])
def edit_config(config: str) -> Response:
    """Biedt een pagina om een configuratiebestand te bewerken en slaat wijzigingen op.

    Deze functie toont het bewerkingsformulier voor een configuratiebestand en verwerkt eventuele wijzigingen
    die door de gebruiker zijn ingediend.

    Args:
        config (Path): De naam van het te bewerken configuratiebestand.

    Returns:
        Response: Een HTML-pagina voor het bewerken van de configuratie of een redirect na opslaan.
    """
    if request.method == "POST":
        content = request.form["content"]
        try:
            yaml.safe_load(content)
        except yaml.YAMLError as e:
            error_message = f"YAML is ongeldig: {str(e)}"
            return render_template("edit.html", config=config, content=content, error=error_message)

        with open(CONFIG_DIR / config, "w") as f:
            f.write(content)
        return redirect(url_for("index"))

    content = (CONFIG_DIR / config).read_text()
    return render_template("edit.html", config=config, content=content)


@app.route("/run/<config>")
def run_config(config: str) -> Response:
    """Start een GenesisRunner-proces met het opgegeven configuratiebestand en toont de uitvoerpagina.

    Deze functie start het uitvoerproces voor de geselecteerde configuratie en rendert de bijbehorende pagina.

    Args:
        config (str): De naam van het configuratiebestand.

    Returns:
        Response: Een HTML-pagina die de uitvoer van het proces toont.
    """
    config_file_path = CONFIG_DIR / config
    if not config_file_path.exists():
        error_message = f"Configuratiebestand '{config}' niet gevonden."
        return render_template("error.html", message=error_message), 404
    try:
        runner.start(config_path=config_file_path)
    except Exception as e:
        error_message = f"Fout bij het starten van de runner: {str(e)}"
        return render_template("error.html", message=error_message), 500
    return render_template("run.html", config=config)


@app.route("/stream")
def stream() -> Response:
    """Stuurt uitvoer van de GenesisRunner naar de client via Server-Sent Events (SSE).

    Dit endpoint biedt real-time streaming van uitvoerregels, waarbij elke regel als een apart SSE-bericht wordt verzonden.
    Als er een fout optreedt tijdens het streamen, wordt een foutmelding naar de client gestuurd.

    Returns:
        Response: Een Flask Response-object dat uitvoer streamt als text/event-stream.
    """

    def generate():
        conv = Ansi2HTMLConverter(inline=True)
        try:
            for line in runner.stream_output():
                html_line = conv.convert(line, full=False).rstrip()
                yield f"data: {html_line}\n\n"
        except (BrokenPipeError, ConnectionResetError):
            return
        except Exception as e:
            logger.exception("Exception occurred while streaming output")
            yield "data: [ERROR] Er is een interne fout opgetreden tijdens het streamen.\n\n"

    return Response(generate(), mimetype="text/event-stream")


@app.route("/input", methods=["POST"])
def send_input() -> dict:
    """Ontvangt invoer van de client en stuurt deze door naar de GenesisRunner.

    Deze functie verwerkt een POST-verzoek met invoerdata, valideert de invoer en stuurt deze naar het uitvoerproces.
    Bij een fout wordt een passende foutmelding geretourneerd.

    Returns:
        dict: Een statusbericht in JSON-formaat, met een foutcode indien van toepassing.
    """
    value = request.json.get("value")
    if value is None or not isinstance(value, str) or not value.strip():
        return {"status": "error", "message": "Invalid or missing input value."}, 400
    try:
        runner.send_input(value)
    except Exception as e:
        return {"status": "error", "message": f"Failed to send input: {str(e)}"}, 500
    return {"status": "ok"}


@app.route("/download-log")
def download_log() -> Response:
    """Maakt het mogelijk om een logbestand te downloaden als CSV-bestand.

    Deze functie valideert de bestandsnaam, controleert of het logbestand bestaat en stuurt het bestand naar de client.
    Bij een ongeldige bestandsnaam of ontbrekend bestand wordt een foutmelding geretourneerd.

    Returns:
        Response: Het CSV-bestand als download, of een foutmelding als het bestand niet geldig of niet gevonden is.
    """
    filename = request.args.get("filename", "sample.csv")
    # Allow periods in the filename (except as path separators), e.g. 'log.2024-06-01.csv'
    if not re.match(r"^[\w.\-]+\.csv$", filename):
        return "Ongeldige bestandsnaam", 400
    log_path = OUTPUT_DIR / filename
    if log_path.exists():
        return send_file(log_path, as_attachment=True)
    return "Geen log gevonden", 404


@app.route("/about")
def about():
    """Toont de 'Over'-pagina met informatie uit het Markdown-bestand.

    Deze functie leest de inhoud van 'about.md', converteert deze naar HTML en rendert de bijbehorende pagina.

    Returns:
        Response: Een HTML-pagina met informatie over de applicatie.
    """
    about_md_path = Path(current_app.static_folder) / "about.md"
    with open(about_md_path, encoding="utf-8") as f:
        content = f.read()
    html = markdown.markdown(content, extensions=["fenced_code", "tables"])
    return render_template("about.html", content=html)


if __name__ == "__main__":
    app.run(debug=True, threaded=True)
