import asyncio
import json
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.utilities.data_classes import APIGatewayProxyEventV2
from shared.db.database import db_connection, get_user_by_username
from shared.logger import logger
from models.messages import Message_Response

def get_or_create_event_loop():
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError("Loop is closed")
        return loop
    except (RuntimeError, ValueError):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop

async def ensure_db():
    if not db_connection.is_connected:
        await db_connection.connect()

async def get_current_user_from_event(api_event: APIGatewayProxyEventV2):
    authorizer = api_event.request_context.authorizer
    if not authorizer or not authorizer.jwt or not authorizer.jwt.claims:
        raise Exception("Unauthorized: No claims found")
    
    username = authorizer.jwt.claims.get("username")
    if not username:
        raise Exception("Unauthorized: No username in claims")
    
    user = await get_user_by_username(username)
    if not user:
        raise Exception("Unauthorized: User not found in DB")
    
    # Handle schema variance between id and cognito_id
    if "id" not in user and "cognito_id" in user:
        user["id"] = user["cognito_id"]
        
    return user

def endpoint_get_messages(event: dict, context: LambdaContext):
    loop = get_or_create_event_loop()
    
    async def _process():
        try:
            api_event = APIGatewayProxyEventV2(event)
            other_user_id_str = api_event.path_parameters.get("other_user_id")
            if not other_user_id_str:
                return {"statusCode": 400, "body": json.dumps({"detail": "other_user_id is required"})}
            other_user_id = int(other_user_id_str)
            
            qs = api_event.query_string_parameters or {}
            limit = int(qs.get("limit", 50))
            offset = int(qs.get("offset", 0))

            await ensure_db()
            current_user = await get_current_user_from_event(api_event)
            user_id = current_user["id"]
            
            query = """
                        SELECT id, sender_id, reciever_id, content, created_at, is_read FROM messages
                        WHERE (sender_id= :user_id AND reciever_id= :other_user_id)
                        OR ((sender_id= :other_user_id AND reciever_id= :user_id))
                        ORDER BY created_at DESC
                        LIMIT :limit OFFSET :offset
                    """
            messages = await db_connection.fetch_all(
                query=query,
                values={
                    "user_id": user_id,
                    "other_user_id": other_user_id,
                    "limit": limit,
                    "offset": offset,
                },
            )
            
            res_list = [Message_Response(**dict(message)).model_dump() for message in messages]
            return {"statusCode": 200, "body": json.dumps(res_list, default=str)}
            
        except Exception as e:
            logger.error(f"Error while retrieving messages or conv {e}")
            return {"statusCode": 500, "body": json.dumps({"detail": str(e)})}
            
    return loop.run_until_complete(_process())

def endpoint_delete_conversation(event: dict, context: LambdaContext):
    loop = get_or_create_event_loop()
    
    async def _process():
        try:
            api_event = APIGatewayProxyEventV2(event)
            other_user_id_str = api_event.path_parameters.get("other_user_id")
            if not other_user_id_str:
                return {"statusCode": 400, "body": json.dumps({"detail": "other_user_id is required"})}
            other_user_id = int(other_user_id_str)

            await ensure_db()
            current_user = await get_current_user_from_event(api_event)
            user_id = current_user["id"]
            
            query = """
                    DELETE FROM messages
                    WHERE (sender_id = :user_id AND reciever_id = :other_user_id) 
                    OR (sender_id = :other_user_id AND reciever_id = :user_id)
                    """
            result = await db_connection.execute(
                query=query, values={"user_id": user_id, "other_user_id": other_user_id}
            )
            
            return {
                "statusCode": 200, 
                "body": json.dumps({
                    "message": "Conversation deleted successfully",
                    "deleted_messages": result,
                })
            }

        except Exception as e:
            logger.error(f"Error while deleting conversation: {e}")
            return {"statusCode": 500, "body": json.dumps({"detail": str(e)})}
            
    return loop.run_until_complete(_process())

def endpoint_get_conversations(event: dict, context: LambdaContext):
    loop = get_or_create_event_loop()
    
    async def _process():
        try:
            api_event = APIGatewayProxyEventV2(event)
            qs = api_event.query_string_parameters or {}
            limit = int(qs.get("limit", 50))
            offset = int(qs.get("offset", 0))

            await ensure_db()
            current_user = await get_current_user_from_event(api_event)
            user_id = current_user["id"]

            query = """
                WITH last_messages AS (
                    SELECT 
                        CASE 
                            WHEN sender_id = :user_id THEN reciever_id
                            ELSE sender_id
                        END AS other_user_id,
                        content AS last_message,
                        created_at AS last_message_time,
                        ROW_NUMBER() OVER (
                            PARTITION BY 
                                LEAST(sender_id, reciever_id),
                                GREATEST(sender_id, reciever_id)
                            ORDER BY created_at DESC
                        ) AS rn
                    FROM messages
                    WHERE sender_id = :user_id OR reciever_id = :user_id
                )
                SELECT
                    lm.other_user_id,
                    lm.last_message,
                    lm.last_message_time,
                    u.username
                FROM last_messages lm
                JOIN users u ON u.id = lm.other_user_id
                WHERE rn = 1
                ORDER BY last_message_time DESC
                LIMIT :limit OFFSET :offset;
            """

            rows = await db_connection.fetch_all(
                query=query,
                values={
                    "user_id": user_id,
                    "limit": limit,
                    "offset": offset,
                },
            )

            res_list = [
                {
                    "other_user_id": r["other_user_id"],
                    "username": r["username"],
                    "last_message": r["last_message"],
                    "last_message_time": r["last_message_time"],
                }
                for r in rows
            ]
            
            return {"statusCode": 200, "body": json.dumps(res_list, default=str)}

        except Exception as e:
            logger.error(f"Error retrieving conversations: {e}")
            return {"statusCode": 500, "body": json.dumps({"detail": str(e)})}
            
    return loop.run_until_complete(_process())
