const consoleBox = document.getElementById("console");
const evtSource = new EventSource("/stream");

evtSource.onmessage = function(event) {
    consoleBox.innerHTML += event.data + "<br/>";
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
