from pathlib import Path
from ansi2html import Ansi2HTMLConverter
from flask import Blueprint, Response, jsonify, render_template, request

from configs_registry import ConfigRegistry

runner = Blueprint("runner", __name__)

CONFIG_DIR = Path("configs").resolve()
OUTPUT_DIR = Path("output").resolve()
config_registry = ConfigRegistry()


@runner.route("/run/<filename>")
def config_run(filename: str) -> Response:
    """Start een GenesisRunner-proces voor een opgegeven configuratiebestand."""
    runner_instance = config_registry.get_config_runner(filename)

    if runner_instance.is_running():
        error_message = f"Configuratiebestand '{filename}' draait al."
        return render_template("error.html", message=error_message), 400

    try:
        runner_instance.start()
    except Exception as e:
        error_message = f"Fout bij het starten van de runner: {str(e)}"
        return render_template("error.html", message=error_message), 500

    return render_template("runner.html", config=filename)


@runner.route("/stream/<filename>")
@runner.route("/stream/")  # New: Handles /stream/ (empty)
def stream(filename: str = None) -> Response:  # Default None for empty
    """Streamt de uitvoer van de GenesisRunner naar de client als Server-Sent Events."""

    def generate():
        conv = Ansi2HTMLConverter(inline=True)
        # If filename None, stream all (global); else per-config
        runners_to_watch = (
            [config_registry.get_config_runner(filename=filename)]
            if filename
            else [config["runner"] for config in config_registry.get_configs()]
        )

        try:
            while any(r.is_running() for r in runners_to_watch):  # Loop until all done
                for runner in runners_to_watch:
                    if runner.is_running():
                        for line in runner.stream_output():
                            html_line = conv.convert(line, full=False).rstrip()
                            yield f"data: {html_line}\n\n"

                            if "doorgaan" in html_line or "antwoorden" in html_line:
                                yield f"data: waiting_input|{runner.path_config.name}\n\n"  # Include filename
                            elif "Afgerond" in html_line:
                                yield f"data: finished|{runner.path_config.name}\n\n"
                # Heartbeat if quiet
                yield ": heartbeat\n\n"
        except GeneratorExit:
            pass  # Client disconnect
        except Exception as e:
            yield f"data: [ERROR] {str(e)}\n\n"

    return Response(generate(), mimetype="text/event-stream")


@runner.route("/statuses", methods=["GET"])
def statuses():
    statuses = []
    for idx, (filename, config) in enumerate(config_registry.items(), 1):
        runner_instance = config["runner"]
        status = runner_instance.status()
        statuses.append({"rowId": idx, "status": status})
    return jsonify(statuses)


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


@runner.route("/send_input", methods=["POST"])
def send_input():
    data = request.get_json()
    filename = data.get("filename")
    answer = data.get("answer", "")

    if not filename or not answer:
        return jsonify(
            {"status": "error", "message": "Missing filename or answer."}
        ), 400

    runner_instance = config_registry.get_config_runner(filename)

    if (
        runner_instance.is_running()
        and runner_instance.process
        and runner_instance.process.stdin
    ):
        try:
            runner_instance.process.stdin.write((answer + "\n").encode("utf-8"))
            runner_instance.process.stdin.flush()
            return jsonify({"status": "ok"})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500
    else:
        return jsonify({"status": "error", "message": "Geen actief proces."}), 400
