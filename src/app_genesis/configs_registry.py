import threading
from datetime import datetime
from pathlib import Path

from genesis_runner import GenesisRunner

from config import GenesisConfig
from logtools import get_logger

logger = get_logger(__name__)

class ConfigRegistry:
    """Beheert het register van configuratiebestanden en hun metadata.

    Deze klasse implementeert een singleton die configuratiebestanden opspoort, registreert en bijwerkt.
    """
    _instance = None
    CONFIG_DIR = Path("configs").resolve()
    _lock = threading.Lock()

    def __new__(cls):
        """Maakt een thread-safe singleton-instantie van het configuratieregister aan.

        Deze methode zorgt ervoor dat er slechts één instantie van het register bestaat en initialiseert de configuraties.

        Returns:
            ConfigRegistry: De singleton-instantie van het configuratieregister.
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(ConfigRegistry, cls).__new__(cls)
                    cls._instance.configs = cls.init_configs()
        return cls._instance

    @classmethod
    def init_configs(cls):
        """Initialiseert en retourneert een dictionary van configuratiebestanden en hun metadata.

        Deze methode doorzoekt de configuratiemap naar YAML-bestanden en verzamelt relevante informatie voor elk bestand.

        Returns:
            dict: Een dictionary waarbij elke sleutel een configuratiebestandsnaam is en elke waarde een dictionary bevat
                met het pad, de uitvoermap, de status van het uitvoerbestand, aanmaak- en wijzigingsdatum, en een runner-instantie.
        """
        paths_config = [
            f
            for f in cls.CONFIG_DIR.iterdir()
            if f.is_file() and f.suffix.lower() in [".yaml", ".yml"]
        ]

        result = {}
        for path_config in paths_config:
            genesis_config = GenesisConfig(file_config=path_config, create_version_dir=False)
            result[path_config.name] = {
                "path_config": path_config.name,
                "dir_output": genesis_config.path_intermediate_root,
                "exists_output": genesis_config.path_intermediate_root.exists(),
                "created": datetime.fromtimestamp(path_config.stat().st_ctime),
                "modified": datetime.fromtimestamp(path_config.stat().st_mtime),
                "runner": GenesisRunner(path_config=path_config),
            }
        return result

    def get(self, filename: str) -> dict:
        return self.configs.get(filename)

    def add(self, file_config: str) -> None:
        """Voegt een nieuw configuratiebestand toe aan het register als het bestaat.

        Deze methode controleert of het opgegeven bestand aanwezig is en werkt het register bij met de nieuwe configuratie.

        Args:
            file_config (str): De naam van het toe te voegen configuratiebestand.
        """
        with self._lock:
            path_config = self.CONFIG_DIR / file_config
            if not path_config.exists():
                logger.error(f"Configuratiebestand {file_config} bestaat niet.")
                return
            genesis_config = GenesisConfig(
                file_config=path_config, create_version_dir=False
            )
            self.configs.update(
                {
                    path_config.name: {
                        "path_config": path_config.name,
                        "dir_output": genesis_config.path_intermediate_root,
                        "exists_output": genesis_config.path_intermediate_root.exists(),
                        "created": datetime.fromtimestamp(path_config.stat().st_ctime),
                        "modified": datetime.fromtimestamp(path_config.stat().st_mtime),
                        "runner": GenesisRunner(path_config=path_config),
                    }
                }
            )

    def get_status_all(self) -> list[dict]:
        return list(self.configs.values())


if __name__ == "__main__":
    config_registry = ConfigRegistry()
    lst_config = config_registry.get_status_all()
    print(config_registry.configs)
    config_registry.add(file_config="config3.yaml")
    print(config_registry.configs)
