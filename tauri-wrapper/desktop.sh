#!/usr/bin/env bash
# Desktop launcher for NLP2DSL Voice Chat
# Workaround: Tauri v1 is incompatible with Ubuntu 24.10+ (libsoup2 vs libsoup3 conflict).
# This script opens the voice chat UI in Chrome/Chromium --app mode, which gives a
# standalone window without address bar — functionally equivalent to a desktop app.

set -euo pipefail

BACKEND_URL="${BACKEND_URL:-http://127.0.0.1:8002}"
CHAT_URL="${CHAT_URL:-${BACKEND_URL%/}/chat}"
WINDOW_SIZE="${WINDOW_SIZE:-1280,900}"
WINDOW_POSITION="${WINDOW_POSITION:-100,50}"
WAIT_SECONDS="${WAIT_SECONDS:-30}"

HEALTH_URL="${BACKEND_URL%/}/health"

if ! command -v curl >/dev/null 2>&1; then
    echo "ERROR: curl is required to wait for the backend health endpoint."
    exit 1
fi

echo "Waiting for nlp-service at ${HEALTH_URL} (up to ${WAIT_SECONDS}s)..."
backend_ready=0
attempt=0
while [ "${attempt}" -lt "${WAIT_SECONDS}" ]; do
    if curl -sf "${HEALTH_URL}" >/dev/null 2>&1; then
        backend_ready=1
        echo "nlp-service is up."
        break
    fi

    attempt=$((attempt + 1))
    sleep 1
done

if [ "${backend_ready}" -ne 1 ]; then
    echo "WARNING: nlp-service did not answer within ${WAIT_SECONDS}s; opening the chat anyway."
fi

# Pick an available browser
SELECTED_BROWSER="${BROWSER:-}"
if [ -n "${SELECTED_BROWSER}" ] && ! command -v "${SELECTED_BROWSER}" >/dev/null 2>&1; then
    echo "ERROR: Requested BROWSER '${SELECTED_BROWSER}' was not found in PATH."
    exit 1
fi

if [ -z "${SELECTED_BROWSER}" ]; then
    for candidate in google-chrome google-chrome-stable chromium chromium-browser brave-browser microsoft-edge; do
        if command -v "$candidate" >/dev/null 2>&1; then
            SELECTED_BROWSER="$candidate"
            break
        fi
    done
fi

if [ -n "${SELECTED_BROWSER}" ]; then
    echo "Launching: ${SELECTED_BROWSER} --app=${CHAT_URL}"
    exec "${SELECTED_BROWSER}" \
        --app="${CHAT_URL}" \
        --window-size="${WINDOW_SIZE}" \
        --window-position="${WINDOW_POSITION}" \
        --use-fake-ui-for-media-stream \
        --disable-features=TranslateUI \
        --no-default-browser-check \
        "$@"
fi

if command -v xdg-open >/dev/null 2>&1; then
    echo "WARNING: No app-mode browser found; falling back to xdg-open."
    exec xdg-open "${CHAT_URL}"
fi

if command -v open >/dev/null 2>&1; then
    echo "WARNING: No app-mode browser found; falling back to macOS open."
    exec open "${CHAT_URL}"
fi

echo "ERROR: No Chrome/Chromium browser or system opener found."
exit 1
