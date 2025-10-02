from pathlib import Path
from ansi2html import Ansi2HTMLConverter
from flask import (
    Blueprint,
    Response,
    jsonify,
    render_template,
    request
)

from configs_registry import ConfigRegistry

runner = Blueprint("runner", __name__)

CONFIG_DIR = Path("configs").resolve()
OUTPUT_DIR = Path("output").resolve()
config_registry = ConfigRegistry()

@runner.route("/run/<filename>")
def config_run(filename: str) -> Response:
    """Start een GenesisRunner-proces voor een opgegeven configuratiebestand."""
    config = config_registry.get(filename)
    runner = config["runner"]

    if runner.is_running():
        # Als het proces al draait, geef een foutmelding terug
        error_message = f"Configuratiebestand '{filename}' draait al."
        return render_template("error.html", message=error_message), 400

    try:
        runner.start()
    except Exception as e:
        error_message = f"Fout bij het starten van de runner: {str(e)}"
        return render_template("error.html", message=error_message), 500

    return render_template("runner.html", config=filename)


@runner.route("/stream/<filename>")
def stream(filename: str) -> Response:
    """Streamt de uitvoer van de GenesisRunner naar de client als Server-Sent Events."""
    def generate():
        config = config_registry.get(filename)
        runner = config["runner"]
        conv = Ansi2HTMLConverter(inline=True)
        try:
            for line in runner.stream_output():
                html_line = conv.convert(line, full=False).rstrip()
                yield f"data: {html_line}\n\n"

                if "doorgaan" in html_line or "antwoorden" in html_line:
                    yield "data: asking_question\n\n"  # Indicate that user input is required
                elif "Afgerond" in html_line:
                    yield "data: finished\n\n"

        except (BrokenPipeError, ConnectionResetError):
            return
        except Exception:
            yield "data: [ERROR] Er is een interne fout opgetreden tijdens het streamen.\n\n"

    return Response(generate(), mimetype="text/event-stream")

# @runner.route("/check_running_status", methods=["POST"])
# def check_running_status() -> Response:
#     """Controleert of een opgegeven configuratie momenteel actief is.

#     Ontvangt de bestandsnaam van de client en retourneert of deze configuratie als 'running' is gemarkeerd.

#     Returns:
#         Response: Een JSON-object met de sleutel 'is_running' die aangeeft of de configuratie actief is.
#     """
#     data = request.get_json()
#     filename = data.get("filename")
#     is_running = running_configs.get(filename) == "running"
#     return jsonify({"is_running": is_running})


# @runner.route("/status/all", methods=["GET"])
# def status_all() -> Response:
#     """Geeft een overzicht van de status van alle bekende configuraties.

#     Retourneert een JSON-object met de status van alle momenteel bekende configuratiebestanden.

#     Returns:
#         Response: Een JSON-object met de status van alle configuraties.
#     """
#     return jsonify(running_configs)


@runner.route("/input/<filename>", methods=["POST"])
def input(filename: str) -> Response:
    """Ontvangt invoer van de client en stuurt deze door naar de GenesisRunner."""
    value = request.json.get("value")
    if value is None or not isinstance(value, str) or not value.strip():
        return jsonify({"status": "error", "message": "Invalid or missing input value."}), 400

    config = config_registry.get(filename)
    runner = config["runner"]
    try:
        runner.send_input(value)
    except Exception as e:
        return jsonify({"status": "error", "message": f"Failed to send input: {str(e)}"}), 500

    return jsonify({"status": "ok"})


@runner.route("/send_input", methods=["POST"])
def send_input():
    data = request.get_json()
    filename = data.get("filename")
    answer = data.get("answer", "")

    config = config_registry.get(filename)
    runner = config["runner"]

    if runner.process and runner.process.stdin:
        try:
            runner.process.stdin.write((answer + "\n").encode("utf-8"))
            runner.process.stdin.flush()
            return jsonify({"status": "ok"})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500
    else:
        return jsonify({"status": "error", "message": "Geen actief proces"}), 400

