from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional

load_dotenv()

# SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here-change-in-production")
# ALGORITHM = "HS256"
# ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))


class Settings(BaseSettings):
    app_name: str = "Sarcasm Sync Chat App"
    app_version: str = "1.0.0"
    debug: bool = False
    log_level: str = "INFO"
    host: str = "0.0.0.0"
    port: int = 8000
    aws_az: str = Field(description="AWS availability zone", default='us-east-1')
    aws_cognito_user_pool_id: str = Field(description="AWS Cognito User Pool ID")
    aws_cognito_client_id: str = Field(description="AWS Cognito Client ID")
    aws_cognito_client_secret: Optional[str] = Field(description="AWS Cognito Client Secret", default=None) # Default to None in case not needed
    secret_key: str = Field(description="jwt secret", default="CHANGE_THIS_IN_PROD")
    algorithm: str = Field(default="HS256", description="JWT algo")
    access_token_expire_minutes: int = Field(default=30, description="jwt token")
    refresh_token_expire_days: int = Field(
        default=7, description="Refresh token expiry in days"
    )
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )
    # db settings
    postgres_user: str = Field(default="postgres", description="PostgreSQL username")
    postgres_password: str = Field(default="root", description="PostgreSQL password")
    postgres_host: str = Field(default="localhost", description="PostgreSQL host")
    postgres_port: int = Field(default=5432, description="PostgreSQL port")
    postgres_db: str = Field(default="chat", description="PostgreSQL database name")

    @property
    def database_url(self) -> str:
        """Construct async PostgreSQL connection URL."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
            f"?ssl=require"
        )

    # redis
    redis_host: str = Field(default="redis", description="redis host")
    redis_port: int = Field(default=6379, description="redis port")
    redis_db: int = Field(default=1, description="redis db name")
    redis_password: str = Field(default="", description="redis password")

    # chatbot
    mutalip_bot_uuid: str = Field(
        default="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        description="Fixed UUID for the Mutalip Kurban chatbot user",
    )


settings = Settings()

AWS_COGNITO_CLIENT_SECRET = settings.aws_cognito_client_secret
AWS_COGNITO_CLIENT_ID = settings.aws_cognito_client_id
AWS_COGNITO_USER_POOL_ID = settings.aws_cognito_user_pool_id
AWS_AZ = settings.aws_az
SECRET_KEY = settings.secret_key
ALGORITHM = settings.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes
REFRESH_TOKEN_EXPIRE_DAYS = settings.refresh_token_expire_days
MUTALIP_BOT_UUID = settings.mutalip_bot_uuid
