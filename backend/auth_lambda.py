from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.utilities.data_classes import APIGatewayProxyEvent



def handler(event:dict, context:LambdaContext):
    api_event = APIGatewayProxyEvent(event)
    
    