import json
import logging
import os
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from aws_lambda_powertools.utilities.data_classes import APIGatewayProxyEventV2
from shared.db.database import db_connection, get_user_by_username

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def _response(status_code: int, body: Any = None, **extra) -> Dict[str, Any]:
    """Build an API Gateway HTTP API v2 response with CORS headers.

    body: dict/list -> json.dumps; str -> passed through (assumed pre-encoded);
    None -> empty body. extra fields (e.g. cookies) merged into the envelope.
    CORS origin reads from CORS_ALLOWED_ORIGIN env var (set by Terraform to the
    CloudFront URL in production); defaults to '*' for local invocation.
    """
    if body is None:
        body_str = ""
    elif isinstance(body, str):
        body_str = body
    else:
        body_str = json.dumps(body, default=str)

    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": os.environ.get("CORS_ALLOWED_ORIGIN", "*"),
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
        },
        "body": body_str,
        **extra,
    }

@dataclass
class CognitoUser:
    user_id: str | None
    username: str | None
    email: Optional[str] = None
    groups: List[str] = None
    is_admin: bool = False
    
    def __post_init__(self):
        if self.groups is None:
            self.groups = []
        self.is_admin = 'admin' in self.groups

class AuthError(Exception):
    """Raised when an authenticated request is missing or has invalid Cognito claims."""
    pass


class CognitoHelper:
    @staticmethod
    def extract_user_from_event(event: APIGatewayProxyEventV2) -> Optional[CognitoUser]:
        """Extract user info from an HTTP API v2 event with a Cognito JWT authorizer.

        Expects claims at event.request_context.authorizer.jwt_claim, which is the
        powertools accessor for HTTP API v2 + JWT authorizer. If the API Gateway
        is REST API v1 instead, this needs to read from .authorizer.claims.

        Returns None if no authorizer context is present (caller should treat as
        unauthenticated).
        """
        try:
            authorizer = event.request_context.authorizer
            if authorizer is None:
                logger.warning("Request has no authorizer context")
                return None
            claims = authorizer.jwt_claim
            if not claims:
                logger.warning("Request has authorizer context but no JWT claims")
                return None

            username = (claims.get('cognito:username') or
                       claims.get('username') or
                       claims.get('preferred_username') or
                       claims.get('email') or
                       claims.get('sub'))

            user_groups = claims.get('cognito:groups', [])
            if isinstance(user_groups, str):
                user_groups = [user_groups]

            return CognitoUser(
                user_id=claims.get('sub'),
                username=username,
                email=claims.get('email'),
                groups=user_groups
            )
        except (KeyError, TypeError, AttributeError) as e:
            logger.error(f"Failed to extract user from event: {str(e)}")
            return None

async def get_database_user_from_event(api_event: APIGatewayProxyEventV2):
    """Look up the database user record for the Cognito-authenticated caller.

    Raises AuthError if claims are missing or no matching DB user exists.
    Lambdas can catch AuthError to return 401; uncaught exceptions remain 500.
    """
    cognito_user = CognitoHelper.extract_user_from_event(api_event)

    if cognito_user is None:
        raise AuthError("Unauthorized: missing or invalid authorizer context")

    if not cognito_user.username:
        raise AuthError("Unauthorized: no username found in claims")

    user = await get_user_by_username(cognito_user.username)
    if not user:
        raise AuthError("Unauthorized: user not found in DB")

    return user

async def ensure_db():
    """Connect the global Database to the current asyncio loop.

    Each Lambda invocation runs under a fresh asyncio.run() loop, but the
    module-global db_connection persists across invocations. Its asyncpg
    pool is bound to the previous (closed) loop, so we must replace it.
    Graceful disconnect() can hang or error against a dead loop, so we
    forcefully terminate the old pool via internals, reset the connection
    flag, then call connect() to build a fresh pool on the current loop.
    """
    try:
        backend = getattr(db_connection, "_backend", None)
        old_pool = getattr(backend, "_pool", None) if backend else None
        if old_pool is not None:
            old_pool.terminate()
            backend._pool = None
    except Exception:
        pass
    try:
        db_connection._is_connected = False
    except Exception:
        pass
    await db_connection.connect()