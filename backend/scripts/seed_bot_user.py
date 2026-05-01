"""
Seed script for the Mutalip Kurban chatbot user.

Inserts the bot user row into the `users` table using an idempotent
ON CONFLICT DO NOTHING upsert. Safe to run multiple times.

Usage:
    python -m scripts.seed_bot_user
    # or from the backend/ directory:
    python scripts/seed_bot_user.py
"""

import asyncio

from shared.config import settings
from shared.db.database import db_connection
from shared.logger import logger


async def seed_bot_user() -> None:
    """Insert the Mutalip Kurban bot row if it does not already exist."""
    await db_connection.execute(
        """
        INSERT INTO users (cognito_sub, email, username)
        VALUES (:sub, :email, :username)
        ON CONFLICT (cognito_sub) DO NOTHING
        """,
        values={
            "sub": settings.mutalip_bot_uuid,
            "email": "mutalip@chatbot.internal",
            "username": "Mutalip Kurban",
        },
    )
    logger.info(
        f"Bot user seed complete (uuid={settings.mutalip_bot_uuid}). "
        "Row inserted or already existed."
    )


async def _main() -> None:
    """Connect to the DB, ensure schema exists, then seed the bot user."""
    from shared.db.database import init_db
    await db_connection.connect()
    try:
        await init_db()
        await seed_bot_user()
    finally:
        await db_connection.disconnect()


if __name__ == "__main__":
    asyncio.run(_main())
