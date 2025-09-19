import subprocess
import threading
import queue
import sys
from pathlib import Path

class GenesisRunner:
    """Beheert het uitvoeren van een Genesis-proces en de communicatie met invoer en uitvoer.

    Deze klasse start het Genesis-proces, verzamelt uitvoerregels, biedt streaming van uitvoer en accepteert invoer van de gebruiker.
    """
    def __init__(self):
        self.process = None
        self.queue_output = queue.Queue()

    def start(self, config_path: Path):
        """Start een nieuw Genesis-proces met het opgegeven configuratiebestand.

        Deze methode initialiseert het proces en start een thread om de uitvoer te verzamelen.

        Args:
            config_path (Path): Het pad naar het configuratiebestand.
        """
        self.process = subprocess.Popen(
            [sys.executable, "src/genesis.py", config_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            encoding="utf8"
        )
        threading.Thread(target=self._enqueue_output, daemon=True).start()

    def _enqueue_output(self):
        """Leest uitvoerregels van het Genesis-proces en plaatst deze in de uitvoerwachtrij.

        Deze methode wordt uitgevoerd in een aparte thread en zorgt ervoor dat alle uitvoer beschikbaar is voor streaming.
        """
        for line in self.process.stdout:
            self.queue_output.put(line) #.strip())
        self.process.stdout.close()

    def stream_output(self):
        """Genereert uitvoerregels van het Genesis-proces voor streaming naar de client.

        Deze methode levert telkens een nieuwe uitvoerregel zolang het proces actief is of er nog uitvoer beschikbaar is.

        Yields:
            str: Een uitvoerregel van het Genesis-proces.
        """
        while True:
            try:
                line = self.queue_output.get(timeout=0.5)
                yield line
            except queue.Empty:
                if self.process.poll() is not None:
                    break

    def send_input(self, text: str):
        """Stuurt invoer naar het actieve Genesis-proces.

        Deze methode schrijft de opgegeven tekst naar de standaardinvoer van het proces als het actief is.

        Args:
            text (str): De tekst die naar het Genesis-proces gestuurd moet worden.
        """
        if self.process and self.process.stdin:
            self.process.stdin.write(text + "\n")
            self.process.stdin.flush()
