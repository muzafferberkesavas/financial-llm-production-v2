"""/v2/ws/live — WebSocket broadcast for live signal updates.

Phase 2.5'te basit: bağlı client'lara ConnectionManager üzerinden broadcast.
Phase 3'te Redis pub/sub ile multi-instance scaling.
"""
from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from finllm.utils.logging import logger

router = APIRouter(tags=["ws"])


class ConnectionManager:
    """In-memory connection pool. Process-local — single-instance only."""

    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.active.append(ws)
        logger.info(f"[WS] client connected, total={len(self.active)}")

    def disconnect(self, ws: WebSocket) -> None:
        if ws in self.active:
            self.active.remove(ws)
        logger.info(f"[WS] client disconnected, total={len(self.active)}")

    async def broadcast(self, message: dict) -> int:
        """Tüm bağlı client'lara JSON gönder. Disconnected olanları temizle."""
        if not self.active:
            return 0
        text = json.dumps(message, default=str)
        dead = []
        sent = 0
        for ws in self.active:
            try:
                await ws.send_text(text)
                sent += 1
            except Exception:
                dead.append(ws)
        for d in dead:
            self.disconnect(d)
        return sent


manager = ConnectionManager()


@router.websocket("/v2/ws/live")
async def ws_live(ws: WebSocket) -> None:
    """Client bağlanır, sunucu hello gönderir, sonra broadcast'leri alır."""
    await manager.connect(ws)
    try:
        await ws.send_json(
            {
                "type": "hello",
                "message": "FinLLM live stream connected",
                "version": "v2",
            }
        )
        # Keep-alive: client'tan ping gelirse pong dön
        while True:
            try:
                msg = await asyncio.wait_for(ws.receive_text(), timeout=30.0)
                if msg.lower() == "ping":
                    await ws.send_text("pong")
            except asyncio.TimeoutError:
                # Idle keepalive
                await ws.send_json({"type": "heartbeat"})
    except WebSocketDisconnect:
        manager.disconnect(ws)
    except Exception as e:
        logger.warning(f"[WS] error: {e}")
        manager.disconnect(ws)


async def broadcast_signal(signal_dict: dict) -> int:
    """Stage 5'ten çağrılabilir — yeni sinyal yayını."""
    return await manager.broadcast({"type": "new_signal", "data": signal_dict})
