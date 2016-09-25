# Lambda Functions
Calligre API for social content.

## Notes
Terraform all the things:
- https://www.terraform.io/docs/providers/aws/r/api_gateway_rest_api.html
- http://www.arvinep.com/2016/06/terraforming-amazon-aws-lambda-function.html

Proper status code setting:
- Raise an exception w/ error code in message:
  - http://docs.aws.amazon.com/lambda/latest/dg/python-exceptions.html
  - http://stackoverflow.com/questions/31329495/is-there-a-way-to-change-the-http-status-codes-returned-by-amazon-api-gateway
- Regex on normal return: https://aws.amazon.com/blogs/compute/error-handling-patterns-in-amazon-api-gateway-and-aws-lambda/
