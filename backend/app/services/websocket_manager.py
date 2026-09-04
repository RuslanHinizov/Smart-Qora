import asyncio

from fastapi import WebSocket


class WebSocketManager:
    def __init__(self):
        self.connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self.connections.add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self.connections.discard(websocket)

    async def broadcast(self, payload: dict) -> None:
        failed = []
        for connection in tuple(self.connections):
            try:
                await connection.send_json(payload)
            except Exception:
                failed.append(connection)
        for connection in failed:
            await self.disconnect(connection)


websockets = WebSocketManager()
