// modal.js – Globale versie (geen exports)
let modalInstance = null;
let pollInterval = null;
let broadcastChannel = null;
let isFocused = true;

function startPolling(statusUrl, onStatusUpdate, pollTime = 1000) {
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

function stopPolling() {
    if (pollInterval) {
        clearInterval(pollInterval);
        pollInterval = null;
    }
}

function initTabSync() {
    broadcastChannel = new BroadcastChannel('genesis-modal-channel');

    window.addEventListener('focus', () => {
        isFocused = true;
        console.log('TAB FOCUS GEKREGEN – isFocused = true');  // <-- Nieuwe log
        if (broadcastChannel) {
            broadcastChannel.postMessage({ type: 'tab-focused', tabId: getTabId() });
        }
    });

    window.addEventListener('blur', () => {
        isFocused = false;
        console.log('TAB BLUR – isFocused = false');  // <-- Nieuwe log
    });

    // Initial focus check
    if (document.hasFocus()) {
        isFocused = true;
        console.log('Initial: TAB IS FOCUSED');
    } else {
        console.log('Initial: TAB IS NOT FOCUSED');
    }

    if (broadcastChannel) {
        broadcastChannel.addEventListener('message', (event) => {
            const { type, tabId } = event.data;
            console.log('Broadcast ontvangen:', type, 'van tab', tabId);  // <-- Log
            if (type === 'show-modal' && isFocused && tabId !== getTabId()) {
                console.log('Toon modal via broadcast (focused)');
                showModal(event.data.filename, event.data.promptText);
            } else if (type === 'tab-focused') {
                if (tabId !== getTabId()) {
                    isFocused = false;
                    console.log('Ander tab focused – zet isFocused = false');
                }
            }
        });
    }
}

function getTabId() {
    if (!window.genesisTabId) {
        window.genesisTabId = Date.now() + '-' + Math.random().toString(36).substr(2, 9);
    }
    return window.genesisTabId;
}

function showModal(filename, promptText, options = {}) {
    const modalEl = document.getElementById('inputModal');
    if (!modalEl) {
        console.error('Modal element not found!');
        return;
    }

    if (options.broadcast && broadcastChannel) {
        broadcastChannel.postMessage({
            type: 'show-modal',
            filename,
            promptText,
            tabId: getTabId()
        });
        if (!isFocused) {
            console.log('Modal event broadcast, maar dit tabblad is niet focused.');
            return;
        }
    }

    if (!modalInstance) {
        modalInstance = new bootstrap.Modal(modalEl, { backdrop: 'static', keyboard: false });
    }

    document.getElementById('modal-filename').innerText = filename;
    document.getElementById('modal-prompt').innerText = promptText || 'Input vereist.';
    modalInstance.show();
}

async function sendModalInput(filename, answer, postUrl) {
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

function hideModal() {
    if (modalInstance) {
        modalInstance.hide();
    }
}

function setupModalCleanup() {
    const modalElement = document.getElementById('inputModal');
    if (modalElement) {
        modalElement.addEventListener('hidden.bs.modal', () => {
            if (modalInstance) {
                modalInstance.dispose();
                modalInstance = null;
            }
        });
    }
    initTabSync();  // Initialiseer tab-sync
}

// Maak alle functies globaal beschikbaar
window.startPolling = startPolling;
window.stopPolling = stopPolling;
window.showModal = showModal;
window.sendModalInput = sendModalInput;
window.hideModal = hideModal;
window.setupModalCleanup = setupModalCleanup;