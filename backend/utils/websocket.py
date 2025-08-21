import logging

import orjson
from fastapi import WebSocket

logger = logging.getLogger(__name__)


async def send_websocket_message(
        websocket: WebSocket | None,
        task_status: str,
        message_type: str,
        content):
    """Safely send a message via websocket"""
    try:
        if not websocket:
            logger.warning("No websocket connection")
            return
        await websocket.send_text(orjson.dumps({
            "type": message_type,
            "task_status": task_status,
            "content": content
        }).decode("utf-8"))
    except Exception as e:
        logger.error(f"Error sending websocket message: {e}")
