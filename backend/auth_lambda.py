from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.utilities.data_classes import APIGatewayProxyEvent
from shared.auth import login, register, refresh_session, confirm_registration


def main(event:dict, context:LambdaContext):
    api_event = APIGatewayProxyEvent(event)
    
    match api_event.http_method:
        case "GET":
            return get(api_event, context)
        
        case "POST":
            return post(api_event, context)
        
        case "PUT":
            return put(api_event, context)
        
        case "PATCH":
            return patch(api_event, context)
        
        case "DELETE":
            return delete(api_event, context)

def get(api_event:APIGatewayProxyEvent, context:LambdaContext):
    pass

def post(api_event:APIGatewayProxyEvent, context:LambdaContext):
    pass

def put(api_event:APIGatewayProxyEvent, context:LambdaContext):
    pass

def patch(api_event:APIGatewayProxyEvent, context:LambdaContext):
    pass

def delete(api_event:APIGatewayProxyEvent, context:LambdaContext):
    pass