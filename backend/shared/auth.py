from dataclasses import dataclass
from typing import Literal
from models.users_model import CreateUserRequest, User
from shared.logger import logger
from pycognito import Cognito
from pycognito.utils import TokenType
from shared.config import AWS_COGNITO_CLIENT_ID, AWS_COGNITO_USER_POOL_ID, AWS_COGNITO_CLIENT_SECRET
from botocore.exceptions import ClientError
from shared.db.database import db_connection
# Initialize the library

@dataclass
class AuthData:
    id_token:TokenType
    access_token:TokenType
    refresh_token:str

async def login(username:str, password:str) -> None | AuthData:
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
    
async def refresh_session(refresh_token: str) -> None | AuthData:
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


async def register(user: CreateUserRequest):
    try:
        u = Cognito(
            user_pool_id=AWS_COGNITO_USER_POOL_ID, 
            client_id=AWS_COGNITO_CLIENT_ID,
            client_secret=AWS_COGNITO_CLIENT_SECRET,
            username=user.username
        )
        u.set_base_attributes(email=user.email)
        u.register(user.username, user.password)
        logger.info(f"""User "{user.username}" successfully started account registration process.""")
    except ClientError as e:
        logger.error(f'Registration failed for "{user.username}": {e.response["Error"]["Message"]}')
    except Exception as e:
        logger.exception(f"Unexpected error during registration: {e}")

async def confirm_registration(email:str, username:str, code:str) -> User | None:
    try:
        u = Cognito(
            user_pool_id=AWS_COGNITO_USER_POOL_ID, 
            client_id=AWS_COGNITO_CLIENT_ID,
            client_secret=AWS_COGNITO_CLIENT_SECRET,
            username=username
        )
        u.confirm_sign_up(code, username=username)
        query = """
            INSERT INTO users (email, username)
            VALUES (:email, :username)
            RETURNING id, email, username, created_at
        """
        new_user = await db_connection.fetch_one(
            query=query,
            values={
                "email": email,
                "username": username,
            },
        )
        logger.info(f"""User "{username}" successfully confirmed their account creation.""")
        return User(
            id=new_user["id"], username=new_user["username"], email=new_user["email"]
        )
    except ClientError as e:
        logger.error(f'Confirming registration failed for "{username}": {e.response["Error"]["Message"]}')
        return None
    except Exception as e:
        logger.exception(f"Unexpected error during registration confirmation: {e}")
        return None
    
async def logout(refresh_token: str):
    """
    Revokes the specific refresh token and its associated access tokens.
    """
    try:
        u = Cognito(
            user_pool_id=AWS_COGNITO_USER_POOL_ID,
            client_id=AWS_COGNITO_CLIENT_ID,
            client_secret=AWS_COGNITO_CLIENT_SECRET
        )
        
        u.client.revoke_token(
            Token=refresh_token,
            ClientId=AWS_COGNITO_CLIENT_ID,
            ClientSecret=AWS_COGNITO_CLIENT_SECRET
        )
        
        logger.info("User successfully logged out of this session.")
        return True
    except ClientError as e:
        logger.error(f"Logout failed: {e.response['Error']['Message']}")
        return False