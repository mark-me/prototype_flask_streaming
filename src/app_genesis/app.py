import csv
import json
import os
import re
import shutil
from pathlib import Path

import markdown
import yaml
from ansi2html import Ansi2HTMLConverter
from flask import (
    Flask,
    Response,
    abort,
    current_app,
    jsonify,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    send_from_directory,
    url_for,
)
from genesis_runner import GenesisRunner

from config import GenesisConfig
from logtools import get_logger

logger = get_logger(__name__)

app = Flask(__name__)
app.secret_key = "supersecret"
runner = GenesisRunner()

CONFIG_DIR = Path("configs").resolve()
OUTPUT_DIR = Path("output").resolve()
ROOT_DIR = Path(".").resolve()


def secure_path(path):
    full_path = ROOT_DIR / path
    if ROOT_DIR not in full_path.parents:
        abort(403)
    return full_path


@app.route("/")
def index() -> Response:
    """Toont de startpagina met een lijst van beschikbare configuratiebestanden.

    Deze functie verzamelt alle configuratiebestanden en rendert de indexpagina waarop deze worden weergegeven.

    Returns:
        Response: Een HTML-pagina met een lijst van configuratiebestanden.
    """
    paths_config = sorted(
        [
            f
            for f in CONFIG_DIR.iterdir()
            if f.is_file() and f.suffix.lower() in [".yaml", ".yml"]
        ]
    )
    configs = [
        GenesisConfig(file_config=path_config, create_version_dir=False)
        for path_config in paths_config
    ]
    files_config = [path_config.name for path_config in paths_config]
    return render_template("index.html", configs=files_config)


@app.route("/configs/edit/<filename>", methods=["GET", "POST"])
def config_edit(filename):
    """Biedt een interface om een configuratiebestand te bewerken of op te slaan.

    Deze functie verwerkt GET- en POST-verzoeken voor het bewerken, opslaan en opslaan als een nieuw configuratiebestand.
    Bij een POST-verzoek wordt het bestand opgeslagen of als nieuw bestand aangemaakt, afhankelijk van de gekozen actie.
    Bij een GET-verzoek wordt de inhoud van het geselecteerde bestand geladen en weergegeven.

    Args:
        filename (str): De naam van het te bewerken configuratiebestand.

    Returns:
        Response: Een HTML-pagina voor het bewerken van het configuratiebestand.
    """
    file_path = os.path.join(CONFIG_DIR, filename)

    if request.method == "POST":
        action = request.form.get("action")
        content = request.form.get("content")

        if action == "save":
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            flash(f"✅ Bestand '{filename}' opgeslagen.", "success")

        elif action == "save_as":
            file_name_new = request.form.get("new_name").strip()
            if not file_name_new.endswith(".yaml"):
                file_name_new += ".yaml"

            path_file_new = CONFIG_DIR / file_name_new

            if os.path.exists(path_file_new):
                flash("❌ Bestand bestaat al, kies een andere naam.", "danger")
            else:
                with open(path_file_new, "w", encoding="utf-8") as f:
                    f.write(content)
                flash(f"✅ Bestand opgeslagen als '{file_name_new}'.", "success")
                return redirect(url_for("config_edit", filename=file_name_new))

    # bestand inladen
    with open(file_path, encoding="utf-8") as f:
        content = f.read()

    return render_template("config_edit.html", filename=filename, content=content)


@app.route("/configs/new", methods=["GET", "POST"])
def config_new():
    """Biedt een interface om een nieuwe configuratie aan te maken op basis van een bestaande.

    Deze functie verwerkt GET- en POST-verzoeken voor het aanmaken van een nieuwe configuratie,
    waarbij een bestaande als basis kan worden gekozen.
    Bij een POST-verzoek wordt het nieuwe bestand aangemaakt en opgeslagen,
    of wordt een foutmelding getoond als de naam al bestaat.

    Returns:
        Response: Een HTML-pagina voor het aanmaken van een nieuwe configuratie.
    """
    configs = sorted(
        [
            f.name
            for f in CONFIG_DIR.iterdir()
            if f.is_file() and f.suffix.lower() in [".yaml", ".yml"]
        ]
    )

    if request.method == "POST":
        base_file = request.form["base_file"]
        new_name = request.form["new_name"].strip()

        if not new_name.endswith(".yaml"):
            new_name += ".yaml"

        base_path = os.path.join(CONFIG_DIR, base_file)
        new_path = os.path.join(CONFIG_DIR, new_name)

        if os.path.exists(new_path):
            flash("❌ Bestand bestaat al, kies een andere naam.", "danger")
        else:
            shutil.copy(base_path, new_path)
            flash(
                f"✅ Nieuwe config '{new_name}' aangemaakt op basis van '{base_file}'",
                "success",
            )
            return redirect(url_for("config_edit", filename=new_name))

    return render_template("config_new.html", configs=configs)


@app.route("/run/<filename>")
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
    try:
        runner.start(config_path=config_file_path)
    except Exception as e:
        error_message = f"Fout bij het starten van de runner: {str(e)}"
        return render_template("error.html", message=error_message), 500
    return render_template("run.html", config=filename)


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
                if "doorgaan" in html_line or "antwoorden" in html_line:
                    yield "data: asking_question\n\n"
                elif "Afgerond" in html_line:
                    yield "data: finished\n\n"
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


@app.route("/browse/", defaults={"req_path": ""})
@app.route("/browse/<path:req_path>")
def browse(req_path):
    abs_path = secure_path(req_path)

    if not os.path.exists(abs_path):
        return abort(404)

    if os.path.isfile(abs_path):
        ext = os.path.splitext(abs_path)[1].lower()
        if ext == ".html":
            return open_html(req_path)
        elif ext == ".json":
            return open_json(req_path)
        elif ext == ".sql":
            return redirect(url_for("edit_sql", file_path=req_path))
        elif ext == ".csv":
            return redirect(url_for("edit_csv", file_path=req_path))
        else:
            return send_from_directory(
                os.path.dirname(abs_path),
                os.path.basename(abs_path),
                as_attachment=True,
            )

    files = os.listdir(abs_path)
    file_list = []
    for file in files:
        file_path = os.path.join(abs_path, file)
        rel_path = os.path.relpath(file_path, ROOT_DIR)
        file_list.append(
            {
                "name": file,
                "path": rel_path.replace("\\", "/"),
                "is_dir": os.path.isdir(file_path),
            }
        )

    return render_template("browser.html", files=file_list, current_path=req_path)


@app.route("/open/html/<path:file_path>")
def open_html(file_path):
    abs_path = secure_path(file_path)
    with open(abs_path, encoding="utf-8") as f:
        content = f.read()
    return Response(content, mimetype="text/html")


@app.route("/open/json/<path:file_path>")
def open_json(file_path):
    abs_path = secure_path(file_path)
    with open(abs_path, encoding="utf-8") as f:
        data = json.load(f)
    return render_template(
        "view_json.html", data=json.dumps(data, indent=2), file_path=file_path
    )


@app.route("/edit/sql/<path:file_path>", methods=["GET", "POST"])
def edit_sql(file_path):
    abs_path = secure_path(file_path)
    if request.method == "POST":
        content = request.form["content"]
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(content)
        return redirect(url_for("browse", req_path=os.path.dirname(file_path)))
    with open(abs_path, encoding="utf-8") as f:
        content = f.read()
    return render_template("edit_sql.html", content=content, file_path=file_path)


@app.route("/edit_csv/<path:path_file>")
def edit_csv(path_file):
    return render_template("edit_csv.html", filepath=path_file)

@app.route("/get_csv_data/<path:path_file>")
def get_csv_data(path_file):
    full_path = os.path.join("path/naar/jouw/csvs", path_file)
    with open(full_path, "r", encoding="utf-8") as f:
        return f.read()

@app.route("/save_csv_data/<path:path_file>", methods=["POST"])
def save_csv_data(path_file):
    data = request.get_json()
    csv_data = data.get("csv", "")
    full_path = os.path.join("path/naar/jouw/csvs", path_file)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(csv_data)
    return jsonify({"status": "ok"})


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
    log_path = (OUTPUT_DIR / filename).resolve()
    if log_path.exists():
        return send_file(str(log_path), as_attachment=True)
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
