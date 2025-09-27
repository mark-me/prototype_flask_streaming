from pathlib import Path

from ansi2html import Ansi2HTMLConverter
from flask import (
    Blueprint,
    Response,
    render_template,
    request,
)
from .genesis_runner import GenesisRunner

runner = Blueprint("runner", __name__)

CONFIG_DIR = Path("configs").resolve()
OUTPUT_DIR = Path("output").resolve()

genesis_runner = GenesisRunner()


@runner.route("/run/<filename>")
def config_run(filename: str) -> Response:
    """Start een GenesisRunner-proces met het opgegeven configuratiebestand en toont de uitvoerpagina.

    Deze functie start het uitvoerproces voor de geselecteerde configuratie en rendert de bijbehorende pagina.

    Args:
        config (str): De naam van het configuratiebestand.

    Returns:
        Response: Een HTML-pagina die de uitvoer van het proces toont.
    """
    config_file_path = CONFIG_DIR / filename
    if not config_file_path.exists():
        error_message = f"Configuratiebestand '{filename}' niet gevonden."
        return render_template("error.html", message=error_message), 404
    if not genesis_runner.is_running():
        try:
            genesis_runner.start(path_config=config_file_path)
        except Exception as e:
            error_message = f"Fout bij het starten van de runner: {str(e)}"
            return render_template("error.html", message=error_message), 500
    return render_template("run.html", config=filename)


@runner.route("/stream")
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
            for line in genesis_runner.stream_output():
                html_line = conv.convert(line, full=False).rstrip()
                yield f"data: {html_line}\n\n"
                if "doorgaan" in html_line or "antwoorden" in html_line:
                    yield "data: asking_question\n\n"
                elif "Afgerond" in html_line:
                    yield "data: finished\n\n"
        except (BrokenPipeError, ConnectionResetError):
            return
        except Exception as e:
            yield "data: [ERROR] Er is een interne fout opgetreden tijdens het streamen.\n\n"

    return Response(generate(), mimetype="text/event-stream")


@runner.route("/input", methods=["POST"])
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
        genesis_runner.send_input(value)
    except Exception as e:
        return {"status": "error", "message": f"Failed to send input: {str(e)}"}, 500
    return {"status": "ok"}
