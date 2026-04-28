from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import jwt
from shared.config import ALGORITHM, SECRET_KEY
from shared.db.database import get_user_by_username, init_db, db_connection, create_database_if_not_exists
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from shared.logger import logger
from shared.redis_service import redis_service
import asyncio
from app.websocket_engine import manager


origins = [
    "http://localhost:3000",
    "http://localhost:5173",  # Vite dev server (default)
    "http://localhost:5174",  # Alternative Vite port hai
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://localhost:8000",  # FastAPI docs
    "http://127.0.0.1:8000",  # FastAPI server
    "https://d14v638rpcg3lp.cloudfront.net",  # production CloudFront
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("starting the application")
    listener_task = None
    try:
        await create_database_if_not_exists()
        await db_connection.connect()
        await init_db()
        logger.info("db init bhayo hai ta ")

        # Connect to Redis and start listener
        if await redis_service.connect():
            listener_task = asyncio.create_task(redis_service.start_message_listener())
            logger.info("Redis connected and listener started")
        else:
            logger.error("Failed to connect to Redis")

    except Exception as e:
        logger.error(f" Startup failed: {e}", exc_info=True)
        raise

    yield
    logger.info("shutting application")
    try:
        # Cancel Redis listener task
        if listener_task:
            listener_task.cancel()
            try:
                await listener_task
            except asyncio.CancelledError:
                logger.info("Redis listener cancelled")

        # Disconnect Redis
        await redis_service.disconnect()
        logger.info("Redis disconnected")

        # Disconnect database
        await db_connection.disconnect()
        logger.info("database disconnected")
    except Exception as e:
        logger.error(f"shutting down: {e}", exc_info=True)


app = FastAPI(lifespan=lifespan)

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# CORS must be added before routers
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # websocket auth with first message authentication
    await websocket.accept()
    logger.info("Websocket connection accepted.")

    user_id: int | None = None
    try:

        auth_message = await asyncio.wait_for(websocket.receive_json(), timeout=10)
        if auth_message.get("type") != "auth":
            logger.error("First message is not a token")
            await websocket.send_json(
                {"type": "error", "content": "first message not an auth token"}
            )
            await websocket.close(code=1008, reason="Authentication required")
            return
        token = auth_message.get("content")
        if not token:
            logger.warning("WebSocket: Missing token in auth message")
            await websocket.send_json({"type": "error", "content": "Missing token"})
            await websocket.close(code=1008, reason="Missing token")
            return
        # jwt verification
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username = payload.get("sub")
            # {
            #   "sub": "john_doe",
            #   "exp": 1716400000,
            #   "iat": 1716390000,
            #   "role": "admin"
            # }

            if not username:
                logger.warning("WebSocket: Invalid token payload")
                await websocket.send_json({"type": "error", "content": "Invalid token"})
                await websocket.close(code=1008, reason="Invalid token")
                return

            user = await get_user_by_username(username)
            if not user:
                logger.error(f"Websocket User not found {username}")
                await websocket.send_json(
                    {"type": "error", "content": "User not found"}
                )
                await websocket.close(code=1008, reason="User not found")
                return
            user_id = user["id"]
            await manager.connect(user_id, websocket)
            user_channel = redis_service.get_user_channel(user_id)
            await redis_service.subscribe_to_channel(
                user_channel, manager.handle_redis_message
            )
            logger.info(f"user {user_id} subscribed to Redis channel: {user_channel}")

            await websocket.send_json(
                {
                    "type": "auth_success",
                    "user": {
                        "id": user["id"],
                        "username": user["username"],
                        "email": user["email"],
                    },
                }
            )
            logger.info(f" WebSocket authenticated: {username} (ID: {user_id})")

        except jwt.ExpiredSignatureError:
            logger.warning("WebSocket: Token expired")
            await websocket.send_json({"type": "error", "content": "Token expired"})
            await websocket.close(code=1008, reason="Token expired")
            return
        except jwt.InvalidTokenError as e:
            logger.warning(f"WebSocket: Invalid token - {e}")
            await websocket.send_json({"type": "error", "content": "Invalid token"})
            await websocket.close(code=1008, reason="Invalid token")
            return

        while True:
            data = await websocket.receive_json()

            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
                logger.debug(f"Ping from user {user_id}")
            elif data.get("type") == "message":
                content = data.get("content")
                reciever_id = data.get("reciever_id")
                logger.info(f"message from user {user_id} to {reciever_id}")

                if not content or not reciever_id:
                    await websocket.send_json(
                        {"type": "error", "content": "Missing content or reciever_id"}
                    )
                    continue

                try:
                    query = """INSERT INTO messages (sender_id,reciever_id,content,created_at,is_read)
                                VALUES (:sender_id,:reciever_id,:content,NOW(),FALSE)
                                RETURNING id,sender_id,reciever_id,content,created_at,is_read"""

                    saved_message = await db_connection.fetch_one(
                        query=query,
                        values={
                            "sender_id": user_id,
                            "reciever_id": reciever_id,
                            "content": content,
                        },
                    )
                except Exception as e:
                    logger.error(f"Error saving message: {e}", exc_info=True)
                    await websocket.send_json(
                        {"type": "error", "content": "Failed to save message"}
                    )
                    continue

                message_data = {
                    "id": saved_message["id"],
                    "sender_id": saved_message["sender_id"],
                    "reciever_id": saved_message["reciever_id"],
                    "content": saved_message["content"],
                    "created_at": saved_message["created_at"].isoformat(),
                    "is_read": saved_message["is_read"],
                }

                local_delivered = await manager.send_private_message(
                    reciever_id, message_data
                )
                reciever_channel = redis_service.get_user_channel(reciever_id)
                redis_published = await redis_service.publish_message(
                    reciever_channel,
                    {"type": "new_message", "user_id": reciever_id, **message_data},
                )
                delivery_status = (
                    "delivered"
                    if local_delivered
                    else ("published" if redis_published else "failed")
                )
                if local_delivered:
                    logger.info("message delivered locally")
                elif redis_published:
                    logger.info(f"message published to redis for user {reciever_id}")
                else:
                    logger.info("message delivery failed")
                await websocket.send_json(
                    {
                        "type": "message_sent",
                        "delivered": delivery_status,
                        **message_data,
                    }
                )
            else:
                logger.warning(f"Unknown message type {data.get('type')}")
    except asyncio.TimeoutError:
        logger.warning("WebSocket: Authentication timeout (10s)")
        await websocket.send_json(
            {"type": "error", "content": "Authentication timeout"}
        )
        await websocket.close(code=1008, reason="Authentication timeout")

    except WebSocketDisconnect:
        if user_id:
            user_channel = redis_service.get_user_channel(user_id)
            await redis_service.unsubscribe_from_channel(user_channel)
            await manager.disconnect(user_id)
            logger.info(f"websocket disconnected by user {user_id}")
        else:
            logger.info("WebSocket disconnected before authentication")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        if user_id:
            user_channel = redis_service.get_user_channel(user_id)
            await redis_service.unsubscribe_from_channel(user_channel)
            await manager.disconnect(user_id)
        try:
            await websocket.close(code=1011, reason="Internal error")
        except:
            pass

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
