import shutil
from pathlib import Path

from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from ..configs_registry import ConfigRegistry

config_handler = Blueprint("config_handler", __name__)

CONFIG_DIR = Path("configs").resolve()
config_registry = ConfigRegistry()


@config_handler.route("/delete/<filename>", methods=["POST"])
def config_delete(filename: str):
    """Verwijdert het geselecteerde configuratiebestand."""
    path_file = CONFIG_DIR / filename
    if path_file.exists():
        path_file.unlink()  # Verwijder het bestand
        config_registry.delete(filename)  # Verwijder uit register
        flash(f"✅ Configuratiebestand '{filename}' is verwijderd.", "success")
    else:
        flash(f"❌ Configuratiebestand '{filename}' niet gevonden.", "danger")
    return redirect(url_for("index"))


@config_handler.route("/edit/<filename>", methods=["GET", "POST"])
def config_edit(filename):
    """Biedt een interface om een configuratiebestand te bewerken of op te slaan."""
    path_file = CONFIG_DIR / filename

    if request.method == "POST":
        return handle_config_edit_post(filename, path_file)

    return handle_config_edit_get(filename, path_file)


def handle_config_edit_post(filename: str, path_file: Path):
    """Verwerkt het POST-verzoek voor het opslaan of opslaan als van een configuratiebestand."""
    action = request.form.get("action")
    content = request.form.get("content")
    content = content.replace("\r\n", "\n")

    if action == "save":
        return _handle_save(filename, path_file, content)

    elif action == "save_as":
        return _handle_save_as(filename, content)

    return _render_editor(filename, path_file)


def _handle_save(filename: str, path_file: Path, content: str):
    """Slaat het configuratiebestand op met de opgegeven inhoud."""
    save_config_file(path_file, content)
    flash(f"✅ Bestand '{filename}' opgeslagen.", "success")
    config_registry.refresh()  # Ververst het register om wijzigingsdatum bij te werken
    return _render_editor(filename, path_file)


def _handle_save_as(filename: str, content: str):
    """Slaat de inhoud op als een nieuw configuratiebestand met een opgegeven naam."""
    file_name_new = request.form.get("new_name").strip()
    if not (file_name_new.endswith(".yaml") or file_name_new.endswith(".yml")):
        file_name_new += ".yaml"

    path_file_new = CONFIG_DIR / file_name_new

    if path_file_new.exists():
        flash("❌ Bestand bestaat al, kies een andere naam.", "danger")
        return _render_editor(filename, path_file_new)
    else:
        save_config_file(path_file_new, content)
        config_registry.add(file_name_new)  # Voeg nieuwe config toe aan register
        flash(f"✅ Bestand opgeslagen als '{file_name_new}'.", "success")
        return redirect(url_for("index"))  # Redirect naar index om tabel bij te werken


def _render_editor(filename: str, path_file: Path):
    """Laadt de inhoud van een configuratiebestand en rendert de editorpagina."""
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
    """Slaat de opgegeven inhoud op in het opgegeven configuratiebestand."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def handle_config_edit_get(filename: str, path_file: Path):
    """Laadt de inhoud van een configuratiebestand en toont deze in de editor."""
    with open(path_file, encoding="utf-8") as f:
        content = f.read()

    return render_template(
        "file_editor.html",
        filename=filename,
        content=content,
        file_type="yaml",
        read_only=False,
    )


@config_handler.route("/new", methods=["GET", "POST"])
def config_new():
    """Biedt een interface om een nieuwe configuratie aan te maken op basis van een bestaande."""
    configs = get_sorted_config_names()

    if request.method == "POST":
        return handle_config_new_post(configs)
    return render_template("config_handler/config_new.html", configs=configs)


def handle_config_new_post(configs: list):
    """Verwerkt het POST-verzoek voor het aanmaken van een nieuwe configuratie op basis van een bestaande."""
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
        config_registry.add(new_name)  # Voeg nieuwe config toe aan register
        flash(
            f"✅ Nieuwe config '{new_name}' aangemaakt op basis van '{base_file}'",
            "success",
        )
        return redirect(
            url_for("config_handler.config_edit", filename=new_name)
        )  # Redirect naar editor
    return render_template("config_handler/config_new.html", configs=configs)


def get_sorted_config_names():
    """Geeft een alfabetisch gesorteerde lijst van configuratiebestandsnamen terug."""
    return sorted(
        [
            f.name
            for f in CONFIG_DIR.iterdir()
            if f.is_file() and f.suffix.lower() in [".yaml", ".yml"]
        ]
    )
