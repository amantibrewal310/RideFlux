import logging
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.ws.manager import manager

logger = logging.getLogger(__name__)
ws_router = APIRouter()


@ws_router.websocket("/ws/dashboard")
async def ws_dashboard(ws: WebSocket):
    await ws.accept()
    await manager.subscribe("dashboard", ws)
    logger.info("Dashboard WS client connected (total: %d)", manager.active_connections)
    try:
        while True:
            data = await ws.receive_text()
            if data == "ping":
                await ws.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass
    finally:
        await manager.unsubscribe("dashboard", ws)
        logger.info("Dashboard WS client disconnected")


@ws_router.websocket("/ws/rides/{ride_id}")
async def ws_ride(ws: WebSocket, ride_id: uuid.UUID):
    await ws.accept()
    channel = f"ride:{ride_id}"
    await manager.subscribe(channel, ws)
    await manager.subscribe("dashboard", ws)
    logger.info("Ride WS client connected for %s", ride_id)
    try:
        while True:
            data = await ws.receive_text()
            if data == "ping":
                await ws.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass
    finally:
        await manager.unsubscribe_all(ws)
        logger.info("Ride WS client disconnected for %s", ride_id)
