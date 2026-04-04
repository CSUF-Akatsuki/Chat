from dataclasses import dataclass
from typing import Literal
from shared.logger import logger
from pycognito import Cognito
from pycognito.utils import TokenType
from shared.config import AWS_COGNITO_CLIENT_ID, AWS_COGNITO_USER_POOL_ID, AWS_COGNITO_CLIENT_SECRET
from botocore.exceptions import ClientError

# Initialize the library

@dataclass
class AuthData:
    id_token:TokenType
    access_token:TokenType
    refresh_token:str

def login(username:str, password:str) -> None | AuthData:
    try:
        u = Cognito(
            user_pool_id=AWS_COGNITO_USER_POOL_ID, 
            client_id=AWS_COGNITO_CLIENT_ID,
            client_secret=AWS_COGNITO_CLIENT_SECRET,
            username=username
        )

        u.authenticate(password=password)
        
        logger.info(f"""User "{username}" authenticated successfuly.""")

        return AuthData(u.id_token, u.access_token, u.refresh_token)
    except ClientError as e:
        logger.info(f"""Auth failed for "{username}": {e.response["Error"]["Message"]}""")
        return None
    except Exception as e:
        logger.exception(f"Unexpected error durring login: {e}")
        return None
    
def refresh_session(refresh_token: str) -> None | AuthData:
    try:
        u = Cognito(
            user_pool_id=AWS_COGNITO_USER_POOL_ID,
            client_id=AWS_COGNITO_CLIENT_ID,
            client_secret=AWS_COGNITO_CLIENT_SECRET
        )
        
        u.refresh_token = refresh_token
        
        u.renew_access_token()
        
        logger.info("Session successfully refreshed.")
        
        return AuthData(u.id_token, u.access_token, u.refresh_token)
    except ClientError as e:
        logger.error(f"Failed to refresh session: {e.response['Error']['Message']}")
        return None
    except Exception as e:
        logger.exception(f"Unexpected error during token refresh: {e}")
        return None


def register(email:str, username:str, password:str):
    u = Cognito(
        user_pool_id=AWS_COGNITO_USER_POOL_ID, 
        client_id=AWS_COGNITO_CLIENT_ID,
        client_secret=AWS_COGNITO_CLIENT_SECRET,
        username=username
    )

    try:
        u.set_base_attributes(email=email)
        u.register(username, password)
        logger.info(f"""User "{username}" successfully started account registration process.""")
    except ClientError as e:
        logger.error(f'Registration failed for "{username}": {e.response["Error"]["Message"]}')
    except Exception as e:
        logger.exception(f"Unexpected error during registration: {e}")

def confirm_registration(username:str, code:str):
    u = Cognito(
        user_pool_id=AWS_COGNITO_USER_POOL_ID, 
        client_id=AWS_COGNITO_CLIENT_ID,
        client_secret=AWS_COGNITO_CLIENT_SECRET,
        username=username
    )

    try:
        u.confirm_sign_up(code, username=username)
        logger.info(f"""User "{username}" successfully confirmed their account creation.""")
    except ClientError as e:
        logger.error(f'Confirming registration failed for "{username}": {e.response["Error"]["Message"]}')
    except Exception as e:
        logger.exception(f"Unexpected error during registration confirmation: {e}")