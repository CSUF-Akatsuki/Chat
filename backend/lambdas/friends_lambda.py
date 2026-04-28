import asyncio
import json
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.utilities.data_classes import APIGatewayProxyEventV2
from lambdas.lib import ensure_db, get_database_user_from_event, get_or_create_event_loop
from shared.db.database import db_connection
from shared.logger import logger
from models.friends import FriendShipResponse, FriendRequest, FriendsProfile


def endpoint_send_friend_request(event: dict, context: LambdaContext):
    loop = get_or_create_event_loop()
    
    async def _process():
        try:
            api_event = APIGatewayProxyEventV2(event)
            friend_request = FriendRequest.model_validate_json(api_event.body)
            
            await ensure_db()
            current_user = await get_database_user_from_event(api_event)
            
            if current_user["id"] == friend_request.id:
                return {"statusCode": 400, "body": json.dumps({"detail": "cannot send request to yourself or the current user"})}
                
            check_friend_exists = await db_connection.fetch_one(
                query="SELECT id FROM users WHERE id = :user_id",
                values={"user_id": friend_request.id},
            )
            if not check_friend_exists:
                logger.error(f"The user does not exist {friend_request.id}")
                return {"statusCode": 404, "body": json.dumps({"detail": "The user does not exist"})}

            check_exists_query = """
                                    SELECT * FROM friendships
                                    WHERE (user_id = :user_id AND friend_id = :friend_id)
                                    OR (friend_id= :user_id AND user_id = :friend_id)
                                """
            exists = await db_connection.fetch_one(
                query=check_exists_query,
                values={"user_id": current_user["id"], "friend_id": friend_request.id},
            )

            if exists and exists["status"] not in (None, "none", "rejected"):
                return {"statusCode": 400, "body": json.dumps({"detail": f"Friend request already exists with status: {exists['status']}"})}

            if exists and exists["status"] in (None, "none", "rejected"):
                await db_connection.execute(
                    query="DELETE FROM friendships WHERE id = :id",
                    values={"id": exists["id"]},
                )

            query = """
                        INSERT INTO friendships (user_id,friend_id,status)
                        VALUES (:user_id,:friend_id,'pending')
                        RETURNING id,user_id,friend_id,status,created_at
                    """
            db_res = await db_connection.fetch_one(
                query=query,
                values={"user_id": current_user["id"], "friend_id": friend_request.id},
            )
            res_obj = FriendShipResponse(**dict(db_res))
            return {"statusCode": 200, "body": res_obj.model_dump_json()}

        except Exception as e:
            logger.error(f"Failed to send a friend request {e}", exc_info=True)
            return {"statusCode": 500, "body": json.dumps({"detail": str(e)})}
            
    return loop.run_until_complete(_process())

def endpoint_accept_friendrequest(event: dict, context: LambdaContext):
    loop = get_or_create_event_loop()
    
    async def _process():
        try:
            api_event = APIGatewayProxyEventV2(event)
            friend_id_str = api_event.path_parameters.get("friend_id")
            if not friend_id_str:
                return {"statusCode": 400, "body": json.dumps({"detail": "friend_id is required"})}
            friend_id = int(friend_id_str)
            
            await ensure_db()
            current_user = await get_database_user_from_event(api_event)

            query = """
                    UPDATE friendships 
                    SET status='accepted'
                    WHERE user_id = :friend_id
                    AND friend_id = :user_id
                    AND status = 'pending'
                    RETURNING id
                    """
            res = await db_connection.fetch_one(
                query=query,
                values={"user_id": current_user["id"], "friend_id": friend_id},
            )
            if res:
                return {"statusCode": 200, "body": json.dumps({"success": True, "message": "Friend Request Accepted"})}
            else:
                return {"statusCode": 404, "body": json.dumps({"detail": "Friend request not found"})}
                
        except Exception as e:
            logger.error(f"Failed to accept the friend request {e}", exc_info=True)
            return {"statusCode": 500, "body": json.dumps({"detail": str(e)})}
            
    return loop.run_until_complete(_process())

def endpoint_reject_friend_request(event: dict, context: LambdaContext):
    loop = get_or_create_event_loop()
    
    async def _process():
        try:
            api_event = APIGatewayProxyEventV2(event)
            friend_id_str = api_event.path_parameters.get("friend_id")
            if not friend_id_str:
                return {"statusCode": 400, "body": json.dumps({"detail": "friend_id is required"})}
            friend_id = int(friend_id_str)
            
            await ensure_db()
            current_user = await get_database_user_from_event(api_event)

            query = """
                   DELETE FROM friendships 
                    WHERE user_id = :friend_id
                    AND friend_id = :user_id
                    AND status = 'pending'
                    RETURNING id
                    """
            res = await db_connection.fetch_one(
                query=query,
                values={"user_id": current_user["id"], "friend_id": friend_id},
            )
            if res:
                return {"statusCode": 200, "body": json.dumps({"success": True, "message": "Friend Request Rejected"})}
            else:
                return {"statusCode": 404, "body": json.dumps({"detail": "Friend request not found"})}
                
        except Exception as e:
            logger.error(f"Failed to reject the friend request {e}", exc_info=True)
            return {"statusCode": 500, "body": json.dumps({"detail": str(e)})}
            
    return loop.run_until_complete(_process())

def endpoint_block_friend(event: dict, context: LambdaContext):
    loop = get_or_create_event_loop()
    
    async def _process():
        try:
            api_event = APIGatewayProxyEventV2(event)
            friend_id_str = api_event.path_parameters.get("friend_id")
            if not friend_id_str:
                return {"statusCode": 400, "body": json.dumps({"detail": "friend_id is required"})}
            friend_id = int(friend_id_str)
            
            await ensure_db()
            current_user = await get_database_user_from_event(api_event)

            query = """
                        UPDATE friendships
                        SET status='blocked'
                        WHERE ((user_id = :user_id AND friend_id = :friend_id)
                            OR (user_id = :friend_id AND friend_id = :user_id))
                        AND status='accepted'
                        RETURNING id
                    """
            response = await db_connection.fetch_one(
                query=query,
                values={"user_id": current_user["id"], "friend_id": friend_id},
            )
            if not response:
                return {"statusCode": 404, "body": json.dumps({"detail": "No accepted friendship found to block"})}
            else:
                return {"statusCode": 200, "body": json.dumps({"success": True, "message": "sucessfully blocked"})}
                
        except Exception as e:
            logger.error(f"Error Blocking friend {e}", exc_info=True)
            return {"statusCode": 500, "body": json.dumps({"detail": str(e)})}
            
    return loop.run_until_complete(_process())

def endpoint_get_all_friends(event: dict, context: LambdaContext):
    loop = get_or_create_event_loop()
    
    async def _process():
        try:
            api_event = APIGatewayProxyEventV2(event)
            await ensure_db()
            current_user = await get_database_user_from_event(api_event)

            query = """
                        SELECT
                            u.id,
                            u.username,
                            f.status as friendship_status,
                            f.created_at as friendship_created_at
                        FROM friendships f 
                        JOIN users u ON (
                            CASE 
                                WHEN f.user_id = :user_id THEN u.id = f.friend_id
                                ELSE u.id = f.user_id
                            END
                        )
                        WHERE (f.user_id = :user_id OR f.friend_id = :user_id) 
                        AND f.status = 'accepted'
                    """
            friends = await db_connection.fetch_all(
                query=query, values={"user_id": current_user["id"]}
            )
            
            res_list = [FriendsProfile(**dict(friend)).model_dump() for friend in friends]
            return {"statusCode": 200, "body": json.dumps(res_list, default=str)}

        except Exception as e:
            logger.error(f"Error fetching friends {e}", exc_info=True)
            return {"statusCode": 500, "body": json.dumps({"detail": str(e)})}
            
    return loop.run_until_complete(_process())

def endpoint_remove_friend(event: dict, context: LambdaContext):
    loop = get_or_create_event_loop()
    
    async def _process():
        try:
            api_event = APIGatewayProxyEventV2(event)
            friend_id_str = api_event.path_parameters.get("friend_id")
            if not friend_id_str:
                return {"statusCode": 400, "body": json.dumps({"detail": "friend_id is required"})}
            friend_id = int(friend_id_str)
            
            await ensure_db()
            current_user = await get_database_user_from_event(api_event)

            query = """
                        DELETE FROM friendships
                        WHERE ((user_id =:user_id AND friend_id = :friend_id)
                        OR (user_id = :friend_id AND friend_id = :user_id))
                        AND status IN ('pending','blocked','accepted')
                        RETURNING id
                    """
            response = await db_connection.fetch_one(
                query=query, values={"user_id": current_user["id"], "friend_id": friend_id}
            )
            if not response:
                return {"statusCode": 400, "body": json.dumps({"detail": "Error in removing friend"})}
            else:
                return {"statusCode": 200, "body": json.dumps({"success": True, "message": "Friend Removed"})}

        except Exception as e:
            logger.error(f"Error Deleting friend {e}", exc_info=True)
            return {"statusCode": 500, "body": json.dumps({"detail": str(e)})}
            
    return loop.run_until_complete(_process())

def endpoint_people_you_may_know(event: dict, context: LambdaContext):
    loop = get_or_create_event_loop()
    
    async def _process():
        try:
            api_event = APIGatewayProxyEventV2(event)
            await ensure_db()
            current_user = await get_database_user_from_event(api_event)

            query = """
                        SELECT id, username, 'none' as friendship_status, NOW() as friendship_created_at 
                        FROM users
                        WHERE id != :user_id
                        AND id NOT IN (
                            SELECT friend_id FROM friendships WHERE user_id = :user_id
                            UNION
                            SELECT user_id FROM friendships WHERE friend_id = :user_id
                        )
                    """
            people = await db_connection.fetch_all(
                query=query, values={"user_id": current_user["id"]}
            )
            
            res_list = [FriendsProfile(**dict(person)).model_dump() for person in people]
            return {"statusCode": 200, "body": json.dumps(res_list, default=str)}

        except Exception as e:
            logger.error(f"Something went wrong in fetching people you may know{e}")
            return {"statusCode": 500, "body": json.dumps({"detail": str(e)})}
            
    return loop.run_until_complete(_process())

def endpoint_all_friend_requests(event: dict, context: LambdaContext):
    loop = get_or_create_event_loop()
    
    async def _process():
        try:
            api_event = APIGatewayProxyEventV2(event)
            await ensure_db()
            current_user = await get_database_user_from_event(api_event)

            query = """
                        SELECT 
                            u.id,
                            u.username,
                            f.status as friendship_status,
                            f.created_at as friendship_created_at
                        FROM friendships f
                        JOIN users u ON u.id = f.user_id
                        WHERE f.friend_id = :user_id
                        AND f.status = 'pending'
                        ORDER BY f.created_at DESC
                   """
            friend_requests = await db_connection.fetch_all(
                query=query, values={"user_id": current_user["id"]}
            )
            
            res_list = [FriendsProfile(**dict(req)).model_dump() for req in friend_requests]
            return {"statusCode": 200, "body": json.dumps(res_list, default=str)}
            
        except Exception as e:
            logger.error(f"Error fetching friend requests {e}", exc_info=True)
            return {"statusCode": 500, "body": json.dumps({"detail": str(e)})}
            
    return loop.run_until_complete(_process())
