let modalInstance = null;
let pollInterval = null;
let broadcastChannel = null;  // Nieuw: voor inter-tab communicatie
let isFocused = true;  // Nieuw: track focus status van dit tabblad

// ... (bestaande functies: startPolling, stopPolling blijven ongewijzigd)

/**
 * Initialiseert de BroadcastChannel en focus-listeners voor tab-synchronisatie.
 * Roep dit aan in DOMContentLoaded op elke pagina.
 */
export function initTabSync() {
    // Maak een channel voor modal-events (uniek per app)
    broadcastChannel = new BroadcastChannel('genesis-modal-channel');

    // Detecteer wanneer dit tabblad focus krijgt/verliest
    window.addEventListener('focus', () => {
        isFocused = true;
        // Broadcast dat dit tabblad nu focused is
        if (broadcastChannel) {
            broadcastChannel.postMessage({ type: 'tab-focused', tabId: getTabId() });
        }
    });

    window.addEventListener('blur', () => {
        isFocused = false;
    });

    // Luister naar broadcasts van andere tabs
    if (broadcastChannel) {
        broadcastChannel.addEventListener('message', (event) => {
            const { type, tabId } = event.data;
            if (type === 'show-modal' && isFocused && tabId !== getTabId()) {
                // Alleen tonen als dit tabblad focused is EN niet de sender
                showModal(event.data.filename, event.data.promptText);
            } else if (type === 'tab-focused') {
                // Update lokale focus als een ander tabblad focus claimt
                if (tabId !== getTabId()) {
                    isFocused = false;
                }
            }
        });
    }
}

/**
 * Genereert een unieke ID voor dit tabblad (gebaseerd op timestamp + random).
 * Gebruikt voor onderscheid in broadcasts.
 */
function getTabId() {
    if (!window.genesisTabId) {
        window.genesisTabId = Date.now() + '-' + Math.random().toString(36).substr(2, 9);
    }
    return window.genesisTabId;
}

/**
 * Uitgebreide showModal: checkt focus en broadcast als nodig.
 * Args: dezelfde als voorheen, plus optioneel { broadcast: true } om naar andere tabs te sturen.
 */
export function showModal(filename, promptText, options = {}) {
    const modalEl = document.getElementById('inputModal');
    if (!modalEl) {
        console.error('Modal element not found!');
        return;
    }

    // Als broadcast gewenst, stuur naar alle tabs (maar toon lokaal alleen als focused)
    if (options.broadcast && broadcastChannel) {
        broadcastChannel.postMessage({
            type: 'show-modal',
            filename,
            promptText,
            tabId: getTabId()
        });
        // Toon lokaal alleen als dit tabblad focused is
        if (!isFocused) {
            console.log('Modal event broadcast, maar dit tabblad is niet focused.');
            return;  // Skip lokale show
        }
    }

    // Normale show-logica (als niet broadcast of lokaal focused)
    if (!modalInstance) {
        modalInstance = new bootstrap.Modal(modalEl, { backdrop: 'static', keyboard: false });
    }

    document.getElementById('modal-filename').innerText = filename;
    document.getElementById('modal-prompt').innerText = promptText || 'Input vereist.';
    modalInstance.show();
}

// ... (bestaande functies: sendModalInput, hideModal, setupModalCleanup blijven ongewijzigd)

// Update setupModalCleanup om ook tab-sync te initialiseren
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
    // Nieuw: Initialiseer tab-sync
    initTabSync();
}