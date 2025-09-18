import argparse
import sys
from time import sleep
from tqdm import tqdm

BOLD_GREEN = "\x1b[1;32m"
BOLD_RED = "\x1b[1;31m"
BOLD_BLUE = "\x1b[1;34m"
UNDERLINE = "\x1b[4m"
BOLD_YELLOW = "\x1b[1;33m"
RESET = "\x1b[0m"


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

    for _ in tqdm(
        range(0, 100),
        desc="Text You Want",
        colour="yellow"
    ):
        sleep(0.1)

    lst_answers_yes = ["", "J", "JA", "JAWOHL", "Y", "YES"]
    lst_answers_no = ["N", "NEE", "NEIN", "NO"]
    while True:
        msg = (
            f"{BOLD_YELLOW}Waarschuwingen gevonden, wil je doorgaan met? (J/n):{RESET}"
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

    print(f"{BOLD_GREEN}Afgerond zonder fouten.{RESET}", file=sys.stdout)


if __name__ == "__main__":
    main()
