const consoleBox = document.getElementById("console");
const evtSource = new EventSource("/stream");

// Functie om de knoppen aan te passen op basis van de status
/*
function updateUI(status) {
    const questionButtons = document.getElementById("question-buttons");
    const downloadButton = document.getElementById("download-button");

    if (status === 'asking_question') {
        questionButtons.style.display = "block";  // Toon de vraag-knoppen
        downloadButton.style.display = "none";  // Verberg de download-knop
    } else if (status === 'finished') {
        questionButtons.style.display = "none";  // Verberg de vraag-knoppen
        downloadButton.style.display = "block";  // Toon de download-knop
    }
}
*/

evtSource.onmessage = function(event) {
        const line = event.data;

        // tqdm updates (met carriage returns) → vervang laatste regel i.p.v. toevoegen
        if (line.includes("%|")) {  // voorbeeld: voortgang
            // overschrijf laatste regel
            let lines = consoleBox.innerHTML.split("<br>");
            lines[lines.length - 1] = line;
            consoleBox.innerHTML = lines.join("<br>");
        } else {
            // gewone nieuwe regel toevoegen
            consoleBox.innerHTML += "<br>" + line;
        }

        consoleBox.scrollTop = consoleBox.scrollHeight;
    };
/**
 * Sends user input to the server via a POST request.
 * This function transmits the provided value as JSON to the "/input" endpoint.
 *
 * Args:
 *   value: The input value to be sent to the server.
 */
function sendInput(value) {
    fetch("/input", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({value: value})
    });
}
