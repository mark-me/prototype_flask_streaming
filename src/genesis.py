import argparse
import sys
from time import sleep
from tqdm import tqdm

from logtools import get_logger

BOLD_GREEN = "\x1b[1;92m"
BOLD_RED = "\x1b[1;91m"
BOLD_BLUE = "\x1b[1;94m"
BOLD_CYAN = "\x1b[1;96m"
BOLD_MAGENTA = "\x1b[1;95m"
BOLD_YELLOW = "\x1b[1;93m"
UNDERLINE = "\x1b[4m"
RESET = "\x1b[0m"

logger = get_logger(__name__)

def main():
    """
    Start het Genesis orkestratieproces via de command line interface.

    Ontleedt command line argumenten, initialiseert de Orchestrator klasse met het opgegeven configuratiebestand en start de verwerking.
    """
    parser = argparse.ArgumentParser(description="De Genesis workflow orkestrator")
    print(
        f"""{BOLD_GREEN}\n
     _____                      _
    / ____|                    (_)
   | |  __  ___ _ __   ___  ___ _ ___
   | | |_ |/ _ \\ '_ \\ / _ \\/ __| / __|
   | |__| |  __/ | | |  __/\\__ \\ \\__ \\
    \\_____|\\___|_| |_|\\___||___/_|___/
                           MDDE{RESET}
    """,
        file=sys.stdout,
    )
    parser.add_argument("config_file", help="Locatie van een configuratiebestand")
    parser.add_argument(
        "-s", "--skip", action="store_true", help="Sla DevOps deployment over"
    )
    args = parser.parse_args()

    print(
        f"{BOLD_CYAN}{UNDERLINE}Start Genesis verwerking{RESET}",
        file=sys.stdout,
    )

    logger.info("Dit is logger info")
    logger.warning("Dit is een logger waarschuwing")
    logger.error("Dit is logger error")


    for _ in tqdm(range(0, 50), desc="Progress 1", colour="blue"):
        sleep(0.1)
    for _ in tqdm(range(0, 25), desc="Progress 2", colour="magenta"):
        sleep(0.1)

    lst_answers_yes = ["", "J", "JA", "JAWOHL", "Y", "YES"]
    lst_answers_no = ["N", "NEE", "NEIN", "NO"]
    while True:
        msg = (
            f"{BOLD_YELLOW}Waarschuwingen gevonden, wil je doorgaan? (J/n):{RESET}"
        )
        print(msg, file=sys.stdout)
        answer = input(msg)
        if answer.upper() in lst_answers_no:
            print(
                f"{BOLD_RED}'We gaan niet door!{RESET}",
                file=sys.stdout,
            )
        elif answer.upper() in lst_answers_yes:
            break
        else:
            print(
                f"{BOLD_RED}'{answer}' behoort niet tot de mogelijke antwoorden (j/n).{RESET}",
                file=sys.stdout,
            )

    for i in range(25):
        print(
                f"{BOLD_MAGENTA}'{i}' regels.{RESET}",
                file=sys.stdout,
            )

    print(f"{BOLD_BLUE}Afgerond zonder fouten.{RESET}", file=sys.stdout)


if __name__ == "__main__":
    main()
