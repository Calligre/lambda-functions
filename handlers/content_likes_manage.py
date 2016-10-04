# curl -X POST
#      -H "Content-Type: application/json"
#      -d '{"userid":12}'
#      https://calligre.com/api/content/1470003029.5935809612274169921875/likes
import decimal

import boto3
from boto3.dynamodb.conditions import Not, Attr


REGION = "us-west-2"
DYNAMO = boto3.resource('dynamodb', region_name=REGION).Table("calligre-posts")


def lambda_handler(event, _context):
    print("Received event: {}".format(event))

    path_params = event.get("pathParameters", {})
    postid = path_params.get("id")
    userid = "auth0userid"

    if postid is None:
        return {
            "statusCode": 400,
            "body": "Provide a post ID",
        }

    method = event.get("httpMethod")
    if method == "POST":
        update = "ADD likes :like SET like_count = like_count + :1"
        update_cond = Not(Attr("likes").contains(userid))
    elif method == "DELETE":
        update = "DELETE likes :like SET like_count = like_count - :1"
        update_cond = Attr("likes").contains(userid)
    else:
        return {
            "statusCode": 405,
        }

    try:
        response = DYNAMO.update_item(
            Key={
                "posts": "posts",
                "timestamp": decimal.Decimal(postid),
            },
            UpdateExpression=update,
            ExpressionAttributeValues={
                ':like': set([userid]),
                ':1': 1
            },
            ConditionExpression=update_cond,
        )

        code = response.get("ResponseMetadata", {}).get("HTTPStatusCode", 500)
        return {
            "statusCode": code,
        }
    # TODO: more specific exception
    # pylint: disable=broad-except
    except Exception as err:
        # pylint: disable=no-member
        print(err.response)

        code = err.response.get("Error", {}).get("Code", "")
        if code == "ConditionalCheckFailedException":
            return {
                "statusCode": 200,
                "body": "No changes",
            }

        message = err.response.get("Error", {}).get("Message", "Unknown Error")
        return {
            "statusCode": 500,
            "body": "{}: {}".format(code, message),
        }
