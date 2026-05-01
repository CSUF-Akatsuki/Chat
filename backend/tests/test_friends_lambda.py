import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

# Need to set environment variable before importing lambdas to avoid side effects
import os
os.environ["ENVIRONMENT"] = "test"

# Import lambda functions
from lambdas.friends_lambda import (
    endpoint_send_friend_request,
    endpoint_accept_friendrequest,
    endpoint_reject_friend_request,
    endpoint_get_all_friends,
)

BOT_UUID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
USER_UUID = "11111111-1111-1111-1111-111111111111"
FRIEND_UUID = "22222222-2222-2222-2222-222222222222"

# Helper to create a mock API Gateway event
def create_mock_event(body=None, path_parameters=None, claims=None, headers=None):
    if claims is None:
        claims = {"username": "testuser"}
    
    event = {
        "version": "2.0",
        "routeKey": "ANY /test",
        "rawPath": "/test",
        "rawQueryString": "",
        "headers": headers or {},
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
        
    return event

# Pytest fixture for mocking the DB and user fetches.
# We patch:
#   - lambdas.friends_lambda.db_connection  — the db reference used inside the lambda
#   - lambdas.friends_lambda.ensure_db      — skip the real asyncpg pool setup
#   - lambdas.friends_lambda.get_database_user_from_event — return a fake user directly
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
        return {"cognito_sub": UUID(USER_UUID), "username": "testuser"}

    with patch("lambdas.friends_lambda.db_connection", mock_conn), \
         patch("lambdas.friends_lambda.ensure_db", fake_ensure_db), \
         patch("lambdas.friends_lambda.get_database_user_from_event", fake_get_db_user):
        yield mock_conn, None


def test_send_friend_request_success(mock_db):
    mock_conn, _ = mock_db
    
    # Setup mocks
    # 1. Target user exists (check_friend_exists)
    # 2. No existing friendship (check_exists_query)
    # 3. Insert response
    mock_conn.fetch_one.side_effect = [
        {"cognito_sub": FRIEND_UUID},  # check_friend_exists
        None,                           # check_exists_query (no existing friendship)
        {                               # insert response
            "id": 100,
            "user_id": USER_UUID,
            "friend_id": FRIEND_UUID,
            "status": "pending",
            "created_at": "2026-04-22T00:00:00",
        },
    ]
    
    event = create_mock_event(body={"cognito_sub": FRIEND_UUID})
    context = MagicMock()
    
    response = endpoint_send_friend_request(event, context)
    
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["status"] == "pending"
    assert body["friend_id"] == FRIEND_UUID


def test_send_friend_request_to_self(mock_db):
    # Current user cognito_sub is USER_UUID; sending to the same UUID should fail
    event = create_mock_event(body={"cognito_sub": USER_UUID})
    context = MagicMock()
    
    response = endpoint_send_friend_request(event, context)
    
    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert "cannot send request to yourself" in body["detail"]


def test_accept_friend_request(mock_db):
    mock_conn, _ = mock_db
    
    # Return a fake id representing successful update
    mock_conn.fetch_one.return_value = {"id": 100}
    
    event = create_mock_event(path_parameters={"friend_id": FRIEND_UUID})
    context = MagicMock()
    
    response = endpoint_accept_friendrequest(event, context)
    
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["success"] is True


def test_get_all_friends(mock_db):
    mock_conn, _ = mock_db
    
    # Return a list of fake friends using cognito_sub (UUID) fields
    mock_conn.fetch_all.return_value = [
        {
            "cognito_sub": FRIEND_UUID,
            "username": "friend1",
            "friendship_status": "accepted",
            "friendship_created_at": "2026-04-22T00:00:00",
        },
        {
            "cognito_sub": "33333333-3333-3333-3333-333333333333",
            "username": "friend2",
            "friendship_status": "accepted",
            "friendship_created_at": "2026-04-22T00:00:00",
        },
    ]
    
    event = create_mock_event()
    context = MagicMock()
    
    response = endpoint_get_all_friends(event, context)
    
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert len(body) == 2
    assert body[0]["username"] == "friend1"
