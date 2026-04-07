"""
Shared pytest fixtures for E2E tests.

Services under test:
  nlp-service  → http://localhost:8002
  backend      → http://localhost:8010
  chat UI      → http://localhost:8002/chat
"""

from __future__ import annotations

import os
import shutil
import pytest
import pytest_asyncio
import httpx

from playwright.async_api import async_playwright, Browser, BrowserContext, Page


# ── Base URLs ──────────────────────────────────────────────────

NLP_URL = os.getenv("NLP_URL", "http://localhost:8002")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8010")
CHAT_URL = f"{NLP_URL}/chat"

PLAYWRIGHT_ARGS = [
    "--use-fake-ui-for-media-stream",
    "--use-fake-device-for-media-stream",
    "--no-sandbox",
    "--disable-dev-shm-usage",
]


def _resolve_browser_executable() -> str | None:
    for candidate in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
        path = shutil.which(candidate)
        if path:
            return path
    return None


# ── HTTP client ────────────────────────────────────────────────

@pytest_asyncio.fixture
async def nlp_client():
    async with httpx.AsyncClient(base_url=NLP_URL, timeout=20.0) as client:
        yield client


@pytest_asyncio.fixture
async def backend_client():
    async with httpx.AsyncClient(base_url=BACKEND_URL, timeout=20.0) as client:
        yield client


# ── Playwright ─────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="session")
async def browser_instance():
    async with async_playwright() as pw:
        browser_kwargs = {
            "headless": True,
            "args": PLAYWRIGHT_ARGS,
        }
        browser_executable = _resolve_browser_executable()
        if browser_executable:
            browser_kwargs["executable_path"] = browser_executable

        browser: Browser = await pw.chromium.launch(**browser_kwargs)
        yield browser
        await browser.close()


@pytest_asyncio.fixture
async def browser_context(browser_instance: Browser):
    ctx: BrowserContext = await browser_instance.new_context(
        permissions=["microphone"],
    )
    yield ctx
    await ctx.close()


@pytest_asyncio.fixture
async def page(browser_context: BrowserContext):
    p: Page = await browser_context.new_page()
    yield p
    await p.close()


@pytest_asyncio.fixture
async def chat_page(page: Page):
    """Page already loaded at CHAT_URL and idle."""
    await page.goto(CHAT_URL, wait_until="domcontentloaded")
    await page.wait_for_selector("#voiceBtn")
    yield page

    try:
        await page.evaluate(
            """() => {
                try {
                    if (typeof stopVoiceRecording === 'function' && isRecording) {
                        stopVoiceRecording();
                    }
                    if (audioStream) {
                        audioStream.getTracks().forEach((track) => track.stop());
                        audioStream = null;
                    }
                    if (ws && ws.readyState === WebSocket.OPEN) {
                        ws.close();
                    }
                } catch (error) {
                    // Ignore cleanup errors; the page is about to close.
                }
            }"""
        )
        await page.wait_for_timeout(250)
    except Exception:
        pass
