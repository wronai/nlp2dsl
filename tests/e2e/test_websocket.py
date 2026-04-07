"""
E2E tests for WebSocket endpoint: ws://localhost:8002/ws/chat/{conversation_id}

Covers:
  - Connection accepted
  - Binary audio data accepted (no crash, STT unavailable → no response)
  - Disconnect handled gracefully
  - Multiple concurrent connections
"""

from __future__ import annotations

import asyncio
import json
import os
import pytest
import websockets
from websockets.connection import State


NLP_WS_URL = os.getenv("NLP_WS_URL", "ws://localhost:8002")

pytestmark = pytest.mark.asyncio


def _uri(conv_id: str) -> str:
    return f"{NLP_WS_URL}/ws/chat/{conv_id}"


def _is_open(ws) -> bool:
    return ws.state == State.OPEN


def _is_closed(ws) -> bool:
    return ws.state == State.CLOSED


# ── Connection ────────────────────────────────────────────────

async def test_websocket_connects_and_accepts():
    async with websockets.connect(_uri("connect-test")) as ws:
        assert _is_open(ws)


async def test_websocket_unique_conversation_id():
    async with websockets.connect(_uri("conv-a")) as ws1:
        async with websockets.connect(_uri("conv-b")) as ws2:
            assert _is_open(ws1)
            assert _is_open(ws2)


# ── Binary data ───────────────────────────────────────────────

async def test_websocket_accepts_binary_audio():
    """
    Send a small chunk of fake audio bytes.
    Without Deepgram, no transcript is returned — the server should
    not crash and the connection should remain open.
    """
    async with websockets.connect(_uri("binary-test")) as ws:
        fake_audio = bytes(320)  # 320 zero-bytes ~ 20ms of silence
        await ws.send(fake_audio)

        try:
            msg = await asyncio.wait_for(ws.recv(), timeout=2.0)
            data = json.loads(msg)
            assert "type" in data
        except asyncio.TimeoutError:
            pass  # no STT → no response, expected

        assert _is_open(ws)


async def test_websocket_accepts_multiple_chunks():
    async with websockets.connect(_uri("multi-chunk")) as ws:
        for _ in range(5):
            await ws.send(bytes(160))
            await asyncio.sleep(0.05)
        assert _is_open(ws)


# ── Disconnect ────────────────────────────────────────────────

async def test_websocket_clean_disconnect():
    async with websockets.connect(_uri("disconnect-test")) as ws:
        assert _is_open(ws)
    assert _is_closed(ws)


async def test_websocket_server_survives_abrupt_close():
    """Server should handle client abruptly closing without crashing."""
    async with websockets.connect(_uri("abrupt-close")) as ws:
        await ws.send(bytes(64))

    # Verify server still accepts new connections after abrupt close
    async with websockets.connect(_uri("after-abrupt")) as ws2:
        assert _is_open(ws2)


# ── Concurrency ───────────────────────────────────────────────

async def test_websocket_concurrent_connections():
    """Server should handle multiple simultaneous connections."""
    async def connect_and_check(cid):
        async with websockets.connect(_uri(cid)) as ws:
            assert _is_open(ws)
            return True

    ids = [f"concurrent-{i}" for i in range(4)]
    results = await asyncio.gather(*[connect_and_check(cid) for cid in ids])
    assert all(results)
