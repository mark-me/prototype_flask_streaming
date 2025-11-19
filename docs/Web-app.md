# Genesis Web Interface

![Webapp](images/web-app.png){ align=right width="90" }

De Genesis Web Interface biedt een gebruiksvriendelijke manier om het krachtige Genesis-systeem te bedienen zonder dat je ooit een terminal hoeft te openen. Deze interface combineert moderne webtechnologieën met een retro console-ervaring, zodat je de dagelijkse workflow eenvoudiger en efficiënter kunt beheren.

Of je nu configuraties wilt aanpassen, de uitvoer van Genesis in real-time wilt volgen, of direct bestanden wilt bewerken, de interface biedt alles wat je nodig hebt, direct vanuit je browser. Met een intuïtieve interface en slimme functies zoals automatische invoermodals en een realtime bestandsbrowser, is Genesis Web Interface ontworpen om de interactie met Genesis eenvoudiger en sneller te maken.

## Overzicht

De Genesis Web Interface is een moderne, gebruiksvriendelijke webapplicatie waarmee je volledig zonder terminal het Genesis-proces kunt:

* Configuratiebestanden (YAML) aanmaken, bewerken, kopiëren en verwijderen
* Genesis starten op basis van een gekozen config
* Live de uitvoer volgen in een retro CRT-stijl console (met kleuren en tqdm-ondersteuning)
* Interactief invoer geven wanneer Genesis daarom vraagt (bijv. “Doorgaan? (j/n)”)
* Alle gegenereerde bestanden direct bekijken, downloaden of bewerken (HTML, JSON, CSV, SQL, etc.)

## Samenvatting van de volledige ervaring

1. Open de app → mooie welkomstpagina met stappenplan
2. Kies/bewerk config → Codemirror met donkere theme
3. Start Genesis → word je direct naar retro console gestuurd
4. Volg live uitvoer (met tqdm-bars die netjes updaten)
5. Wordt er iets gevraagd → modal verschijnt automatisch (zelfs in achtergrondtab)
6. Proces klaar → klik op map-icoontje bij de config → verken alle output in de mooie bestandsbrowser
7. Open HTML-rapporten, bewerk CSV’s, download alles wat je nodig hebt

Alles werkt zonder pagina-verversingen waar mogelijk (SSE + polling), waardoor de ervaring vloeiend is.

## Functionaliteit

### Configuratiebeheer

* Nieuwe config aanmaken op basis van bestaande (kopiëren)
* Direct bewerken met CodeMirror (donkere theme)
* “Opslaan als…” functionaliteit
* Verwijderen met bevestigingsmodal

### Live Uitvoering

* Eén klik → Genesis start
* Automatische redirect naar retro console
* Live uitvoer met kleuren (ansi2html)
* Progress bars (tqdm) worden netjes overschreven
* Interactieve vragen → modal met invoerveld of Ja/Nee-knoppen

### Bestandsbrowser

* secure_path() in zowel browser als andere routes → voorkomt directory traversal
* Subprocess draait met text=True, bufsize=0 → echte real-time uitvoer
* Geen authenticatie (bedoeld voor lokale/intern gebruik)
* Alle invoer wordt veilig verwerkt

## Technische Architectuur

```bash
app/
── app.py                    → Hoofd Flask-applicatie + routes (/, /about)
├── genesis_runner.py        → Subprocess-wrapper rond genesis.py
├── configs_registry.py      → Singleton-register van alle configs + runners
├── secure_path.py           → Beveiliging tegen directory traversal
├── routes/
    ├── browser.py           → Volledige bestandsbrowser (/browser)
    ├── config_handler.py    → CRUD voor YAML-configs
    └── runner.py            → Starten, streamen, status & input van Genesis
```

### Belangrijkste componenten

| **Component**      | **Functie**                                                                               |
|--------------------|-------------------------------------------------------------------------------------------|
| ConfigRegistry     | Houdt alle .yaml/.yml bestanden in configs/ bij + maakt automatisch een GenesisRunner aan |
| GenesisRunner      | Start python src/genesis.py <config>. Real-time uitvoer. Detecteert automatisch prompts   |
| Bestandsbrowser    | Volledige file manager met breadcrumb, sortering en bewerkbare CSV’s                      |
| Live Streaming     | Server-Sent Events (SSE) + ansi2html + tqdm-ondersteuning                                 |

## Gebruikersinterface

### Belangrijkste pagina’s

| **Pagina**        | **Beschrijving**                                                              |
|-------------------|-------------------------------------------------------------------------------|
| Home (/)          | Welkomstscherm + overzicht alle configuraties (sorteerbaar)                   |
| Runner            | Live retro console + automatische invoermodal                                 |
| Bestandsbrowser   | Verken uitvoermappen, open rapporten, bewerk CSV’s                            |
| Config-editor     | CodeMirror (material-darker) voor YAML                                        |
| Nieuwe config     | Kopieer bestaande config als startpunt                                        |

## Interactieve invoer

Wanneer Genesis een vraag stelt:

1. Backend markeert status als awaiting_input
2. Frontend poll elke seconde /runner/status
3. Bij nieuwe prompt → modal verschijnt automatisch
4. BroadcastChannel zorgt dat slechts één tabblad de modal toont (werkt ook met meerdere tabs open)
5. Antwoord → POST naar /runner/input/<config>
6. Proces gaat direct verder

→ Werkt zelfs als het tabblad op de achtergrond staat.

## Frontend – Templates & JavaScript

### Templates

| **Template**      | **Doel**                                                                      |
|-------------------|-------------------------------------------------------------------------------|
| base.html         | Basislayout + Bootstrap 5 + iconen                                            |
| index.html        | Home met stappenplan                                                          |
| runner.html       | Retro console + modal                                                         |
| browser.html      | Bestandsbrowser met sortering                                                 |
| file_editor.html  | YAML-editor                                                                   |
| edit_csv.html     | Bewerkbare CSV-tabel (Tabulator.js)                                           |
| about.html        | Informatie over de app                                                        |

### JavaScript (static/js/)

| **Bestand**       | **Functie**                                                                   |
|-------------------|-------------------------------------------------------------------------------|
| runner.js         | Live streaming via Server-Sent Events (SSE), Ontvangt uitvoer van /runner/stream/<config> + tqdm-ondersteuning + autoscroll |
| modal.js          | Polling, prompt-detectie, tab-synchronisatie via BroadcastChannel             |
| close_window.js   | Venster sluiten (CSV pop-up)                                                  |
