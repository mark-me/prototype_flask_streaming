# log_manager.py
import logging
import logging.config
from .log_config import get_logging_config
from .issue_tracking import IssueTrackingHandler


# Set up issue tracker handler (shared across all modules)
issue_tracker = IssueTrackingHandler()

def get_logger(name: str, dir_output: str, base_file: str) -> logging.Logger:
    """Haalt een logger-instantie op aan de hand van een naam.

    Deze functie vereenvoudigt het ophalen van een logger en zorgt voor
    een consistente configuratie volgens de logging-instellingen van het project.

    Args:
        name: De naam van de logger die opgehaald moet worden.

    Retourneert:
        Een logger-instantie met de opgegeven naam.
    """
    logging.config.dictConfig(get_logging_config(dir_output = dir_output, base_file = base_file))
    logger = logging.getLogger(name)
    logger.addHandler(issue_tracker)
    return logger
