import threading
import time
from pathlib import Path

from ansi2html import Ansi2HTMLConverter
from configs_registry import ConfigRegistry
from flask import (
    Blueprint,
    Response,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)

runner = Blueprint("runner", __name__)

CONFIG_DIR = Path("configs").resolve()
OUTPUT_DIR = Path("output").resolve()
config_registry = ConfigRegistry()
outputs = {}  # filename: {'lines': [], 'prompt': None, 'awaiting': False, 'lock': threading.Lock()}


@runner.route("/start/<filename>", methods=['POST'])
def start(filename: str) -> Response:
    runner = config_registry.get_config_runner(filename)
    if filename not in outputs:
        outputs[filename] = {
            "lines": [],
            "prompt": None,
            "awaiting": False,
            "lock": threading.Lock(),
        }
    if runner.status in ["idle", "finished"]:
        if runner.status == "finished":
            runner.stop()  # Reset to idle
        # Clear previous output for new run
        with outputs[filename]["lock"]:
            outputs[filename]["lines"] = []
            outputs[filename]["prompt"] = None
            outputs[filename]["awaiting"] = False
        runner.start()

        def collector():
            """Verzamelt uitvoerregels van de GenesisRunner en detecteert prompts.
            # ... (bestaande collector-code)
            """
            for line in runner.stream_output():
                with outputs[filename]["lock"]:
                    outputs[filename]["lines"].append(line)
                    if all(["(j/n)" in line.lower(), "?" in line]):
                        outputs[filename]["prompt"] = line.strip()
                        outputs[filename]["awaiting"] = True
                    if "Afgerond" in line:
                        pass  # Finished handled by status
            # After stream ends, ensure status updates

        threading.Thread(target=collector, daemon=True).start()

        # Redirect naar de output-pagina
        return redirect(url_for('runner.show_output', filename=filename))
    else:
        # Optioneel: redirect ook hier
        return redirect(url_for('runner.show_output', filename=filename)), 400  # Of behoud jsonify als je wilt


@runner.route("/show-output/<filename>")
def show_output(filename):
    return render_template("runner.html", config=filename)


@runner.route("/stream/<filename>")
def stream(filename: str = None) -> Response:  # Default None for empty
    """Streamt de uitvoer van de GenesisRunner voor het opgegeven configuratiebestand als server-sent events.

    Zet nieuwe uitvoerregels om naar HTML en stuurt deze in realtime naar de client. Sluit de stream af wanneer de runner klaar is.

    Args:
        filename: De naam van het configuratiebestand waarvan de uitvoer wordt gestreamd.

    Returns:
        Response: Een Flask Response-object dat server-sent events streamt.
    """

    def generate():
        """Genereert server-sent events voor de uitvoer van een GenesisRunner-configuratie.

        Streamt nieuwe uitvoerregels in HTML-formaat naar de client totdat de runner is afgerond.

        Yields:
            str: Server-sent event data met de uitvoerregel of een eindmelding.
        """
        if filename not in outputs:
            yield "data: No output\n\n"
            return
        last_sent = 0
        conv = Ansi2HTMLConverter(inline=True)
        while True:
            with outputs[filename]["lock"]:
                current_lines = outputs[filename]["lines"]
                for line in current_lines[last_sent:]:
                    html_line = conv.convert(line, full=False).rstrip()
                    yield f"data: {html_line}\n\n"
                last_sent = len(current_lines)
                runner = config_registry.get_config_runner(filename)
            if runner.status == "finished":
                yield "data: [END]\n\n"
                break
            time.sleep(0.5)

    return Response(generate(), mimetype="text/event-stream")


@runner.route("/status")
def get_status():
    """Geeft de huidige status en eventuele prompts van alle GenesisRunner-configuraties terug.

    Bepaalt voor elk configuratiebestand de status en of er op invoer wordt gewacht.
    Retourneert een JSON-object met de status en prompt per configuratie.

    Returns:
        Response: Een Flask JSON-respons met de status en prompt van elke configuratie.
    """
    status_dict = {}
    for filename in config_registry.configs:
        runner = config_registry.get_config_runner(filename)
        stat = runner.status
        awaiting = False
        prompt = None
        if filename in outputs:
            with outputs[filename]["lock"]:
                awaiting = outputs[filename]["awaiting"]
                prompt = outputs[filename]["prompt"]
        if awaiting:
            stat = "awaiting_input"
        status_dict[filename] = {"status": stat, "prompt": prompt}
    return jsonify(status_dict)


@runner.route("/input/<filename>", methods=["POST"])
def send_input(filename):
    """Stuurt gebruikersinvoer naar de GenesisRunner voor het opgegeven configuratiebestand.

    Ontvangt een antwoord van de client en levert dit aan de runner.
    Zet de promptstatus terug en geeft een bevestiging terug.

    Args:
        filename: De naam van het configuratiebestand waarvoor invoer wordt verzonden.

    Returns:
        Response: Een Flask JSON-respons die bevestigt dat de invoer is verzonden.
    """
    answer = request.json.get("answer")
    runner = config_registry.get_config_runner(filename)
    runner.send_input(answer)
    with outputs[filename]["lock"]:
        outputs[filename]["awaiting"] = False
        outputs[filename]["prompt"] = None
    return jsonify({"status": "sent"})
