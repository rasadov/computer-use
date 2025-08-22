import orjson
from anthropic.types.beta import BetaMessageParam, BetaTextBlockParam

from backend.models.message import Message


def convert_to_anthropic_message(
        db_message: Message) -> BetaMessageParam | dict:
    """Convert database message to Anthropic API format"""
    if isinstance(db_message.content, str):
        try:
            content_data = orjson.loads(db_message.content)
            # Ensure content is always a list
            if isinstance(content_data, list):
                content = content_data
            elif isinstance(content_data, dict):
                content = [content_data]
            else:
                content = [{"type": "text", "text": str(content_data)}]

            return {
                "role": db_message.role,
                "content": content
            }
        except (orjson.JSONDecodeError, TypeError):
            return {
                "role": db_message.role,
                "content": [
                    BetaTextBlockParam(
                        type="text",
                        text=db_message.content)]}
    else:
        return {
            "role": db_message.role,
            "content": db_message.content if isinstance(
                db_message.content,
                list) else [
                db_message.content]}
