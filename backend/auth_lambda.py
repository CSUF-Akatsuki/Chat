from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.utilities.data_classes import APIGatewayProxyEventV2
from shared.auth import login, register, refresh_session, confirm_registration, logout
from models.users_model import ConfirmRegistrationRequest, CreateUserRequest, Token, UserLoginRequest
import asyncio

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

def endpoint_register(event:dict, context:LambdaContext):
    try:
        api_event = APIGatewayProxyEventV2(event)
        user = CreateUserRequest.model_validate_json(api_event.body)
        register(user)
        return {"statusCode": 200, "body": "Success"}
        
    except Exception as e:
        return {"statusCode": 400, "body": str(e)}
    
def endpoint_confirm_register(event:dict, context:LambdaContext):
    try:
        api_event = APIGatewayProxyEventV2(event)
        confirmation = ConfirmRegistrationRequest.model_validate_json(api_event.body)

        loop = get_or_create_event_loop()
        user = loop.run_until_complete(confirm_registration(confirmation))
        
        return {"statusCode": 200, "body": user.model_dump_json()}
        
    except Exception as e:
        return {"statusCode": 400, "body": str(e)}
    
def endpoint_login(event:dict, context:LambdaContext):
    try:
        api_event = APIGatewayProxyEventV2(event)
        login_request = UserLoginRequest.model_validate_json(api_event.body)
        
        auth_data = login(login_request)
        
        return {"statusCode": 200, "body": Token(access_token=str(auth_data.access_token), token_type="bearer").model_dump_json()}
        
    except Exception as e:
        return {"statusCode": 400, "body": str(e)}
    
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
        
        return {"statusCode": 200, "body": Token(str(auth_data.access_token), token_type="bearer").model_dump_json()}
    except Exception as e:
        return {"statusCode": 400, "body": str(e)}
    
def endpoint_logout(event:dict, context:LambdaContext):
    try:
        api_event = APIGatewayProxyEventV2(event)
        auth_header = api_event.headers.get("Authorization") or api_event.headers.get("authorization")
    
        if not (auth_header and auth_header.startswith("Bearer ")):
            raise Exception("Malformed request.")

        jwt_token = auth_header.split(" ")[1]
        logout(jwt_token)
        delete_cookie = "refresh_token=deleted; Path=/; Max-Age=0; HttpOnly; Secure; SameSite=Strict"
        return {
            "statusCode": 200,
            "cookies": [ delete_cookie ],
            "body": "Success"
        }
        
    except Exception as e:
        return {"statusCode": 400, "body": str(e)}