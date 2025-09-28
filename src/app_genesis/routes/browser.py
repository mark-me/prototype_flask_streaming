import csv
import io
import json
import os
from datetime import datetime
from pathlib import Path

from flask import (
    Blueprint,
    Response,
    abort,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)

browser = Blueprint("browser", __name__)


def secure_path(path):
    root = Path(".").resolve()
    full_path = root / path
    if root not in full_path.parents:
        abort(403)
    return full_path


@browser.route("/browse/", defaults={"req_path": ""})
@browser.route("/browse/<path:req_path>")
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
        return handle_file_request(path_absolute, req_path)

    return render_directory_listing(path_absolute, req_path)


def handle_file_request(path_absolute, req_path):
    """Handelt het openen of downloaden van een bestand af op basis van de extensie.

    Deze functie bepaalt het type bestand en stuurt het naar de juiste viewer of als download naar de client.

    Args:
        path_absolute (Path): Het absolute pad naar het bestand.
        req_path (str): Het relatieve pad dat door de gebruiker is aangevraagd.

    Returns:
        Response: Een response die het bestand toont in de juiste viewer of als download aanbiedt.
    """
    ext = path_absolute.suffix.lower()
    if ext == ".html":
        return open_html(req_path)
    elif ext == ".json":
        return open_json(req_path)
    elif ext == ".sql":
        return redirect(url_for("browser.open_sql", path_file=req_path))
    elif ext == ".csv":
        return redirect(url_for("browser.edit_csv", path_file=req_path))
    else:
        return send_from_directory(
            str(path_absolute.parent),
            path_absolute.name,
            as_attachment=True,
        )


def render_directory_listing(path_absolute, req_path):
    """Genereert een HTML-pagina met de inhoud van een directory.

    Deze functie verzamelt informatie over alle bestanden en mappen in de opgegeven directory en rendert deze in een browser-template.

    Args:
        path_absolute (Path): Het absolute pad naar de directory.
        req_path (str): Het relatieve pad dat door de gebruiker is aangevraagd.

    Returns:
        Response: Een HTML-pagina met een lijst van bestanden en mappen in de directory.
    """
    path_root = Path(".").resolve()
    path_files = sorted(path_absolute.iterdir(), key=lambda p: (p.is_file(), p.name))
    files_data = [
        {"path": path_file, "stat": path_file.stat()} for path_file in path_files
    ]
    file_list = [
        {
            "name": file_data["path"].name,
            "path": str(file_data["path"].relative_to(path_root)).replace("\\", "/"),
            "modified": datetime.fromtimestamp(file_data["stat"].st_mtime),
            "created": datetime.fromtimestamp(file_data["stat"].st_ctime),
            "is_dir": file_data["path"].is_dir(),
        }
        for file_data in files_data
    ]

    req_path_formatted = str(req_path).replace("\\", "/")
    return render_template(
        "browser/browser.html", files=file_list, current_path=req_path_formatted
    )


@browser.route("/open/html/<path:path_file>")
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
    # return render_template('html_view.html', content=content)
    return Response(content, mimetype="text/html")


@browser.route("/open/json/<path:path_file>")
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
        content = json.load(f)

    return jsonify(data=content, status=200)


@browser.route("/open/sql/<path:path_file>", methods=["GET", "POST"])
def open_sql(path_file):
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
        return redirect(url_for("browser.browse", req_path=os.path.dirname(path_file)))
    with open(abs_path, encoding="utf-8") as f:
        content = f.read()
    return render_template(
        "file_editor.html",
        filename=path_file,
        content=content,
        file_type="sql",
        read_only=True,
    )


@browser.route("/edit_csv/<path:path_file>", methods=["GET", "POST"])
def edit_csv(path_file):
    """Biedt een interface om een CSV-bestand te bekijken en te bewerken.

    Deze functie verwerkt GET- en POST-verzoeken voor het bewerken van een CSV-bestand.
    Bij een GET-verzoek wordt de inhoud van het bestand geladen en weergegeven.
    Bij een POST-verzoek wordt het bestand opgeslagen met de nieuwe inhoud.

    Args:
        path_file (str): Het pad naar het CSV-bestand dat bewerkt moet worden.

    Returns:
        Response: Een HTML-pagina voor het bewerken van het CSV-bestand of een JSON-status na opslaan.
    """

    if not os.path.exists(path_file):
        return "Bestand niet gevonden", 404

    if request.method == "GET":
        return handle_edit_csv_get(path_file)

    if request.method == "POST":
        return handle_edit_csv_post(path_file)


def handle_edit_csv_get(path_file):
    """Leest de inhoud van een CSV-bestand en rendert deze in een HTML-template.

    Deze functie opent het opgegeven CSV-bestand, leest de rijen en stuurt deze naar de template voor bewerking.

    Args:
        path_file (str): Het pad naar het CSV-bestand dat gelezen moet worden.

    Returns:
        Response: Een HTML-pagina met de inhoud van het CSV-bestand.
    """
    with open(path_file, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        data = list(reader)
    return render_template("browser/edit_csv.html", path_file=path_file, data=data)


def handle_edit_csv_post(csv_path):
    """Slaat nieuwe CSV-inhoud op in het opgegeven bestand.

    Deze functie ontvangt de nieuwe CSV-data van de client en schrijft deze naar het opgegeven bestandspad.

    Args:
        csv_path (str): Het pad naar het CSV-bestand waarin de nieuwe data moet worden opgeslagen.

    Returns:
        Response: Een JSON-object met de status van de opslagoperatie.
    """
    new_csv = request.json["csv"]
    with open(csv_path, "w", newline="", encoding="utf-8") as csvfile:
        reader = csv.reader(io.StringIO(new_csv))
        writer = csv.writer(csvfile)
        writer.writerows(reader)
    return jsonify({"status": "success"})


@browser.route("/get_csv_data/<path:path_file>")
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


@browser.route("/download_csv/<path:path_file>", methods=["POST"])
def download_csv(path_file: str):
    """Slaat de ontvangen CSV-gegevens op in het opgegeven bestandspad.

    Deze functie ontvangt CSV-data via een POST-verzoek en schrijft deze naar het opgegeven bestand.
    Na het succesvol opslaan van de gegevens wordt een bevestiging in JSON-formaat geretourneerd.

    Args:
        path_file (str): Het pad naar het CSV-bestand waarin de gegevens moeten worden opgeslagen.

    Returns:
        Response: Een JSON-object met de status van de opslagoperatie.
    """
    filename = Path(path_file).name
    data = request.get_json()
    csv_data = data.get("csv", "")

    response = Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
    return response
