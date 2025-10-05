document.addEventListener("DOMContentLoaded", function() {
    const consoleBox = document.getElementById("console");
    const questionButtons = document.getElementById("question-buttons");
    const downloadButton = document.getElementById("download-button");
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

    // Functie om UI te updaten op basis van status
    function updateUI(status) {
        if (status === "asking_question") {
            questionButtons.style.display = "flex";  // Gebruik flex voor gap-2 in HTML
            downloadButton.style.display = "none";
        } else if (status === "finished") {
            questionButtons.style.display = "none";
            // Vul download-knop met link (pas outputDir aan als nodig)
            const outputDir = configFile.replace(".yml", "_output");  // Bijv. 'mijnconfig_output'
            downloadButton.innerHTML = `
                <a href="/browser/browse/${encodeURIComponent(outputDir)}" class="btn btn-primary" target="_blank">
                    <i class="bi bi-folder-open"></i> Resultaten verkennen
                </a>
            `;
            downloadButton.style.display = "block";
            evtSource.close();  // Sluit SSE na finish
        } else {
            questionButtons.style.display = "none";
            downloadButton.style.display = "none";
        }
        console.log("UI update:", status);
    }

    evtSource.onmessage = function(event) {
        let line = event.data.trim();
        if (line === "" || line.startsWith(":")) {
          return;
        }  // Skip empty/heartbeats

        // Parse speciale status-berichten (backend formaat: "awaiting_input|filename" of "finished|filename")
        if (line.startsWith("awaiting_input|")) {
            updateUI("asking_question");
            appendLine('<span class="text-warning">Wachten op input... (prompt zichtbaar in output)</span>');
            return;
        } else if (line.startsWith("finished|")) {
            updateUI("finished");
            appendLine('<span class="text-success">Proces voltooid!</span>');
            return;
        } else if (line.startsWith("idle|")) {
            appendLine('<span class="text-muted">Geen activiteit...</span>');
            return;
        }

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

    // Globale sendInput voor onclick in HTML
    window.sendInput = function(value) {
        fetch("/runner/send_input", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ filename: configFile, answer: value })  // Backend verwacht 'answer'
        })
        .then(resp => resp.json())
        .then(data => {
            if (data.status === "ok") {
                const answerText = value === "J" ? "Ja" : "Nee";
                appendLine(`<span class="text-info">Ingevoerd: ${answerText}</span>`);
                updateUI("");  // Reset UI (verberg knoppen tot nieuwe prompt)
                consoleBox.scrollTop = consoleBox.scrollHeight;
            } else {
                alert("Fout bij verzenden: " + data.message);
            }
        })
        .catch(err => {
            console.error("Fetch error:", err);
            alert("Netwerkfout bij input.");
        });
    };
});