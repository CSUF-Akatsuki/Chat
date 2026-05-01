import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import os

os.environ["ENVIRONMENT"] = "test"

from lambdas.message_lambda import (
    endpoint_get_messages,
    endpoint_get_conversations,
)

USER_UUID = "11111111-1111-1111-1111-111111111111"
OTHER_UUID = "22222222-2222-2222-2222-222222222222"

def create_mock_event(body=None, path_parameters=None, query_string=None, claims=None):
    if claims is None:
        claims = {"username": "testuser"}
    
    event = {
        "version": "2.0",
        "routeKey": "ANY /test",
        "rawPath": "/test",
        "rawQueryString": "",
        "headers": {},
        "requestContext": {
            "authorizer": {
                "jwt": {
                    "claims": claims
                }
            }
        },
        "isBase64Encoded": False
    }
    
    if body:
        event["body"] = json.dumps(body)
    if path_parameters:
        event["pathParameters"] = path_parameters
    if query_string:
        event["queryStringParameters"] = query_string
        
    return event

# Pytest fixture for mocking the DB and user fetches.
# We patch:
#   - lambdas.message_lambda.db_connection  — the db reference used inside the lambda
#   - lambdas.message_lambda.ensure_db      — skip the real asyncpg pool setup
#   - lambdas.message_lambda.get_database_user_from_event — return a fake user directly
@pytest.fixture
def mock_db():
    mock_conn = MagicMock()
    mock_conn.is_connected = True
    mock_conn.connect = AsyncMock()
    mock_conn.fetch_one = AsyncMock()
    mock_conn.fetch_all = AsyncMock()
    mock_conn.execute = AsyncMock()

    async def fake_ensure_db():
        pass

    async def fake_get_db_user(api_event):
        return {"cognito_sub": USER_UUID, "username": "testuser"}

    with patch("lambdas.message_lambda.db_connection", mock_conn), \
         patch("lambdas.message_lambda.ensure_db", fake_ensure_db), \
         patch("lambdas.message_lambda.get_database_user_from_event", fake_get_db_user):
        yield mock_conn, None


def test_get_messages(mock_db):
    mock_conn, _ = mock_db
    
    mock_conn.fetch_all.return_value = [
        {
            "id": 1,
            "sender_id": USER_UUID,
            "reciever_id": OTHER_UUID,
            "content": "Hello",
            "created_at": "2026-04-22T00:00:00",
            "is_read": True,
        },
        {
            "id": 2,
            "sender_id": OTHER_UUID,
            "reciever_id": USER_UUID,
            "content": "Hi",
            "created_at": "2026-04-22T00:01:00",
            "is_read": False,
        },
    ]
    
    event = create_mock_event(
        path_parameters={"other_user_id": OTHER_UUID},
        query_string={"limit": "10", "offset": "0"}
    )
    context = MagicMock()
    
    response = endpoint_get_messages(event, context)
    
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert len(body) == 2
    assert body[0]["content"] == "Hello"


def test_get_conversations(mock_db):
    mock_conn, _ = mock_db
    
    mock_conn.fetch_all.return_value = [
        {
            "other_user_id": OTHER_UUID,
            "last_message": "Hi",
            "last_message_time": "2026-04-22T00:01:00",
            "username": "friend1",
        },
        {
            "other_user_id": "33333333-3333-3333-3333-333333333333",
            "last_message": "Yo",
            "last_message_time": "2026-04-22T00:02:00",
            "username": "friend2",
        },
    ]
    
    event = create_mock_event()
    context = MagicMock()
    
    response = endpoint_get_conversations(event, context)
    
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert len(body) == 2
    assert body[0]["username"] == "friend1"
