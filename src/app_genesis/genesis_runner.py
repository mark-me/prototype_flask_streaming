import subprocess
import threading
import queue
import sys
from pathlib import Path


class GenesisRunner:
    """Beheert het uitvoeren van een Genesis-proces en de communicatie met invoer en uitvoer.

    Deze klasse start het Genesis-proces, verzamelt uitvoerregels, biedt streaming van uitvoer en accepteert invoer van de gebruiker.
    """

    def __init__(self, path_config: Path):
        self._process = None
        self._queue_output = queue.Queue()
        self.path_config = path_config

    def start(self):
        """Start een nieuw Genesis-proces met het opgegeven configuratiebestand.

        Deze methode initialiseert het proces en start een thread om de uitvoer te verzamelen.

        Args:
            path_config (Path): Het pad naar het configuratiebestand.
        """
        self._process = subprocess.Popen(
            [sys.executable, "src/genesis.py", self.path_config],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            encoding="utf8",
        )
        threading.Thread(target=self._enqueue_output, daemon=True).start()

    def is_running(self) -> bool:
        """Controleert of het Genesis-proces momenteel actief is.

        Geeft True terug als het proces draait, anders False.

        Returns:
            bool: True als het proces actief is, anders False.
        """
        return self._process is not None and self._process.poll() is None

    def stop(self):
        """Stopt het actieve Genesis-proces indien aanwezig.

        Deze methode beëindigt het proces en wacht tot het volledig is afgesloten.
        """
        if self._process:
            self._process.terminate()
            self._process.wait()

    def _enqueue_output(self):
        """Leest uitvoerregels van het Genesis-proces en plaatst deze in de uitvoerwachtrij.

        Deze methode wordt uitgevoerd in een aparte thread en zorgt ervoor dat alle uitvoer beschikbaar is voor streaming.
        """
        for line in self._process.stdout:
            self._queue_output.put(line)
        self._process.stdout.close()

    def stream_output(self):
        """Genereert uitvoerregels van het Genesis-proces voor streaming naar de client.

        Deze methode levert telkens een nieuwe uitvoerregel zolang het proces actief is of er nog uitvoer beschikbaar is.

        Yields:
            str: Een uitvoerregel van het Genesis-proces.
        """
        while True:
            try:
                yield self._queue_output.get(timeout=0.5)
            except queue.Empty:
                if self._process.poll() is not None:
                    break

    def send_input(self, text: str):
        """Stuurt invoer naar het actieve Genesis-proces.

        Deze methode schrijft de opgegeven tekst naar de standaardinvoer van het proces als het actief is.

        Args:
            text (str): De tekst die naar het Genesis-proces gestuurd moet worden.
        """
        if self._process and self._process.stdin:
            self._process.stdin.write(text + "\n")
            self._process.stdin.flush()
