let modalInstance = null;
let pollInterval = null;

/**
 * Start het periodiek ophalen van statusupdates van de server.
 * Deze functie roept de opgegeven callback aan met de nieuwste statusgegevens op een vast interval.
 *
 * Args:
 *   statusUrl: De URL waar de statusinformatie wordt opgehaald.
 *   onStatusUpdate: Callbackfunctie die wordt aangeroepen met de opgehaalde statusdata.
 *   pollTime: Het interval in milliseconden tussen opeenvolgende statusverzoeken (standaard 1000 ms).
 */
export function startPolling(statusUrl, onStatusUpdate, pollTime = 1000) {
    stopPolling();
    pollInterval = setInterval(async () => {
        try {
            const response = await fetch(statusUrl);
            if (!response.ok) {
              throw new Error('Polling failed');
            }
            const data = await response.json();
            onStatusUpdate(data);
        } catch (err) {
            console.error('Error during polling:', err);
        }
    }, pollTime);
}

/**
 * Stopt het periodiek ophalen van statusupdates door de polling-interval te wissen.
 * Deze functie zorgt ervoor dat er geen verdere statusverzoeken meer worden uitgevoerd.
 */
export function stopPolling() {
    if (pollInterval) {
        clearInterval(pollInterval);
        pollInterval = null;
    }
}

/**
 * Toont een modale dialoogvenster aan de gebruiker met een bestandsnaam en optionele prompttekst.
 * Deze functie initialiseert de modal indien nodig en stelt de weergegeven tekst in voordat de modal wordt getoond.
 *
 * Args:
 *   filename: De naam van het bestand die in de modal wordt weergegeven.
 *   promptText: De tekst die als prompt aan de gebruiker wordt getoond (optioneel).
 */
export function showModal(filename, promptText) {
    const modalEl = document.getElementById('inputModal');
    if (!modalEl) {
        console.error('Modal element not found!');
        return;
    }

    if (!modalInstance) {
        modalInstance = new bootstrap.Modal(modalEl, { backdrop: 'static', keyboard: false });
    }

    document.getElementById('modal-filename').innerText = filename;
    document.getElementById('modal-prompt').innerText = promptText || 'Input vereist.';
    modalInstance.show();
}

/**
 * Stuurt de invoer van de gebruiker vanuit de modal naar de server met een POST-verzoek.
 * Sluit de modal na het verzenden van de invoer en retourneert de serverrespons.
 *
 * Args:
 *   filename: De naam van het bestand of de resource waarvoor de invoer wordt verzonden.
 *   answer: De gebruikersinvoer die naar de server wordt gestuurd.
 *   postUrl: De basis-URL waarnaar de invoer gepost moet worden.
 *
 * Returns:
 *   De geparseerde JSON-respons van de server als het verzoek succesvol is.
 *
 * Raises:
 *   Gooit een fout als het netwerkverzoek mislukt of de respons niet OK is.
 */
export async function sendModalInput(filename, answer, postUrl) {
    try {
        const response = await fetch(`${postUrl}/${filename}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ answer })
        });
        if (!response.ok) {
          throw new Error('Failed to send input');
        }
        const data = await response.json();
        hideModal();
        return data;
    } catch (err) {
        console.error('Error sending modal input:', err);
        hideModal();
    }
}


/**
 * Verbergt de momenteel weergegeven modale dialoog.
 * Deze functie sluit de modal als deze momenteel open is.
 */
export function hideModal() {
    if (modalInstance) {
        modalInstance.hide();
    }
}


/**
 * Stelt het opruimen van de modal in wanneer deze wordt gesloten.
 * Zorgt ervoor dat bronnen worden vrijgegeven en de modal-instantie wordt gereset nadat de modal is gesloten.
 */
export function setupModalCleanup() {
    const modalElement = document.getElementById('inputModal');
    if (modalElement) {
        modalElement.addEventListener('hidden.bs.modal', () => {
            if (modalInstance) {
                modalInstance.dispose();
                modalInstance = null;
            }
        });
    }
}
