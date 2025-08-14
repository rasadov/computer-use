import json
import logging

from fastapi import WebSocket


logger = logging.getLogger(__name__)

async def send_websocket_message(
        websocket: WebSocket,
        task_status: str,
        message_type: str,
        content):
    """Safely send a message via websocket"""
    try:
        await websocket.send_text(json.dumps({
            "type": message_type,
            "task_status": task_status,
            "content": content
        }))
    except Exception as e:
        logger.error(f"Error sending websocket message: {e}")
