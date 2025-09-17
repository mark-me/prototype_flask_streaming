import subprocess
import threading
import queue
import sys

class GenesisRunner:
    def __init__(self):
        self.process = None
        self.output_queue = queue.Queue()

    def start(self, config_path):
        self.process = subprocess.Popen(
            [sys.executable, "genesis.py", config_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        threading.Thread(target=self._enqueue_output, daemon=True).start()

    def _enqueue_output(self):
        for line in self.process.stdout:
            self.output_queue.put(line.strip())
        self.process.stdout.close()

    def stream_output(self):
        while True:
            try:
                line = self.output_queue.get(timeout=0.5)
                yield line
            except queue.Empty:
                if self.process.poll() is not None:
                    break

    def send_input(self, text):
        if self.process and self.process.stdin:
            self.process.stdin.write(text + "\n")
            self.process.stdin.flush()
