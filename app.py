import os
from pathlib import Path

from flask import (
    Flask,
    Response,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)

from genesis_runner import GenesisRunner

app = Flask(__name__)
runner = GenesisRunner()

CONFIG_DIR = "configs"
OUTPUT_DIR = "output"


@app.route("/")
def index():
    configs = [f for f in os.listdir(CONFIG_DIR) if f.endswith(".yml")]
    return render_template("index.html", configs=configs)


@app.route("/edit/<config>", methods=["GET", "POST"])
def edit_config(config):
    path = os.path.join(CONFIG_DIR, config)
    if request.method == "POST":
        content = request.form["content"]
        with open(path, "w") as f:
            f.write(content)
        return redirect(url_for("index"))

    content = Path(path).read_text()
    return render_template("edit.html", config=config, content=content)


@app.route("/run/<config>")
def run_config(config):
    path = os.path.join(CONFIG_DIR, config)
    runner.start(path)
    return render_template("run.html", config=config)


@app.route("/stream")
def stream():
    def generate():
        for line in runner.stream_output():
            yield f"data: {line}\n\n"
    return Response(generate(), mimetype="text/event-stream")


@app.route("/input", methods=["POST"])
def send_input():
    value = request.json.get("value")
    runner.send_input(value)
    return {"status": "ok"}


@app.route("/download-log")
def download_log():
    log_path = os.path.join(OUTPUT_DIR, "sample.csv")
    if os.path.exists(log_path):
        return send_file(log_path, as_attachment=True)
    return "Geen log gevonden", 404


if __name__ == "__main__":
    app.run(debug=True, threaded=True)
