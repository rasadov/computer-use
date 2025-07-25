import json
from fastapi import WebSocket

async def send_websocket_message(websocket: WebSocket, message_type: str, content):
    """Safely send a message via websocket"""
    try:
        await websocket.send_text(json.dumps({
            "type": message_type,
            "content": content
        }))
    except Exception as e:
        print(f"Error sending websocket message: {e}")
