variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-west-1"
}

variable "environment" {
  description = "Deployment environment tag"
  type        = string
  default     = "dev"
}

variable "project" {
  description = "Resource name prefix"
  type        = string
  default     = "room67chat"
}

variable "lambda_image_tag" {
  description = "ECR image tag the Lambda functions should run. Updated by build-and-push.sh."
  type        = string
  default     = "latest"
}

variable "cors_allowed_origin" {
  description = "Origin allowed by CORS on API Gateway and the lambdas. CloudFront URL in prod."
  type        = string
  default     = "*"
}

variable "local_auth_mode" {
  description = "If true, the WebSocket falls back to legacy SECRET_KEY HS256. Lambdas always use Cognito."
  type        = bool
  default     = false
}
