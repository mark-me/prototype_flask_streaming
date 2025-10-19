import threading
from datetime import datetime
from pathlib import Path

from .genesis_runner import GenesisRunner
from config import GenesisConfig
from logtools import get_logger

logger = get_logger(__name__)

class ConfigRegistry:
    """Beheert het register van configuratiebestanden en hun metadata."""
    _instance = None
    CONFIG_DIR = Path("configs").resolve()
    _lock = threading.Lock()


    def __new__(cls):
        """Implementeert het singleton-patroon voor ConfigRegistry.

        Zorgt ervoor dat er slechts één instantie van ConfigRegistry bestaat en initialiseert de configuraties bij de eerste aanmaak.

        Returns:
            ConfigRegistry: De singleton-instantie van ConfigRegistry.
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(ConfigRegistry, cls).__new__(cls)
                    cls._instance.__init__()
        return cls._instance

    def __init__(self):
        """Initialiseert een nieuwe instantie van ConfigRegistry.

        Zet de status- en configuratieregisters op bij het aanmaken van de instantie.
        """
        self.statuses = {}
        self.configs = self.init_configs()

    @classmethod
    def _create_config_entry(cls, path_config: Path) -> dict:
        try:
            genesis_config = GenesisConfig(file_config=path_config, create_version_dir=False)
            return {
                "path_config": path_config.name,
                "dir_output": genesis_config.path_intermediate_root,
                "exists_output": genesis_config.path_intermediate_root.exists(),
                "created": datetime.fromtimestamp(path_config.stat().st_ctime),
                "modified": datetime.fromtimestamp(path_config.stat().st_mtime),
                "runner": GenesisRunner(path_config=path_config),
            }
        except Exception as e:
            logger.error(f"Fout bij het verwerken van {path_config.name}: {str(e)}")
            raise

    @classmethod
    def init_configs(cls):
        """Scant de configuratiemap en initialiseert alle gevonden configuratiebestanden.

        Zoekt naar YAML-configuratiebestanden in de configuratiemap en maakt voor elk bestand een
        configuratie-informatie dictionary aan. Logt fouten bij het verwerken van individuele bestanden.

        Returns:
            dict: Een dictionary met configuratiebestandsnamen als sleutels en hun metadata als waarden.
        """
        paths_config = [
                f
                for f in cls.CONFIG_DIR.iterdir()
                if f.is_file() and f.suffix.lower() in [".yaml", ".yml"]
            ]

        result = {}
        for path_config in paths_config:
            try:
                result[path_config.name] = cls._create_config_entry(path_config)
            except Exception:
                continue
        return result

    def refresh(self) -> None:
        """Vernieuwt het configuratieregister met de laatste configuratiebestanden.

        Laadt alle configuratiebestanden opnieuw in en werkt het register bij.
        """
        with self._lock:
            self.configs = self.init_configs()
            logger.info("Config registry refreshed.")

    def delete(self, filename: str) -> None:
        """Verwijdert een configuratiebestand uit het register.

        Zoekt het opgegeven configuratiebestand en verwijdert het uit het register en
        de statuslijst. Logt het resultaat van de verwijderactie.

        Args:
            filename: De naam van het configuratiebestand dat verwijderd moet worden.
        """
        with self._lock:
            if filename in self.configs:
                del self.configs[filename]
                if filename in self.statuses:
                    del self.statuses[filename]
                logger.info(f"Configuratiebestand {filename} verwijderd uit register.")
            else:
                logger.warning(f"Configuratiebestand {filename} niet gevonden in register.")

    def get_configs(self) -> list[dict]:
        """Geeft een lijst terug met alle configuratie-informatie in het register.

        Retourneert de waarden van het configuratieregister als een lijst van configuratiedictionaries.

        Returns:
            list[dict]: Een lijst met configuratie-informatie dictionaries.
        """
        with self._lock:
            return list(self.configs.values())

    def get_config(self, filename: str) -> dict | None:
        """Geeft de configuratie-informatie terug voor het opgegeven bestand.

        Zoekt de configuratie op basis van de bestandsnaam en retourneert de bijbehorende dictionary.
        Geeft een KeyError als het bestand niet bestaat.

        Args:
            filename: De naam van het configuratiebestand waarvan de informatie wordt opgevraagd.

        Returns:
            dict: De configuratie-informatie dictionary.

        Raises:
            KeyError: Als het configuratiebestand niet gevonden is in het register.
        """
        with self._lock:
            config = self.configs.get(filename)
            if config is None:
                raise KeyError(f"Configuratiebestand {filename} niet gevonden in register.")
            return config

    def get_config_runner(self, filename: str) -> GenesisRunner | None:
        """Geeft de GenesisRunner-instantie terug voor het opgegeven configuratiebestand.

        Zoekt de runner behorend bij de opgegeven bestandsnaam en retourneert deze, of None als het bestand niet bestaat.

        Args:
            filename: De naam van het configuratiebestand waarvan de runner wordt opgevraagd.

        Returns:
            GenesisRunner | None: De GenesisRunner-instantie of None als het bestand niet gevonden is.
        """
        with self._lock:
            config = self.configs.get(filename)
            return config.get("runner") if config else None

    def update_status(self, filename, status) -> None:
        """Werk de status bij van een configuratiebestand in het register.

        Stelt de status in voor het opgegeven configuratiebestand in de statuslijst.

        Args:
            filename: De naam van het configuratiebestand waarvan de status wordt bijgewerkt.
            status: De nieuwe statuswaarde voor het configuratiebestand.
        """
        with self._lock:
            self.statuses[filename] = status

    def config_runner_status(self, filename: str) -> str | None:
        """Geeft de status van de GenesisRunner voor het opgegeven configuratiebestand terug.

        Zoekt de runner bij het opgegeven bestand en retourneert de statusstring, of None als het bestand of de runner niet bestaat.

        Args:
            filename: De naam van het configuratiebestand waarvan de runnerstatus wordt opgevraagd.

        Returns:
            str | None: De status van de GenesisRunner, of None als het bestand of de runner niet gevonden is.
        """
        with self._lock:
            if config := self.configs.get(filename):
                runner = config.get("runner")
                return runner.status() if runner else None
            return None

    def add(self, file_config: str) -> None:
        """Voegt een nieuw configuratiebestand toe aan het register.

        Controleert of het opgegeven bestand bestaat en voegt het toe aan het configuratieregister met bijbehorende metadata.
        Logt waarschuwingen of fouten als het bestand niet gevonden of niet toegankelijk is.

        Args:
            file_config: De naam van het toe te voegen configuratiebestand.

        Raises:
            FileNotFoundError: Als het configuratiebestand niet bestaat.
        """
        try:
            self._create_config_entry(file_config)
        except OSError as e:
            logger.warning(f"Configuratiebestand '{file_config}' niet gevonden of niet toegankelijk tijdens toevoegen: {e}")
        except Exception as e:
            logger.error(f"Onverwachte fout bij toevoegen van configuratiebestand '{file_config}': {e}")

        with self._lock:
            path_config = self.CONFIG_DIR / file_config
            if not path_config.exists():
                logger.error(f"Configuratiebestand {file_config} bestaat niet.")
                raise FileNotFoundError(f"Configuratiebestand {file_config} bestaat niet.")
            self.configs[path_config.name] = self._create_config_entry(path_config)
            logger.info(f"Configuratiebestand {file_config} toegevoegd aan register.")

    def get_status_all(self) -> list[dict]:
        """Geeft de statusinformatie van alle configuratiebestanden in het register terug.

        Retourneert een lijst met de configuratie-informatie dictionaries van alle geregistreerde configuratiebestanden.

        Returns:
            list[dict]: Een lijst met configuratie-informatie dictionaries.
        """
        with self._lock:
            return list(self.configs.values())
