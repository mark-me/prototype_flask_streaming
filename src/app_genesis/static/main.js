const consoleBox = document.getElementById("console");
const evtSource = new EventSource("/stream");

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
            consoleBox.innerHTML += line + "<br>";
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
