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

class CognitoHelper:
    @staticmethod
    def extract_user_from_event(event: APIGatewayProxyEventV2) -> Optional[CognitoUser]:
        """Extract user information from API Gateway event with Cognito authorizer"""
        try:
            claims = event.request_context.authorizer.jwt_claim
            
            username = (claims.get('cognito:username') or 
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
        except (KeyError, TypeError) as e:
            logger.error(f"Failed to extract user from event: {str(e)}")
            return None

async def get_database_user_from_event(api_event: APIGatewayProxyEventV2):    
    cognito_user = CognitoHelper.extract_user_from_event(api_event)

    if not cognito_user.username:
        raise Exception("Unauthorized: No username found in claims or token")
    
    user = await get_user_by_username(cognito_user.username)
    if not user:
        raise Exception("Unauthorized: User not found in DB")
    
    # Handle schema variance between id and cognito_id
    if "id" not in user and "cognito_id" in user:
        user["id"] = user["cognito_id"]
        
    return user

async def ensure_db():
    if not db_connection.is_connected:
        await db_connection.connect()