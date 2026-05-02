"""
Chatbot Lambda — Mutalip First Friend feature.

Receives a fire-and-forget payload from the WebSocket server when a user sends
a message to the Mutalip Kurban bot, calls Amazon Bedrock to generate a reply,
persists the reply to the messages table, and publishes it to Redis so the
WebSocket server can fan it out to the original sender.
"""

import asyncio
import json
import os

import boto3
from aws_lambda_powertools.utilities.typing import LambdaContext

from lambdas.lib import ensure_db
from shared.db.database import db_connection
from shared.logger import logger
from shared.redis_service import redis_service

MUTALIP_BOT_UUID: str = os.environ.get(
    "MUTALIP_BOT_UUID", "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
)

BEDROCK_MODEL_ID: str = os.environ.get("BEDROCK_MODEL_ID", "us.amazon.nova-lite-v1:0")

SYSTEM_PROMPT: str = (
    "You are Mutalip Kurban, a friendly AWS expert chatbot in a chat app. "
    "You ONLY discuss AWS services, microservice architecture, and three-tiered architecture. "
    "If asked about anything else, politely redirect the conversation back to these topics with a joke related to your topics. "
    "Keep your replies short and conversational — 2 to 4 sentences maximum. "
    "Never use markdown, bullet points, headers, or code blocks. Plain text only."
)

FALLBACK_REPLY: str = (
    "Sorry, I'm having trouble connecting to AWS right now. "
    "Try asking me about microservices later!"
)

_bedrock = boto3.client(
    "bedrock-runtime",
    region_name=os.environ.get("AWS_AZ", "us-east-1"),
)


async def _deliver_reply(sender_id: str, reply_text: str) -> None:
    """Persist the bot reply to the DB and publish it to Redis."""
    await ensure_db()

    row = await db_connection.fetch_one(
        query=(
            "INSERT INTO messages "
            "(sender_id, reciever_id, content, created_at, is_read) "
            "VALUES (:sender_id, :reciever_id, :content, NOW(), FALSE) "
            "RETURNING id, sender_id, reciever_id, content, created_at, is_read"
        ),
        values={
            "sender_id": MUTALIP_BOT_UUID,
            "reciever_id": sender_id,
            "content": reply_text,
        },
    )

    message_fields = {}
    if row:
        for k, v in dict(row).items():
            if hasattr(v, "hex"):  # UUID
                message_fields[k] = str(v)
            elif hasattr(v, "isoformat"):  # datetime
                message_fields[k] = v.isoformat()
            else:
                message_fields[k] = v

    # Publish to Redis — non-fatal if it fails
    try:
        await redis_service.connect()
        await redis_service.publish_message(
            f"user:{sender_id}",
            {
                "type": "new_message",
                "user_id": sender_id,
                **message_fields,
            },
        )
    except Exception as exc:
        logger.error(f"Failed to publish bot reply to Redis for user {sender_id}: {exc}")


def endpoint_chatbot(event: dict, context: LambdaContext) -> None:
    """Lambda entry point for the Chatbot Lambda.

    Event payload (fire-and-forget from WebSocket server):
        {
            "sender_id":   "<uuid>",
            "reciever_id": "<MUTALIP_BOT_UUID>",
            "content":     "<user message text>",
            "message_id":  42
        }
    """
    sender_id = event.get("sender_id")
    content = event.get("content")

    if not sender_id or not content:
        logger.warning(
            "endpoint_chatbot: missing sender_id or content in payload — "
            f"sender_id={sender_id!r}, content={content!r}. Aborting."
        )
        return

    request_body = json.dumps(
        {
            "messages": [
                {
                    "role": "user",
                    "content": [{"text": content}],
                }
            ],
            "system": [{"text": SYSTEM_PROMPT}],
            "inferenceConfig": {"maxTokens": 150},
        }
    )

    try:
        response = _bedrock.invoke_model(
            modelId=BEDROCK_MODEL_ID,
            body=request_body,
        )
        response_body = json.loads(response["body"].read())
        reply_text = response_body["output"]["message"]["content"][0]["text"]
    except Exception as exc:
        logger.error(f"Bedrock invocation failed: {exc}. Using fallback reply.")
        reply_text = FALLBACK_REPLY

    asyncio.run(_deliver_reply(sender_id, reply_text))
