from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.utilities.data_classes import APIGatewayProxyEventV2
from shared.auth import login, register, refresh_session, confirm_registration, logout
from models.users_model import ConfirmRegistrationRequest, CreateUserRequest, Token, UserLoginRequest
from lambdas.lib import _response
import asyncio

def endpoint_register(event:dict, context:LambdaContext):
    try:
        api_event = APIGatewayProxyEventV2(event)
        user = CreateUserRequest.model_validate_json(api_event.body)
        register(user)
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