import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import os

os.environ["ENVIRONMENT"] = "test"

from lambdas.message_lambda import (
    endpoint_get_messages,
    endpoint_get_conversations,
)

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

@pytest.fixture
def mock_db():
    with patch("lambdas.message_lambda.db_connection") as mock_conn, \
         patch("lambdas.message_lambda.get_user_by_username") as mock_get_user:
         
        mock_conn.is_connected = True
        mock_conn.connect = AsyncMock()
        mock_conn.fetch_one = AsyncMock()
        mock_conn.fetch_all = AsyncMock()
        mock_conn.execute = AsyncMock()
        
        mock_get_user.return_value = {"id": 1, "username": "testuser"}
        
        yield mock_conn, mock_get_user


def test_get_messages(mock_db):
    mock_conn, _ = mock_db
    
    mock_conn.fetch_all.return_value = [
        {"id": 1, "sender_id": 1, "reciever_id": 2, "content": "Hello", "created_at": "2026-04-22T00:00:00", "is_read": True},
        {"id": 2, "sender_id": 2, "reciever_id": 1, "content": "Hi", "created_at": "2026-04-22T00:01:00", "is_read": False}
    ]
    
    event = create_mock_event(
        path_parameters={"other_user_id": "2"},
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
        {"other_user_id": 2, "last_message": "Hi", "last_message_time": "2026-04-22T00:01:00", "username": "friend1"},
        {"other_user_id": 3, "last_message": "Yo", "last_message_time": "2026-04-22T00:02:00", "username": "friend2"}
    ]
    
    event = create_mock_event()
    context = MagicMock()
    
    response = endpoint_get_conversations(event, context)
    
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert len(body) == 2
    assert body[0]["username"] == "friend1"
