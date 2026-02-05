import logging

logger = logging.getLogger(__name__)

# Lazy import to avoid circular dependency at module load time
_ws_manager = None


def _get_manager():
    global _ws_manager
    if _ws_manager is None:
        from app.ws.manager import manager
        _ws_manager = manager
    return _ws_manager


async def notify_ride_event(ride_id: str, event_type: str, data: dict) -> None:
    msg = {"type": event_type, "ride_id": ride_id, **data}
    mgr = _get_manager()
    await mgr.broadcast(f"ride:{ride_id}", msg)
    await mgr.broadcast("dashboard", msg)


async def notify_driver_event(driver_id: str, event_type: str, data: dict) -> None:
    msg = {"type": event_type, "driver_id": driver_id, **data}
    mgr = _get_manager()
    await mgr.broadcast(f"driver:{driver_id}", msg)
    await mgr.broadcast("dashboard", msg)
