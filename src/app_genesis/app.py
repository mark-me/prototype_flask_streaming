import shutil
from pathlib import Path

import markdown
from flask import (
    Flask,
    Response,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from routes import browser, runner

from config import GenesisConfig
from logtools import get_logger

logger = get_logger(__name__)

app = Flask(__name__)
app.secret_key = "supersecret"
app.register_blueprint(browser, url_prefix="/browser")
app.register_blueprint(runner, url_prefix="/runner")


CONFIG_DIR = Path("configs").resolve()
OUTPUT_DIR = Path("output").resolve()


@app.route("/")
def index() -> Response:
    """Toont de startpagina met een lijst van beschikbare configuratiebestanden.

    Deze functie verzamelt alle configuratiebestanden en rendert de indexpagina waarop deze worden weergegeven.

    Returns:
        Response: Een HTML-pagina met een lijst van configuratiebestanden.
    """
    configs = get_configs()
    # files_config = [path_config.name for path_config in paths_config]
    return render_template("index.html", configs=configs)


def get_configs() -> list[dict]:
    """Geeft een lijst van configuratiebestanden met hun outputdirectory en status.

    Deze functie zoekt naar alle YAML-configuratiebestanden in de configuratiemap en retourneert
    een lijst met hun namen, outputdirectory en of deze bestaat.

    Returns:
        list: Een lijst van dicts met informatie over de configuratiebestanden.
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
            "exists_output": GenesisConfig(
                file_config=path_config, create_version_dir=False
            ).path_intermediate_root.exists(),
        }
        for path_config in paths_config
    ]
    return configs


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
        return handle_config_edit_post(filename, path_file)

    return handle_config_edit_get(filename, path_file)


def handle_config_edit_post(filename: str, path_file: Path):
    """Verwerkt het POST-verzoek voor het opslaan of opslaan als van een configuratiebestand.

    Deze functie verwerkt de actie van de gebruiker (opslaan of opslaan als) en slaat het configuratiebestand op.
    Bij 'save_as' wordt gecontroleerd of de nieuwe bestandsnaam al bestaat en wordt het bestand eventueel als nieuw opgeslagen.

    Args:
        filename (str): De naam van het huidige configuratiebestand.
        path_file (Path): Het pad naar het huidige configuratiebestand.

    Returns:
        Response: Een HTML-pagina voor het bewerken van het configuratiebestand of een redirect na 'save as'.
    """
    action = request.form.get("action")
    content = request.form.get("content")
    content = content.replace("\r\n", "\n")

    if action == "save":
        return _handle_save(filename, path_file, content)

    elif action == "save_as":
        return _handle_save_as(filename, content)

    return _render_editor(filename, path_file)


def _handle_save(filename: str, path_file: Path, content: str):
    """Slaat het configuratiebestand op met de opgegeven inhoud.

    Deze functie slaat de inhoud op in het bestaande configuratiebestand en toont een succesmelding.

    Args:
        filename (str): De naam van het configuratiebestand.
        path_file (Path): Het pad naar het configuratiebestand.
        content (str): De inhoud die moet worden opgeslagen.

    Returns:
        Response: Een HTML-pagina voor het bewerken van het configuratiebestand.
    """
    save_config_file(path_file, content)
    flash(f"✅ Bestand '{filename}' opgeslagen.", "success")
    return _render_editor(filename, path_file)


def _handle_save_as(filename: str, content: str):
    """Slaat de inhoud op als een nieuw configuratiebestand met een opgegeven naam.

    Deze functie controleert of de nieuwe bestandsnaam al bestaat en slaat het bestand op als deze uniek is.
    Bij een bestaande naam wordt een foutmelding getoond.

    Args:
        filename (str): De naam van het huidige configuratiebestand.
        content (str): De inhoud die moet worden opgeslagen.

    Returns:
        Response: Een HTML-pagina voor het bewerken van het configuratiebestand of een redirect naar de editor.
    """
    file_name_new = request.form.get("new_name").strip()
    if not (file_name_new.endswith(".yaml") or file_name_new.endswith(".yml")):
        file_name_new += ".yaml"

    path_file_new = CONFIG_DIR / file_name_new

    if path_file_new.exists():
        flash("❌ Bestand bestaat al, kies een andere naam.", "danger")
        return _render_editor(filename, path_file_new)
    else:
        save_config_file(path_file_new, content)
        flash(f"✅ Bestand opgeslagen als '{file_name_new}'.", "success")
        return redirect(url_for("config_edit", filename=file_name_new))


def _render_editor(filename: str, path_file: Path):
    """Laadt de inhoud van een configuratiebestand en rendert de editorpagina.

    Deze functie opent het opgegeven configuratiebestand en toont de editor met de huidige inhoud.

    Args:
        filename (str): De naam van het configuratiebestand.
        path_file (Path): Het pad naar het configuratiebestand.

    Returns:
        Response: Een HTML-pagina voor het bewerken van het configuratiebestand.
    """
    with open(path_file, encoding="utf-8") as f:
        content = f.read()

    return render_template(
        "file_editor.html",
        filename=filename,
        content=content,
        file_type="yaml",
        read_only=False,
    )


def save_config_file(path: Path, content: str):
    """Slaat de opgegeven inhoud op in het opgegeven configuratiebestand.

    Args:
        path (Path): Het pad naar het configuratiebestand.
        content (str): De inhoud die moet worden opgeslagen.
    """
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def handle_config_edit_get(filename: str, path_file: Path):
    """Laadt de inhoud van een configuratiebestand en toont deze in de editor.

    Deze functie opent het opgegeven configuratiebestand en rendert de editorpagina met de inhoud.

    Args:
        filename (str): De naam van het te bewerken configuratiebestand.
        path_file (Path): Het pad naar het configuratiebestand.

    Returns:
        Response: Een HTML-pagina voor het bewerken van het configuratiebestand.
    """
    with open(path_file, encoding="utf-8") as f:
        content = f.read()

    return render_template(
        "file_editor.html",
        filename=filename,
        content=content,
        file_type="yaml",
        read_only=False,
    )


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
    configs = get_sorted_config_names()

    if request.method == "POST":
        return handle_config_new_post(configs)
    return render_template("config_new.html", configs=configs)


def get_sorted_config_names():
    """Geeft een alfabetisch gesorteerde lijst van configuratiebestandsnamen terug.

    Deze functie zoekt naar alle YAML-configuratiebestanden in de configuratiemap en retourneert hun namen gesorteerd.

    Returns:
        list: Een alfabetisch gesorteerde lijst van configuratiebestandsnamen.
    """
    return sorted(
        [
            f.name
            for f in CONFIG_DIR.iterdir()
            if f.is_file() and f.suffix.lower() in [".yaml", ".yml"]
        ]
    )


def handle_config_new_post(configs: list):
    """Verwerkt het POST-verzoek voor het aanmaken van een nieuwe configuratie op basis van een bestaande.

    Deze functie kopieert een bestaande configuratie naar een nieuw bestand met de opgegeven naam, mits deze nog niet bestaat.
    Bij een bestaande naam wordt een foutmelding getoond.

    Args:
        configs (list): Een lijst van bestaande configuratiebestandsnamen.

    Returns:
        Response: Een HTML-pagina voor het aanmaken van een nieuwe configuratie of een redirect naar de editor.
    """
    base_file = request.form["base_file"]
    new_name = request.form["new_name"].strip()

    if not new_name.endswith(".yaml") and not new_name.endswith(".yml"):
        new_name += ".yaml"

    base_path = CONFIG_DIR / base_file
    new_path = CONFIG_DIR / new_name

    if new_path.exists():
        flash("❌ Bestand bestaat al, kies een andere naam.", "danger")
    else:
        shutil.copy(base_path, new_path)
        flash(
            f"✅ Nieuwe config '{new_name}' aangemaakt op basis van '{base_file}'",
            "success",
        )
        return redirect(url_for("config_edit", filename=new_name))
    return render_template("config_new.html", configs=configs)


@app.route("/about")
def about():
    """Toont de 'Over'-pagina met informatie uit het Markdown-bestand.

    Deze functie leest de inhoud van 'about.md', converteert deze naar HTML en rendert de bijbehorende pagina.

    Returns:
        Response: Een HTML-pagina met informatie over de applicatie.
    """
    about_md_path = Path(current_app.static_folder) / "about.md"
    if not about_md_path.exists():
        error_message = (
            "<p>Het bestand <code>about.md</code> kon niet worden gevonden.</p>"
        )
        return render_template("about.html", content=error_message), 404
    with open(about_md_path, encoding="utf-8") as f:
        content = f.read()
    html = markdown.markdown(content, extensions=["fenced_code", "tables"])
    return render_template("about.html", content=html)


if __name__ == "__main__":
    app.run(debug=True, threaded=True)
