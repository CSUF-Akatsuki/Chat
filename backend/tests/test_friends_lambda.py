import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

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

# Pytest fixture for mocking the DB and user fetches
@pytest.fixture
def mock_db():
    with patch("lambdas.friends_lambda.db_connection") as mock_conn, \
         patch("lambdas.friends_lambda.get_user_by_username") as mock_get_user:
         
        mock_conn.is_connected = True
        mock_conn.connect = AsyncMock()
        mock_conn.fetch_one = AsyncMock()
        mock_conn.fetch_all = AsyncMock()
        mock_conn.execute = AsyncMock()
        
        # Default mock user
        mock_get_user.return_value = {"id": 1, "username": "testuser"}
        
        yield mock_conn, mock_get_user


def test_send_friend_request_success(mock_db):
    mock_conn, _ = mock_db
    
    # Setup mocks
    # 1. Target user exists
    mock_conn.fetch_one.side_effect = [
        {"id": 2}, # check_friend_exists
        None,      # check_exists_query (no existing friendship)
        {"id": 100, "user_id": 1, "friend_id": 2, "status": "pending", "created_at": "2026-04-22T00:00:00"} # insert response
    ]
    
    event = create_mock_event(body={"id": 2})
    context = MagicMock()
    
    response = endpoint_send_friend_request(event, context)
    
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["status"] == "pending"
    assert body["friend_id"] == 2


def test_send_friend_request_to_self(mock_db):
    event = create_mock_event(body={"id": 1}) # Current user is id 1
    context = MagicMock()
    
    response = endpoint_send_friend_request(event, context)
    
    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert "cannot send request to yourself" in body["detail"]


def test_accept_friend_request(mock_db):
    mock_conn, _ = mock_db
    
    # Return a fake id representing successful update
    mock_conn.fetch_one.return_value = {"id": 100}
    
    event = create_mock_event(path_parameters={"friend_id": "2"})
    context = MagicMock()
    
    response = endpoint_accept_friendrequest(event, context)
    
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["success"] is True


def test_get_all_friends(mock_db):
    mock_conn, _ = mock_db
    
    # Return a list of fake friends
    mock_conn.fetch_all.return_value = [
        {"id": 2, "username": "friend1", "friendship_status": "accepted", "friendship_created_at": "2026-04-22T00:00:00"},
        {"id": 3, "username": "friend2", "friendship_status": "accepted", "friendship_created_at": "2026-04-22T00:00:00"}
    ]
    
    event = create_mock_event()
    context = MagicMock()
    
    response = endpoint_get_all_friends(event, context)
    
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert len(body) == 2
    assert body[0]["username"] == "friend1"
