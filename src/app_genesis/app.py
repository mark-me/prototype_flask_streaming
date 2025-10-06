from datetime import datetime
from pathlib import Path

import markdown
from flask import (
    Flask,
    Response,
    current_app,
    render_template,
    request,
)

from logtools import get_logger

from configs_registry import ConfigRegistry
from routes import browser, config_handler, runner

logger = get_logger(__name__)

app = Flask(__name__)
app.secret_key = "supersecret"
app.register_blueprint(browser, url_prefix="/browser")
app.register_blueprint(config_handler, url_prefix="/configs")
app.register_blueprint(runner, url_prefix="/runner")

config_registry = ConfigRegistry()


@app.route("/", methods=["GET", "POST"])
def index() -> Response:
    """Toont de startpagina met een lijst van beschikbare configuratiebestanden.

    Deze functie verzamelt alle configuratiebestanden en rendert de indexpagina waarop deze worden weergegeven.

    Returns:
        Response: Een HTML-pagina met een lijst van configuratiebestanden.
    """
    sort_by = request.args.get('sort', 'name')
    order = request.args.get('order', 'asc')
    configs = list(config_registry.get_configs())
    key_map = {'name': 'path_config', 'created': 'created', 'modified': 'modified'}
    key = key_map.get(sort_by, 'path_config')
    reverse = order == 'desc'
    configs.sort(key=lambda x: x[key], reverse=reverse)
    return render_template('index.html', configs=configs, sort_by=sort_by, order=order)


@app.template_filter("datetimeformat")
def datetimeformat(value):
    """Formateer de datum naar een leesbaar formaat."""
    return datetime.fromtimestamp(value, tz=None).strftime("%Y-%m-%d %H:%M:%S")


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
