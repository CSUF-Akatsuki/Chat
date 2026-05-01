from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.utilities.data_classes import APIGatewayProxyEventV2
from shared.auth import login, register, refresh_session, confirm_registration, logout
from shared.db.database import db_connection
from shared.logger import logger
from models.users_model import ConfirmRegistrationRequest, CreateUserRequest, Token, UserLoginRequest
from lambdas.lib import _response, ensure_db
import asyncio
import os
import boto3

_cognito = boto3.client("cognito-idp", region_name=os.environ.get("AWS_AZ", "us-west-1"))

def endpoint_register(event: dict, context: LambdaContext):
    """Register + auto-confirm + insert into users table.

    Demo flow: bypasses email verification by admin-confirming the user
    server-side. The frontend skips the confirm-code screen entirely.
    Switch to the email-code flow later by removing the admin_confirm_sign_up
    block and restoring endpoint_confirm_register on a /auth/register/confirm
    route.
    """
    try:
        api_event = APIGatewayProxyEventV2(event)
        user = CreateUserRequest.model_validate_json(api_event.body)
        pool_id = os.environ["AWS_COGNITO_USER_POOL_ID"]

        register(user)

        _cognito.admin_confirm_sign_up(UserPoolId=pool_id, Username=user.username)
        _cognito.admin_update_user_attributes(
            UserPoolId=pool_id,
            Username=user.username,
            UserAttributes=[{"Name": "email_verified", "Value": "true"}],
        )

        resp = _cognito.admin_get_user(UserPoolId=pool_id, Username=user.username)
        sub = next(a["Value"] for a in resp["UserAttributes"] if a["Name"] == "sub")

        async def _insert_db_row():
            await ensure_db()
            await db_connection.execute(
                "INSERT INTO users (cognito_sub, email, username) VALUES (:sub, :email, :username)",
                values={"sub": sub, "email": user.email, "username": user.username},
            )
            # Non-fatal: create friendship with the Mutalip bot
            try:
                bot_uuid = os.environ.get("MUTALIP_BOT_UUID", "a1b2c3d4-e5f6-7890-abcd-ef1234567890")
                await db_connection.execute(
                    """
                    INSERT INTO friendships (user_id, friend_id, status)
                    VALUES (:user_id, :friend_id, 'accepted')
                    ON CONFLICT (user_id, friend_id) DO NOTHING
                    """,
                    values={"user_id": sub, "friend_id": bot_uuid},
                )
            except Exception as e:
                logger.error(f"Non-fatal: failed to create bot friendship for {sub}: {e}")

        asyncio.run(_insert_db_row())
        return _response(200, {"message": "Success"})

    except Exception as e:
        return _response(400, {"detail": str(e)})
    
def endpoint_confirm_register(event:dict, context:LambdaContext):
    try:
        api_event = APIGatewayProxyEventV2(event)
        confirmation = ConfirmRegistrationRequest.model_validate_json(api_event.body)

        user = asyncio.run(confirm_registration(confirmation))
        
        return _response(200, user.model_dump())
        
    except Exception as e:
        return _response(400, {"detail": str(e)})
    
def endpoint_login(event:dict, context:LambdaContext):
    try:
        api_event = APIGatewayProxyEventV2(event)
        login_request = UserLoginRequest.model_validate_json(api_event.body)
        
        auth_data = login(login_request)
        
        return _response(200, Token(access_token=str(auth_data.access_token), token_type="bearer").model_dump())
        
    except Exception as e:
        return _response(400, {"detail": str(e)})
    
def endpoint_refresh(event:dict, context:LambdaContext):
    try:
        api_event = APIGatewayProxyEventV2(event)
        raw_cookies = api_event.cookies
        
        cookie_dict = {}
        for c in raw_cookies:
            parts = c.split("=", 1)
            if len(parts) == 2:
                cookie_dict[parts[0].strip()] = parts[1].strip()

        refresh_token = cookie_dict.get("refresh_token")

        auth_data = refresh_session(refresh_token)
        
        return _response(200, Token(access_token=str(auth_data.access_token), token_type="bearer").model_dump())
    except Exception as e:
        return _response(400, {"detail": str(e)})
    
def endpoint_logout(event:dict, context:LambdaContext):
    try:
        api_event = APIGatewayProxyEventV2(event)
        auth_header = api_event.headers.get("Authorization") or api_event.headers.get("authorization")
    
        if not (auth_header and auth_header.startswith("Bearer ")):
            raise Exception("Malformed request.")

        jwt_token = auth_header.split(" ")[1]
        logout(jwt_token)
        delete_cookie = "refresh_token=deleted; Path=/; Max-Age=0; HttpOnly; Secure; SameSite=Strict"
        return _response(200, {"message": "Success"}, cookies=[delete_cookie])
        
    except Exception as e:
        return _response(400, {"detail": str(e)})