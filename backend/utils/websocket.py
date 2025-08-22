import logging

import orjson
from fastapi import WebSocket

from backend.models.enums import SessionStatus
from backend.services.connection_manager import WebsocketsManager
from backend.services.session_manager import SessionManager

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


async def cleanup_websocket_connection(
    session_id: str,
    session_manager: SessionManager,
    connection_manager: WebsocketsManager,
):
    """Cleanup function to remove connection and update session status"""
    logger.debug(f"Cleaning up session {session_id}")
    try:
        await connection_manager.remove_connection(session_id)
        await session_manager.update_session_status(session_id, SessionStatus.INACTIVE)
    except Exception as e:
        logger.error(f"Error cleaning up session {session_id}: {e}")
