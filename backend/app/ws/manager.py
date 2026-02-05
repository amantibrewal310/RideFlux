import json
import logging
from collections import defaultdict

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Channel-based WebSocket connection manager."""

    def __init__(self):
        self._channels: dict[str, set[WebSocket]] = defaultdict(set)

    async def subscribe(self, channel: str, ws: WebSocket) -> None:
        self._channels[channel].add(ws)

    async def unsubscribe(self, channel: str, ws: WebSocket) -> None:
        self._channels[channel].discard(ws)
        if not self._channels[channel]:
            del self._channels[channel]

    async def unsubscribe_all(self, ws: WebSocket) -> None:
        empty = []
        for channel, connections in self._channels.items():
            connections.discard(ws)
            if not connections:
                empty.append(channel)
        for ch in empty:
            del self._channels[ch]

    async def broadcast(self, channel: str, message: dict) -> None:
        dead: list[WebSocket] = []
        for ws in self._channels.get(channel, set()):
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._channels[channel].discard(ws)
            logger.debug("Removed dead connection from channel %s", channel)

    @property
    def active_connections(self) -> int:
        seen: set[int] = set()
        for connections in self._channels.values():
            for ws in connections:
                seen.add(id(ws))
        return len(seen)


manager = ConnectionManager()
