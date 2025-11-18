document.addEventListener("DOMContentLoaded", function() {
    const consoleBox = document.getElementById("console");
    const configFile = document.getElementById("config").dataset.filename;

    if (!configFile) {
        console.error("Geen config-filename gevonden!");
        return;
    }

    const evtSource = new EventSource(`/runner/stream/${encodeURIComponent(configFile)}`);

    // Functie om de laatste console-lijn te updaten (voor tqdm/CR)
    function updateLastLine(newLine) {
        const lines = consoleBox.querySelectorAll(".console-line");
        if (lines.length > 0) {
            lines[lines.length - 1].innerHTML = newLine;
        } else {
            appendLine(newLine);
        }
    }

    // Functie om een nieuwe lijn toe te voegen
    function appendLine(line) {
        const div = document.createElement("div");
        div.className = "console-line mb-1";  // Kleine margin voor leesbaarheid
        div.innerHTML = line;
        consoleBox.appendChild(div);
    }

    evtSource.onmessage = function(event) {
        let line = event.data.trim();
        if (line === "" || line.startsWith(":")) {
            return;
        }  // Skip empty/heartbeats

        // Normale output of tqdm
        if (line.includes("%|")) {  // tqdm/CR detectie
            updateLastLine(line);
        } else {
            appendLine(line);
        }

        consoleBox.scrollTop = consoleBox.scrollHeight;
    };

    evtSource.onerror = function(err) {
        console.error("SSE error:", err);
        appendLine('<span class="text-danger">Connectie verloren. Herlaad de pagina om te hervatten.</span>');
        // Optioneel: reconnect na 5s
        // setTimeout(() => { evtSource = new EventSource(...); }, 5000);
    };

});