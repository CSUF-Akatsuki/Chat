output "api_url" {
  description = "Invoke URL for the HTTP API. Frontend uses this for HTTP calls."
  value       = aws_apigatewayv2_api.main.api_endpoint
}

output "cognito_user_pool_id" {
  description = "Cognito User Pool ID. Set as AWS_COGNITO_USER_POOL_ID on the WebSocket server."
  value       = aws_cognito_user_pool.main.id
}

output "cognito_client_id" {
  description = "Cognito App Client ID. Set as AWS_COGNITO_CLIENT_ID on the WebSocket server and the frontend."
  value       = aws_cognito_user_pool_client.backend.id
}

output "cognito_client_secret" {
  description = "Cognito App Client secret. Required by pycognito for server-side auth flows."
  value       = aws_cognito_user_pool_client.backend.client_secret
  sensitive   = true
}

output "cognito_jwks_url" {
  description = "JWKS URL the WebSocket server uses to verify Cognito JWTs."
  value       = "https://cognito-idp.${data.aws_region.current.name}.amazonaws.com/${aws_cognito_user_pool.main.id}/.well-known/jwks.json"
}

output "ecr_repository_url" {
  description = "ECR repo URL for the Lambda container image. Used by build-and-push.sh."
  value       = aws_ecr_repository.lambdas.repository_url
}

output "lambda_security_group_id" {
  description = "Security group attached to all Lambda functions."
  value       = aws_security_group.lambda.id
}

output "chatbot_lambda_arn" {
  description = "ARN of the Chatbot Lambda. Set as CHATBOT_LAMBDA_NAME on the WebSocket server ECS task container environment."
  value       = aws_lambda_function.chatbot.arn
}

output "ecs_task_role_arn" {
  description = "ARN of the ECS task IAM role. Set as task_role_arn on the WebSocket server ECS task definition so it can invoke the Chatbot Lambda."
  value       = aws_iam_role.ecs_task.arn
}
