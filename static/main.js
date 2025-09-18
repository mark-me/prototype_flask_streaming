const consoleBox = document.getElementById("console");
const evtSource = new EventSource("/stream");

evtSource.onmessage = function(event) {
    consoleBox.innerHTML += event.data + "<br/>";
    consoleBox.scrollTop = consoleBox.scrollHeight;
};

function sendInput(value) {
    fetch("/input", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({value: value})
    });
}
