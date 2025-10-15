import threading
from datetime import datetime
from pathlib import Path

from genesis_runner import GenesisRunner
from config import GenesisConfig
from logtools import get_logger

logger = get_logger(__name__)

class ConfigRegistry:
    """Beheert het register van configuratiebestanden en hun metadata."""
    _instance = None
    CONFIG_DIR = Path("configs").resolve()
    _lock = threading.Lock()
    statuses = {}  # {filename: 'idle' | 'running' | 'finished'}

    def __new__(cls):
        """Maakt een thread-safe singleton-instantie van het configuratieregister aan."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(ConfigRegistry, cls).__new__(cls)
                    cls._instance.configs = cls.init_configs()
        return cls._instance

    @classmethod
    def init_configs(cls):
        """Initialiseert en retourneert een dictionary van configuratiebestanden en hun metadata."""
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

    def refresh(self):
        """Ververst de configuratie dictionary door de config map opnieuw te scannen."""
        with self._lock:
            self.configs = self.init_configs()
            logger.info("Config registry refreshed.")

    def delete(self, filename: str):
        """Verwijdert een configuratiebestand uit het register."""
        with self._lock:
            if filename in self.configs:
                del self.configs[filename]
                if filename in self.statuses:
                    del self.statuses[filename]
                logger.info(f"Configuratiebestand {filename} verwijderd uit register.")
            else:
                logger.warning(f"Configuratiebestand {filename} niet gevonden in register.")

    def get_configs(self) -> list[dict]:
        return self.configs.values()

    def get_config(self, filename: str) -> dict:
        """Haalt de configuratie-informatie op voor een opgegeven bestandsnaam."""
        return self.configs.get(filename)

    def get_config_runner(self, filename: str) -> GenesisRunner | None:
        """Geeft de GenesisRunner-instantie terug voor een opgegeven configuratiebestand."""
        config = self.configs.get(filename)
        return config.get("runner") if config else None

    def update_status(self, filename, status):
        self.statuses[filename] = status

    def config_runner_status(self, filename: str) -> str | None:
        config = self.configs.get(filename)
        if config:
            runner = config.get("runner")
            return runner.status() if runner else None
        return None

    def add(self, file_config: str) -> None:
        """Voegt een nieuw configuratiebestand toe aan het register als het bestaat."""
        with self._lock:
            path_config = self.CONFIG_DIR / file_config
            if not path_config.exists():
                logger.error(f"Configuratiebestand {file_config} bestaat niet.")
                return
            genesis_config = GenesisConfig(file_config=path_config, create_version_dir=False)
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
            logger.info(f"Configuratiebestand {file_config} toegevoegd aan register.")

    def get_status_all(self) -> list[dict]:
        return list(self.configs.values())
