from pathlib import Path
from ansi2html import Ansi2HTMLConverter
from flask import (
    Blueprint,
    Response,
    jsonify,
    render_template,
    request
)
from .genesis_runner import GenesisRunner

runner = Blueprint("runner", __name__)

CONFIG_DIR = Path("configs").resolve()
OUTPUT_DIR = Path("output").resolve()

genesis_runner = GenesisRunner()

# Centrale in-memory status store
# voorbeeld: {"config1.yaml": "running", "config2.yaml": "finished"}
running_configs = {}


@runner.route("/run/<filename>")
def config_run(filename: str) -> Response:
    """Start een GenesisRunner-proces voor een opgegeven configuratiebestand.

    Valideert het configuratiebestand, start het proces indien nodig en markeert de status als actief. Foutmeldingen worden weergegeven als het bestand ongeldig is of het proces niet kan worden gestart.
    """
    config_file_path = (CONFIG_DIR / filename).resolve()
    # Veiligheidscheck: bestand moet binnen CONFIG_DIR liggen
    if not str(config_file_path).startswith(str(CONFIG_DIR)):
        error_message = "Ongeldig configuratiepad."
        return render_template("error.html", message=error_message), 400

    if not config_file_path.exists():
        error_message = f"Configuratiebestand '{filename}' niet gevonden."
        return render_template("error.html", message=error_message), 404

    running_configs[filename] = "running"  # Markeer als actief

    if not genesis_runner.is_running():
        try:
            genesis_runner.start(path_config=config_file_path)
        except Exception as e:
            running_configs[filename] = "error"
            error_message = f"Fout bij het starten van de runner: {str(e)}"
            return render_template("error.html", message=error_message), 500

    return render_template("run.html", config=filename)


@runner.route("/stream")
def stream() -> Response:
    """Streamt de uitvoer van de GenesisRunner naar de client als Server-Sent Events.

    Deze functie zet de uitvoer van het GenesisRunner-proces om naar HTML en stuurt deze regel voor regel naar de client.
    Speciale signalen worden verzonden als er om input wordt gevraagd of als het proces is afgerond.
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
                    # Zoek actieve config en markeer als klaar
                    for cfg, status in running_configs.items():
                        if status == "running":
                            running_configs[cfg] = "finished"
                            break
        except (BrokenPipeError, ConnectionResetError):
            return
        except Exception:
            yield "data: [ERROR] Er is een interne fout opgetreden tijdens het streamen.\n\n"

    return Response(generate(), mimetype="text/event-stream")


@runner.route("/check_running_status", methods=["POST"])
def check_running_status():
    data = request.get_json()
    filename = data.get("filename")
    is_running = running_configs.get(filename) == "running"
    return jsonify({"is_running": is_running})


@runner.route("/status/all", methods=["GET"])
def status_all():
    """Geeft een overzicht van de status van alle bekende configuraties."""
    return jsonify(running_configs)


@runner.route("/input", methods=["POST"])
def send_input() -> Response:
    """Ontvangt invoer van de client en stuurt deze door naar de GenesisRunner."""
    value = request.json.get("value")
    if value is None or not isinstance(value, str) or not value.strip():
        return jsonify({"status": "error", "message": "Invalid or missing input value."}), 400

    try:
        genesis_runner.send_input(value)
    except Exception as e:
        return jsonify({"status": "error", "message": f"Failed to send input: {str(e)}"}), 500

    return jsonify({"status": "ok"})
