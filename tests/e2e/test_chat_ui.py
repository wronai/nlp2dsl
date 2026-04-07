"""
E2E browser tests for the Voice Chat UI (http://localhost:8002/chat).

Uses Playwright with a fake microphone device (--use-fake-device-for-media-stream)
so tests run headless without real hardware.

Covers:
  - Page loads, title, manifest
  - TTS button present and togglable
  - speak() function wired to speechSynthesis
  - Microphone getUserMedia works (fake device)
  - Voice transcription auto-starts on page load
  - Voice (Start/Stop) button still works as a fallback
  - Text input → assistant response rendered
  - speak() invoked after assistant response
  - No JavaScript errors on load
"""

from __future__ import annotations

import time

import pytest
from playwright.async_api import Page


pytestmark = pytest.mark.asyncio


# ── Page load ─────────────────────────────────────────────────

async def test_page_title(chat_page: Page):
    title = await chat_page.title()
    assert title, "Page has no title"
    assert "chat" in title.lower() or "nlp" in title.lower() or "voice" in title.lower()


async def test_page_has_no_js_errors(page: Page):
    errors: list[str] = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    await page.goto("http://localhost:8002/chat", wait_until="networkidle")
    assert errors == [], f"JS errors on load: {errors}"


async def test_web_app_manifest(chat_page: Page):
    r = await chat_page.request.get("/manifest.json")
    assert r.status == 200
    data = await r.json()
    assert "name" in data or "short_name" in data


# ── TTS (speakers) ────────────────────────────────────────────

async def test_tts_button_present(chat_page: Page):
    btn = await chat_page.query_selector("#ttsBtn")
    assert btn is not None, "#ttsBtn not found in DOM"


async def test_tts_button_default_state_active(chat_page: Page):
    btn = await chat_page.query_selector("#ttsBtn")
    text = await btn.inner_text()
    assert "🔊" in text, f"Expected active (🔊) TTS button, got: '{text}'"
    enabled = await chat_page.evaluate("ttsEnabled")
    assert enabled is True


async def test_tts_toggle_disables(chat_page: Page):
    await chat_page.click("#ttsBtn")
    enabled = await chat_page.evaluate("ttsEnabled")
    assert enabled is False
    btn = await chat_page.query_selector("#ttsBtn")
    text = await btn.inner_text()
    assert "🔇" in text


async def test_tts_toggle_re_enables(chat_page: Page):
    await chat_page.click("#ttsBtn")
    await chat_page.click("#ttsBtn")
    enabled = await chat_page.evaluate("ttsEnabled")
    assert enabled is True
    text = await (await chat_page.query_selector("#ttsBtn")).inner_text()
    assert "🔊" in text


async def test_speak_function_defined(chat_page: Page):
    is_func = await chat_page.evaluate("typeof speak === 'function'")
    assert is_func, "speak() function not defined on page"


async def test_speech_synthesis_available(chat_page: Page):
    available = await chat_page.evaluate("'speechSynthesis' in window")
    assert available, "speechSynthesis not available in browser context"


async def test_speak_calls_speech_synthesis(chat_page: Page):
    """speak() should invoke speechSynthesis.speak."""
    called = await chat_page.evaluate("""() => {
        let called = false;
        const orig = speechSynthesis.speak.bind(speechSynthesis);
        speechSynthesis.speak = function(utt) {
            called = true;
            speechSynthesis.speak = orig;
        };
        speak("test audio output");
        return called;
    }""")
    assert called, "speechSynthesis.speak was not called by speak()"


async def test_speak_respects_tts_disabled(chat_page: Page):
    """When TTS is disabled, speak() must not call speechSynthesis.speak."""
    called = await chat_page.evaluate("""() => {
        ttsEnabled = false;
        let called = false;
        const orig = speechSynthesis.speak.bind(speechSynthesis);
        speechSynthesis.speak = function(utt) {
            called = true;
            speechSynthesis.speak = orig;
        };
        speak("this should be silent");
        ttsEnabled = true;
        return called;
    }""")
    assert not called, "speak() should not call speechSynthesis when ttsEnabled=false"


# ── Microphone (getUserMedia) ─────────────────────────────────

async def test_microphone_get_user_media(chat_page: Page):
    result = await chat_page.evaluate("""async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            stream.getTracks().forEach(t => t.stop());
            return "granted";
        } catch (e) {
            return String(e);
        }
    }""")
    assert result == "granted", f"getUserMedia failed: {result}"


async def test_media_recorder_supported(chat_page: Page):
    supported = await chat_page.evaluate("typeof MediaRecorder !== 'undefined'")
    assert supported, "MediaRecorder not available"


# ── Voice button ──────────────────────────────────────────────

async def test_voice_button_present(chat_page: Page):
    btn = await chat_page.query_selector("#voiceBtn")
    assert btn is not None, "#voiceBtn not found"


async def test_voice_button_initial_text(chat_page: Page):
    text = await chat_page.evaluate("document.getElementById('voiceBtnText').textContent")
    assert "start" in text.lower() or "stop" in text.lower() or "voice" in text.lower(), \
        f"Unexpected voice button label: '{text}'"


async def wait_for_voice_recording(chat_page: Page, timeout_s: float = 10.0) -> str:
    deadline = time.monotonic() + timeout_s
    last_text = ""

    while time.monotonic() < deadline:
        last_text = await chat_page.evaluate("document.getElementById('voiceBtnText').textContent")
        if "stop" in last_text.lower():
            return last_text
        await chat_page.wait_for_timeout(250)

    pytest.fail(f"Voice recording did not start automatically. Last label: '{last_text}'")


async def test_voice_transcription_autostarts_on_load(chat_page: Page):
    """Voice transcription should start automatically once the page and websocket are ready."""
    text_after = await wait_for_voice_recording(chat_page)
    assert "stop" in text_after.lower(), f"Expected 'Stop' label, got: '{text_after}'"

    await chat_page.click("#voiceBtn")
    await chat_page.wait_for_timeout(750)
    stopped_text = await chat_page.evaluate("document.getElementById('voiceBtnText').textContent")
    assert "start" in stopped_text.lower(), f"Expected 'Start' label after cleanup stop, got: '{stopped_text}'"


async def test_voice_button_click_stops_recording(chat_page: Page):
    await wait_for_voice_recording(chat_page)
    await chat_page.click("#voiceBtn")
    await chat_page.wait_for_timeout(750)
    text_after = await chat_page.evaluate("document.getElementById('voiceBtnText').textContent")
    assert "start" in text_after.lower(), f"Expected 'Start' label after stop, got: '{text_after}'"


# ── Text chat flow ────────────────────────────────────────────

async def test_text_input_present(chat_page: Page):
    inp = await chat_page.query_selector("#textInput")
    assert inp is not None, "#textInput not found"


async def test_send_button_present(chat_page: Page):
    btn = await chat_page.query_selector(".send-btn")
    assert btn is not None, ".send-btn not found"


async def test_text_message_renders_user_bubble(chat_page: Page):
    await chat_page.fill("#textInput", "Cześć, testowa wiadomość")
    await chat_page.click(".send-btn")
    await chat_page.wait_for_timeout(500)
    user_msgs = await chat_page.query_selector_all(".message.user")
    assert len(user_msgs) >= 1, "User message bubble not rendered"


async def test_text_message_gets_assistant_response(chat_page: Page):
    await chat_page.fill("#textInput", "test")
    await chat_page.click(".send-btn")
    await chat_page.wait_for_timeout(4000)
    assistant_msgs = await chat_page.query_selector_all(".message.assistant")
    assert len(assistant_msgs) >= 1, "No assistant response rendered"


async def test_speak_called_on_assistant_response(chat_page: Page):
    """After assistant responds, speak() should have been invoked."""
    await chat_page.evaluate("""() => {
        window._speakLog = [];
        const orig = window.speak;
        window.speak = function(txt) {
            window._speakLog.push(txt);
            return orig ? orig(txt) : undefined;
        };
    }""")
    await chat_page.fill("#textInput", "Wyślij fakturę")
    await chat_page.click(".send-btn")
    await chat_page.wait_for_timeout(4000)

    log = await chat_page.evaluate("window._speakLog")
    assert len(log) >= 1, "speak() was never called after assistant response"
    assert len(log[0]) > 0, "speak() was called with empty string"


async def test_text_input_cleared_after_send(chat_page: Page):
    await chat_page.fill("#textInput", "test input clear")
    await chat_page.click(".send-btn")
    await chat_page.wait_for_timeout(300)
    value = await chat_page.evaluate("document.getElementById('textInput').value")
    assert value == "", f"Text input not cleared after send, still contains: '{value}'"


# ── Status indicator ──────────────────────────────────────────

async def test_status_element_present(chat_page: Page):
    status = await chat_page.query_selector("#status")
    assert status is not None, "#status element not found"


async def test_websocket_connects_on_load(chat_page: Page):
    """WebSocket should be connected after page load."""
    ws_state = await chat_page.evaluate("""() => {
        if (!ws) return 'null';
        const states = ['CONNECTING', 'OPEN', 'CLOSING', 'CLOSED'];
        return states[ws.readyState] || 'unknown';
    }""")
    assert ws_state in ("CONNECTING", "OPEN"), \
        f"WebSocket not connected on load, state: {ws_state}"
