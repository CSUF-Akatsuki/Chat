locals {
  image_uri = "${aws_ecr_repository.lambdas.repository_url}:${var.lambda_image_tag}"

  common_env = {
    AWS_COGNITO_USER_POOL_ID  = aws_cognito_user_pool.main.id
    AWS_COGNITO_CLIENT_ID     = aws_cognito_user_pool_client.backend.id
    AWS_COGNITO_CLIENT_SECRET = aws_cognito_user_pool_client.backend.client_secret
    AWS_AZ                    = data.aws_region.current.name
    CORS_ALLOWED_ORIGIN       = var.cors_allowed_origin
    DB_SECRET_ARN             = data.aws_secretsmanager_secret.db.arn
    REDIS_SECRET_ARN          = data.aws_secretsmanager_secret.redis.arn
  }

  # handler_command per logical endpoint maps to the lambda code's module.function.
  # The same container image is reused; CMD override picks the handler.
  endpoints = {
    register         = { module = "lambdas.auth_lambda", fn = "endpoint_register", method = "POST", path = "/auth/register", authorize = false }
    register_confirm = { module = "lambdas.auth_lambda", fn = "endpoint_confirm_register", method = "POST", path = "/auth/register/confirm", authorize = false }
    login            = { module = "lambdas.auth_lambda", fn = "endpoint_login", method = "POST", path = "/auth/login", authorize = false }
    refresh          = { module = "lambdas.auth_lambda", fn = "endpoint_refresh", method = "POST", path = "/auth/refresh", authorize = false }
    logout           = { module = "lambdas.auth_lambda", fn = "endpoint_logout", method = "POST", path = "/auth/logout", authorize = true }

    send_friend_request   = { module = "lambdas.friends_lambda", fn = "endpoint_send_friend_request", method = "POST", path = "/friends/request", authorize = true }
    accept_friend_request = { module = "lambdas.friends_lambda", fn = "endpoint_accept_friendrequest", method = "POST", path = "/friends/accept/{friend_id}", authorize = true }
    reject_friend_request = { module = "lambdas.friends_lambda", fn = "endpoint_reject_friend_request", method = "POST", path = "/friends/reject/{friend_id}", authorize = true }
    block_friend          = { module = "lambdas.friends_lambda", fn = "endpoint_block_friend", method = "POST", path = "/friends/block/{friend_id}", authorize = true }
    get_all_friends       = { module = "lambdas.friends_lambda", fn = "endpoint_get_all_friends", method = "GET", path = "/friends", authorize = true }
    remove_friend         = { module = "lambdas.friends_lambda", fn = "endpoint_remove_friend", method = "DELETE", path = "/friends/{friend_id}", authorize = true }
    people_you_may_know   = { module = "lambdas.friends_lambda", fn = "endpoint_people_you_may_know", method = "GET", path = "/friends/suggestions", authorize = true }
    all_friend_requests   = { module = "lambdas.friends_lambda", fn = "endpoint_all_friend_requests", method = "GET", path = "/friends/requests", authorize = true }

    get_messages        = { module = "lambdas.message_lambda", fn = "endpoint_get_messages", method = "GET", path = "/messages/{other_user_id}", authorize = true }
    get_conversations   = { module = "lambdas.message_lambda", fn = "endpoint_get_conversations", method = "GET", path = "/conversations", authorize = true }
    delete_conversation = { module = "lambdas.message_lambda", fn = "endpoint_delete_conversation", method = "DELETE", path = "/messages/{other_user_id}", authorize = true }
  }
}

resource "aws_cloudwatch_log_group" "lambda" {
  for_each          = local.endpoints
  name              = "/aws/lambda/${var.project}-${each.key}"
  retention_in_days = 14
}

resource "aws_lambda_function" "endpoint" {
  for_each = local.endpoints

  function_name = "${var.project}-${each.key}"
  role          = aws_iam_role.lambda_exec.arn
  package_type  = "Image"
  image_uri     = local.image_uri
  architectures = ["arm64"]

  image_config {
    command = ["${each.value.module}.${each.value.fn}"]
  }

  timeout     = 30
  memory_size = 512

  vpc_config {
    subnet_ids         = data.aws_subnets.private_app.ids
    security_group_ids = [aws_security_group.lambda.id]
  }

  environment {
    variables = local.common_env
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_basic,
    aws_iam_role_policy_attachment.lambda_vpc,
    aws_iam_role_policy_attachment.lambda_secrets,
    aws_cloudwatch_log_group.lambda,
  ]
}
