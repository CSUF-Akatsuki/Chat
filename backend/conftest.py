import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Set fake environment variables required by pydantic Settings before config is imported
os.environ["AWS_COGNITO_USER_POOL_ID"] = "test-pool-id"
os.environ["AWS_COGNITO_CLIENT_ID"] = "test-client-id"
os.environ["AWS_COGNITO_CLIENT_SECRET"] = "test-client-secret"
