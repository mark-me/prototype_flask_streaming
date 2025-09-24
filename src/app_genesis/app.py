import json
import os
import shutil
from pathlib import Path

import markdown
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
        {
            "path_config": path_config.name,
            "dir_output": GenesisConfig(
                file_config=path_config, create_version_dir=False
            ).path_intermediate_root,
            "exists_output":  GenesisConfig(
                file_config=path_config, create_version_dir=False
            ).path_intermediate_root.exists()
        }
        for path_config in paths_config
    ]
    #files_config = [path_config.name for path_config in paths_config]
    return render_template("index.html", configs=configs)


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
    path_file = CONFIG_DIR / filename

    if request.method == "POST":
        action = request.form.get("action")
        content = request.form.get("content")

        if action == "save":
            with open(path_file, "w", encoding="utf-8") as f:
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
    with open(path_file, encoding="utf-8") as f:
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
    """Biedt een bestandsbrowser waarmee gebruikers door mappen kunnen navigeren en bestanden kunnen openen of downloaden.

    Deze functie verwerkt het opgegeven pad, toont de inhoud van mappen of stuurt bestanden naar de juiste viewers of als download naar de client.

    Args:
        req_path (str): Het relatieve pad naar de te bekijken map of het bestand.

    Returns:
        Response: Een HTML-pagina met de inhoud van de map, of een bestand als download of in de juiste viewer.
    """
    path_absolute = secure_path(req_path)

    if not path_absolute.exists():
        return abort(404)

    if path_absolute.is_file():
        ext = path_absolute.suffix
        if ext == ".html":
            return open_html(req_path)
        elif ext == ".json":
            return open_json(req_path)
        elif ext == ".sql":
            return redirect(url_for("edit_sql", path_file=req_path))
        elif ext == ".csv":
            return redirect(url_for("edit_csv", path_file=req_path))
        else:
            return send_from_directory(
                str(path_absolute.parent),
                path_absolute.name,
                as_attachment=True,
            )

    path_files = sorted(path_absolute.iterdir(), key=lambda p: (p.is_file(), p.name))
    file_list = []
    for file in path_files:
        rel_path = file.relative_to(ROOT_DIR)
        file_list.append(
            {
                "name": file.name,
                "path": str(rel_path),
                "is_dir": file.is_dir(),
            }
        )

    return render_template("browser.html", files=file_list, current_path=req_path)


@app.route("/open/html/<path:path_file>")
def open_html(path_file):
    """Opent een HTML-bestand en retourneert de inhoud als HTML-respons.

    Deze functie leest het opgegeven HTML-bestand en stuurt de inhoud terug naar de client als een HTML-pagina.

    Args:
        path_file (str): Het pad naar het HTML-bestand dat geopend moet worden.

    Returns:
        Response: De inhoud van het HTML-bestand als een Flask Response-object met mimetype 'text/html'.
    """
    abs_path = secure_path(path_file)
    with open(abs_path, encoding="utf-8") as f:
        content = f.read()
    return Response(content, mimetype="text/html")


@app.route("/open/json/<path:path_file>")
def open_json(path_file):
    """Opent een JSON-bestand en toont de inhoud in een HTML-template.

    Deze functie leest het opgegeven JSON-bestand, formatteert de inhoud en rendert deze in een HTML-pagina.

    Args:
        path_file (str): Het pad naar het JSON-bestand dat geopend moet worden.

    Returns:
        Response: Een HTML-pagina met de geformatteerde JSON-inhoud.
    """
    # Beveilig het pad naar het JSON-bestand
    abs_path = secure_path(path_file)

    # Lees de JSON-data
    with open(abs_path, encoding="utf-8") as f:
        data = json.load(f)

    # Geef de data door aan de template
    return render_template("view_json.html", data=data, path_file=path_file)


@app.route("/edit/sql/<path:path_file>", methods=["GET", "POST"])
def edit_sql(path_file):
    """Biedt een interface om een SQL-bestand te bewerken en op te slaan.

    Deze functie verwerkt GET- en POST-verzoeken voor het bewerken en opslaan van een SQL-bestand.
    Bij een POST-verzoek wordt het bestand opgeslagen en wordt de gebruiker teruggeleid naar de bestandsbrowser.
    Bij een GET-verzoek wordt de inhoud van het bestand geladen en weergegeven.

    Args:
        path_file (str): Het pad naar het SQL-bestand dat bewerkt moet worden.

    Returns:
        Response: Een HTML-pagina voor het bewerken van het SQL-bestand of een redirect na opslaan.
    """
    abs_path = secure_path(path_file)
    if request.method == "POST":
        content = request.form["content"]
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(content)
        return redirect(url_for("browse", req_path=os.path.dirname(path_file)))
    with open(abs_path, encoding="utf-8") as f:
        content = f.read()
    return render_template("edit_sql.html", content=content, file_path=path_file)


@app.route("/edit_csv/<path:path_file>")
def edit_csv(path_file):
    """Biedt een interface om een CSV-bestand te bewerken.

    Deze functie rendert een HTML-pagina waarmee gebruikers het opgegeven CSV-bestand kunnen bekijken en bewerken.

    Args:
        path_file (str): Het pad naar het CSV-bestand dat bewerkt moet worden.

    Returns:
        Response: Een HTML-pagina voor het bewerken van het CSV-bestand.
    """
    path_file = Path(path_file).resolve()
    return render_template("edit_csv.html", path_file=path_file)


@app.route("/get_csv_data/<path:path_file>")
def get_csv_data(path_file):
    """Haalt de inhoud van een CSV-bestand op en retourneert deze als tekst.

    Deze functie leest het opgegeven CSV-bestand en stuurt de inhoud terug naar de client.

    Args:
        path_file (str): Het pad naar het CSV-bestand dat opgehaald moet worden.

    Returns:
        str: De inhoud van het CSV-bestand als tekst.
    """
    path_file = Path(path_file).resolve()
    with open(path_file, "r", encoding="utf-8") as f:
        return f.read()


@app.route("/save_csv_data/<path:path_file>", methods=["POST"])
def save_csv_data(path_file):
    """Slaat de ontvangen CSV-gegevens op in het opgegeven bestandspad.

    Deze functie ontvangt CSV-data via een POST-verzoek en schrijft deze naar het opgegeven bestand.
    Na het succesvol opslaan van de gegevens wordt een bevestiging in JSON-formaat geretourneerd.

    Args:
        path_file (str): Het pad naar het CSV-bestand waarin de gegevens moeten worden opgeslagen.

    Returns:
        Response: Een JSON-object met de status van de opslagoperatie.
    """
    data = request.get_json()
    csv_data = data.get("csv", "")
    path_file = Path(path_file).resolve()
    with open(path_file, "w", encoding="utf-8") as f:
        f.write(csv_data)
    return jsonify({"status": "ok"})


@app.route("/download-file/<path:path_file>")
def download_file(path_file) -> Response:
    """Maakt het mogelijk om een logbestand te downloaden als CSV-bestand.

    Deze functie valideert de bestandsnaam, controleert of het logbestand bestaat en stuurt het bestand naar de client.
    Bij een ongeldige bestandsnaam of ontbrekend bestand wordt een foutmelding geretourneerd.

    Returns:
        Response: Het CSV-bestand als download, of een foutmelding als het bestand niet geldig of niet gevonden is.
    """
    path_file = Path(path_file).resolve()
    if path_file.exists():
        return send_file(path_file, as_attachment=True)
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
