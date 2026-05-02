import json
import logging
import os
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from aws_lambda_powertools.utilities.data_classes import APIGatewayProxyEventV2
from shared.config import settings
from shared.db.database import db_connection, get_user_by_cognito_sub

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

    # Look up by sub (UUID PK), not username — Cognito lowercases usernames in
    # JWT claims when the pool has case_sensitive=false, so a username match
    # against the DB row breaks for any user who registered with capital letters.
    if not cognito_user.user_id:
        raise AuthError("Unauthorized: no sub found in claims")

    user = await get_user_by_cognito_sub(cognito_user.user_id)
    if not user:
        raise AuthError("Unauthorized: user not found in DB")

    return user

async def ensure_db():
    """Reset the global Database for the current asyncio loop.

    Each Lambda invocation runs under a fresh asyncio.run() loop, but the
    module-global db_connection's asyncpg pool was created on the previous
    (now-closed) loop. We can't reassign the global because lambdas import
    the symbol directly (`from shared.db.database import db_connection`),
    so they'd hold a stale reference. Instead, terminate the old pool and
    re-run __init__ in place — same object, fresh internal state — then
    connect on the current loop.
    """
    try:
        backend = getattr(db_connection, "_backend", None)
        old_pool = getattr(backend, "_pool", None) if backend else None
        if old_pool is not None:
            old_pool.terminate()
    except Exception:
        pass
    type(db_connection).__init__(
        db_connection, settings.database_url, min_size=1, max_size=2
    )
    await db_connection.connect()