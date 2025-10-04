from flask import Flask, render_template, request, jsonify, Response
import threading
import time
from configs_registry import ConfigRegistry

app = Flask(__name__)
registry = ConfigRegistry()
outputs = {}  # filename: {'lines': [], 'prompt': None, 'awaiting': False, 'lock': threading.Lock()}

@app.route('/')
def index():
    sort_by = request.args.get('sort', 'name')
    order = request.args.get('order', 'asc')
    configs = list(registry.get_configs())
    key_map = {'name': 'path_config', 'created': 'created', 'modified': 'modified'}
    key = key_map.get(sort_by, 'path_config')
    reverse = order == 'desc'
    configs.sort(key=lambda x: x[key], reverse=reverse)
    return render_template('index.html', configs=configs, sort_by=sort_by, order=order)

@app.route('/start/<filename>', methods=['POST'])
def start(filename):
    runner = registry.get_config_runner(filename)
    if filename not in outputs:
        outputs[filename] = {'lines': [], 'prompt': None, 'awaiting': False, 'lock': threading.Lock()}
    if runner.status in ['idle', 'finished']:
        if runner.status == 'finished':
            runner.stop()  # Reset to idle
        # Clear previous output for new run
        with outputs[filename]['lock']:
            outputs[filename]['lines'] = []
            outputs[filename]['prompt'] = None
            outputs[filename]['awaiting'] = False
        runner.start()
        def collector():
            for line in runner.stream_output():
                with outputs[filename]['lock']:
                    outputs[filename]['lines'].append(line)
                    if any(["doorgaan" in line.lower(), "antwoorden" in line.lower()]):
                        outputs[filename]['prompt'] = line.strip()
                        outputs[filename]['awaiting'] = True
                    if "Afgerond" in line:
                        pass  # Finished handled by status
            # After stream ends, ensure status updates
        threading.Thread(target=collector, daemon=True).start()
        return jsonify({'status': 'started'})
    else:
        return jsonify({'status': 'already_running'}), 400

@app.route('/input/<filename>', methods=['POST'])
def send_input(filename):
    answer = request.json.get('answer')
    runner = registry.get_config_runner(filename)
    runner.send_input(answer)
    with outputs[filename]['lock']:
        outputs[filename]['awaiting'] = False
        outputs[filename]['prompt'] = None
    return jsonify({'status': 'sent'})

@app.route('/status')
def get_status():
    status_dict = {}
    for filename in registry.configs:
        runner = registry.get_config_runner(filename)
        stat = runner.status
        awaiting = False
        prompt = None
        if filename in outputs:
            with outputs[filename]['lock']:
                awaiting = outputs[filename]['awaiting']
                prompt = outputs[filename]['prompt']
        if awaiting:
            stat = 'awaiting_input'
        status_dict[filename] = {'status': stat, 'prompt': prompt}
    return jsonify(status_dict)

@app.route('/output/<filename>')
def output(filename):
    return render_template('output.html', filename=filename)

@app.route('/stream_output/<filename>')
def stream_output(filename):
    def generate():
        if filename not in outputs:
            yield "data: No output\n\n"
            return
        last_sent = 0
        while True:
            with outputs[filename]['lock']:
                current_lines = outputs[filename]['lines']
                for line in current_lines[last_sent:]:
                    yield f"data: {line.replace('\n', '')}\n\n"
                last_sent = len(current_lines)
            runner = registry.get_config_runner(filename)
            if runner.status == 'finished':
                yield "data: [END]\n\n"
                break
            time.sleep(0.5)
    return Response(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(debug=True)