# The ECS task definition for the WebSocket server is not managed in this
# Terraform workspace. When updating that task definition, add the following
# to the WebSocket server container:
#
#   CHATBOT_LAMBDA_NAME = <chatbot_lambda_arn output>
#   task_role_arn       = <ecs_task_role_arn output>
#
# The WebSocket server uses CHATBOT_LAMBDA_NAME to fire-and-forget invoke the
# Chatbot Lambda when a message is sent to the Mutalip bot. The task role
# (defined in iam.tf) grants the required lambda:InvokeFunction permission.

locals {
  websocket_server_chatbot_env = {
    CHATBOT_LAMBDA_NAME = aws_lambda_function.chatbot.arn
  }
}
