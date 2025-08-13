from backend.models.message import ChatMessage
from anthropic.types.beta import BetaMessageParam, BetaTextBlockParam
import json


def convert_to_anthropic_message(
        db_message: ChatMessage) -> BetaMessageParam | dict:
    """Convert database message to Anthropic API format"""
    if isinstance(db_message.content, str):
        try:
            content_data = json.loads(db_message.content)
            return {
                "role": db_message.role,
                "content": content_data
            }
        except (json.JSONDecodeError, TypeError):
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
